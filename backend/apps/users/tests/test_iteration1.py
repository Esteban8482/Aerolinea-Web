"""Regresiones de interacciones entre HU-007, HU-008 y HU-009."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from rest_framework.test import APIClient

from apps.users.auth_services import recovery_token, request_recovery, reset_password
from apps.users.mail import process_verification_emails
from apps.users.models import EmailVerification, PasswordRecovery, User
from apps.users.services import register_customer, verification_token
from apps.users.tests.test_authentication import PASSWORD, csrf, independently, login
from apps.users.tests.test_registration import data as data
from apps.users.tests.test_registration import registration_settings as registration_settings

NEW_PASSWORD = "credencial-nueva-sintetica-iteracion-2026"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("role", ["ROOT", "ADMINISTRADOR"])
def test_login_rehash_cannot_overwrite_a_concurrent_password_reset(role, provider):
    if role == "ROOT":
        user = User.objects.create_root(
            root_id="iteration-root", email="root@example.invalid", password=PASSWORD
        )
    else:
        user = User.objects.create_user(email="admin@example.invalid", role=role, password=PASSWORD)
    # Una credencial heredada obliga a Django a actualizar el hash durante login.
    User.objects.filter(pk=user.pk).update(password=make_password(PASSWORD, hasher="pbkdf2_sha256"))
    request_recovery(email=user.email, origin="192.0.2.1")
    token = recovery_token(PasswordRecovery.objects.get())
    checking, resume = Event(), Event()
    original = User.check_password

    def delayed_check(instance, raw):
        if instance.pk == user.pk:
            checking.set()
            assert resume.wait(timeout=15)
        return original(instance, raw)

    def authenticate():
        client = APIClient(enforce_csrf_checks=True)
        csrf(client)
        response = login(client, user)
        return response.status_code, client

    def recover():
        reset_password(token=token, password=NEW_PASSWORD, origin="192.0.2.2")

    with patch.object(User, "check_password", delayed_check):
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending_login = pool.submit(independently, authenticate)
            try:
                assert checking.wait(timeout=15)
                pending_reset = pool.submit(independently, recover)
                pending_reset.result(timeout=15)
            finally:
                resume.set()
            status, client = pending_login.result(timeout=30)
            pending_reset.result(timeout=30)
    user.refresh_from_db()
    assert check_password(NEW_PASSWORD, user.password)
    assert not check_password(PASSWORD, user.password)
    assert status == 401
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False


@pytest.mark.django_db(transaction=True)
def test_verification_worker_skips_a_recipient_that_no_longer_matches(data):
    user = register_customer(data=data)
    User.objects.filter(pk=user.pk).update(email="replacement@example.invalid")
    assert process_verification_emails() == (0, 0)
    assert not getattr(mail, "outbox", [])
    job = EmailVerification.objects.get(user=user)
    assert job.attempts == 0 and job.sent_at is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("asynchronous", [False, True])
def test_legacy_hash_still_upgrades_when_credentials_have_not_changed(asynchronous):
    from asgiref.sync import async_to_sync

    user = User.objects.create_user(
        email="legacy@example.invalid", role="ADMINISTRADOR", password=PASSWORD
    )
    user.password = make_password(PASSWORD, hasher="pbkdf2_sha256")
    user.save(update_fields=["password"])
    assert (
        async_to_sync(user.acheck_password)(PASSWORD)
        if asynchronous
        else user.check_password(PASSWORD)
    )
    user.refresh_from_db()
    assert user.password.startswith("argon2$") and check_password(PASSWORD, user.password)


@pytest.mark.django_db(transaction=True)
def test_customer_registration_recovery_and_verification_are_independent(data):
    client = APIClient(enforce_csrf_checks=True)
    csrf(client)
    assert client.post("/api/v1/auth/register/", data, format="json").status_code == 201
    user = User.objects.get(email=data["email"].lower())
    verification = verification_token(EmailVerification.objects.get(user=user))
    assert login(client, user, data["password"]).status_code == 200
    csrf(client)
    assert (
        client.post(
            "/api/v1/auth/password-recovery/", {"email": user.email}, format="json"
        ).status_code
        == 202
    )
    recovery = recovery_token(PasswordRecovery.objects.get(user=user))
    assert (
        client.post(
            "/api/v1/auth/password-reset/",
            {"token": recovery, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
            format="json",
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False
    user.refresh_from_db()
    assert not user.is_email_verified and user.wallet.balance == 0
    # Recuperar no verifica el correo ni consume el enlace de HU-007.
    csrf(client)
    assert (
        client.post(
            "/api/v1/auth/verify-email/", {"token": verification}, format="json"
        ).status_code
        == 200
    )
    assert login(client, user, NEW_PASSWORD).json() == {
        "authenticated": True,
        "role": "CLIENTE",
        "is_email_verified": True,
    }


@pytest.mark.django_db(transaction=True)
def test_root_password_change_invalidates_pending_recovery_and_session(settings, provider):
    from apps.users.recovery_mail import process_recovery_emails
    from apps.users.services import provision_root

    settings.PASSWORD_RECOVERY_FRONTEND_URL = "https://example.invalid/recuperar"
    root, _ = provision_root(
        root_id="root-iteration", email="root@example.invalid", password=PASSWORD
    )
    client = APIClient(enforce_csrf_checks=True)
    csrf(client)
    assert login(client, root).status_code == 200
    csrf(client)
    assert (
        client.post(
            "/api/v1/auth/password-recovery/", {"email": root.email}, format="json"
        ).status_code
        == 202
    )
    job = PasswordRecovery.objects.get(user=root)
    token = recovery_token(job)
    assert (
        client.post(
            "/api/v1/users/root/password/",
            {
                "current_password": PASSWORD,
                "password": NEW_PASSWORD,
                "password_confirmation": NEW_PASSWORD,
            },
            format="json",
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False
    csrf(client)
    response = client.post(
        "/api/v1/auth/password-reset/",
        {"token": token, "password": PASSWORD, "password_confirmation": PASSWORD},
        format="json",
    )
    assert response.status_code == 400 and response.json()["code"] == "recovery_invalid"
    assert process_recovery_emails() == (0, 0)
    job.refresh_from_db()
    assert job.superseded_at is not None and job.sent_at is None
    root.refresh_from_db()
    assert check_password(NEW_PASSWORD, root.password) and not root.is_email_verified
    assert login(client, root, NEW_PASSWORD).status_code == 200
