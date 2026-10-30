from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core import mail, signing
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.users.errors import (
    EmailAlreadyRegistered,
    ExpiredVerification,
    InvalidVerification,
    RegistrationUnavailable,
    UsedVerification,
)
from apps.users.mail import process_verification_emails
from apps.users.models import EmailVerification, RegistrationConsent, RegistrationEvent, User
from apps.users.permissions import HasVerifiedEmail
from apps.users.services import (
    VERIFICATION_SALT,
    confirm_email,
    register_customer,
    verification_token,
)
from apps.wallets.models import Wallet

PASSWORD = "prueba-larga-con-varias-palabras-2026"


@pytest.fixture
def registration_settings(settings, tmp_path, provider):
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private-media"
    settings.REGISTRATION_PRODUCTION = False
    settings.REGISTRATION_POLICY_IS_TEST = True
    settings.REGISTRATION_POLICY_REFERENCE = "synthetic-policy-test-v1"
    settings.REGISTRATION_POLICY_VERSION = "test-v1"
    settings.REGISTRATION_POLICY_URL = "https://example.invalid/synthetic-policy"
    settings.EMAIL_VERIFICATION_FRONTEND_URL = "https://example.invalid/verificar"
    return settings


@pytest.fixture
def data(registration_settings):
    return {
        "email": "Persona@Example.invalid",
        "username": "viajero",
        "first_name": "Persona",
        "last_name": "De Prueba",
        "document_number": "00123456",
        "birth_date": "1995-06-15",
        "birth_place": "Pereira",
        "billing_address": "Dirección ficticia",
        "gender": "dato de prueba",
        "password": PASSWORD,
        "accepts_data_policy": True,
        "policy_reference": "synthetic-policy-test-v1",
        "policy_version": "test-v1",
    }


@pytest.fixture
def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    client.credentials(HTTP_X_CSRFTOKEN=response.json()["csrf_token"])
    return client


@pytest.mark.django_db
def test_register_creates_client_consent_wallet_and_durable_delivery_together(data):
    user = register_customer(data=data)
    assert user.role == User.Role.CLIENTE
    assert user.email == "persona@example.invalid"
    assert not user.is_email_verified and not user.is_staff and not user.is_superuser
    assert user.check_password(PASSWORD)
    assert user.password.startswith("argon2$argon2id$")
    assert user.wallet.balance == 0
    assert "created_at" not in {f.name for f in Wallet._meta.fields}
    assert "creada_en" not in {f.name for f in Wallet._meta.fields}
    assert user.registration_consent.policy_reference == data["policy_reference"]
    job = EmailVerification.objects.get(user=user)
    assert job.recipient == user.email and job.sent_at is None
    assert job.expires_at - job.created_at == timedelta(hours=24)
    assert RegistrationEvent.objects.get().kind == "registered"
    assert not getattr(mail, "outbox", [])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "username",
        "email",
        "first_name",
        "last_name",
        "document_number",
        "birth_date",
        "birth_place",
        "billing_address",
        "gender",
        "password",
        "accepts_data_policy",
        "policy_reference",
        "policy_version",
    ],
)
def test_required_fields_are_rejected_without_persistence(data, field):
    data.pop(field)
    with pytest.raises(ValidationError) as exc:
        register_customer(data=data)
    assert field in exc.value.detail
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes,field",
    [
        ({"accepts_data_policy": False}, "accepts_data_policy"),
        ({"policy_reference": "old-policy"}, "policy_reference"),
        ({"email": "bad-email"}, "email"),
        ({"birth_date": "bad-date"}, "birth_date"),
        ({"first_name": "  "}, "first_name"),
        ({"password": "too-short"}, "password"),
        ({"password": "1234567890123456"}, "password"),
        ({"password": "1234567890qwertyuiop"}, "password"),
        ({"password": "persona@example.invalid"}, "password"),
    ],
)
def test_invalid_values_and_framework_password_validators(data, changes, field):
    data.update(changes)
    with pytest.raises(ValidationError) as exc:
        register_customer(data=data)
    assert field in exc.value.detail
    assert not User.objects.exists()


@pytest.mark.django_db
def test_document_type_is_optional_and_not_a_fabricated_catalog(data):
    data["document_type"] = "tipo de prueba"
    assert register_customer(data=data).document_type == "tipo de prueba"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "ROOT"),
        ("root_id", "root"),
        ("is_staff", True),
        ("is_superuser", True),
        ("is_email_verified", True),
        ("balance", "100"),
        ("is_active", False),
        ("date_joined", "2020-01-01"),
        ("profile_image_url", "https://example.invalid/image.png"),
        ("image", "not-a-file"),
    ],
)
def test_internal_or_unknown_fields_cannot_be_submitted(data, field, value):
    data[field] = value
    with pytest.raises(ValidationError) as exc:
        register_customer(data=data)
    assert field in exc.value.detail
    assert not User.objects.exists()


@pytest.mark.django_db
def test_case_insensitive_duplicate_and_document_reuse(data):
    first = register_customer(data=data)
    data["email"] = "PERSONA@EXAMPLE.INVALID"
    with pytest.raises(EmailAlreadyRegistered):
        register_customer(data=data)
    assert User.objects.count() == Wallet.objects.count() == EmailVerification.objects.count() == 1
    data["email"] = "another@example.invalid"
    second = register_customer(data=data)
    assert first.document_number == second.document_number
    assert User.objects.count() == Wallet.objects.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target",
    [
        "Wallet.objects.create",
        "RegistrationConsent.objects.create",
        "EmailVerification.objects.create",
        "RegistrationEvent.objects.create",
    ],
)
def test_persistence_failure_rolls_back_entire_registration(data, target):
    with patch("apps.users.services." + target, side_effect=IntegrityError("synthetic")):
        with pytest.raises(IntegrityError):
            register_customer(data=data)
    for model in [User, Wallet, RegistrationConsent, EmailVerification, RegistrationEvent]:
        assert not model.objects.exists()


@pytest.mark.django_db
def test_verification_is_single_use_and_never_unverifies_on_reuse(data):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    token = verification_token(job)
    confirm_email(token=token)
    with pytest.raises(UsedVerification):
        confirm_email(token=token)
    user.refresh_from_db()
    job.refresh_from_db()
    assert user.is_email_verified and job.consumed_at
    assert RegistrationEvent.objects.filter(kind="verified").count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("offset,expired", [(-1, False), (0, True), (1, True)])
def test_verification_expiration_boundary_uses_a_deterministic_clock(data, offset, expired):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    with patch(
        "apps.users.services.timezone.now", return_value=job.expires_at + timedelta(seconds=offset)
    ):
        if expired:
            with pytest.raises(ExpiredVerification):
                confirm_email(token=verification_token(job))
        else:
            confirm_email(token=verification_token(job))
    user.refresh_from_db()
    assert user.is_email_verified is not expired


@pytest.mark.django_db
def test_invalid_signature_wrong_purpose_missing_or_cross_account_cannot_verify(data):
    first = register_customer(data=data)
    data["email"] = "second@example.invalid"
    second = register_customer(data=data)
    job = EmailVerification.objects.get(user=first)
    payload = {"delivery": job.pk, "account": first.pk}
    tokens = [
        "invalid",
        verification_token(job) + "x",
        signing.Signer(salt="different-purpose").sign_object(payload),
        signing.Signer(salt=VERIFICATION_SALT).sign_object({**payload, "account": second.pk}),
        signing.Signer(salt=VERIFICATION_SALT).sign_object({**payload, "delivery": 999999}),
        signing.Signer(salt=VERIFICATION_SALT).sign_object({**payload, "account": 999999}),
        signing.Signer(salt=VERIFICATION_SALT).sign_object({**payload, "account": 2**80}),
        signing.Signer(salt=VERIFICATION_SALT).sign_object([]),
    ]
    for token in tokens:
        with pytest.raises(InvalidVerification):
            confirm_email(token=token)
    assert not User.objects.filter(is_email_verified=True).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["email", "inactive", "role"])
def test_token_is_bound_to_the_current_active_customer_email(data, change):
    user = register_customer(data=data)
    token = verification_token(EmailVerification.objects.get(user=user))
    if change == "email":
        user.email = "changed@example.invalid"
    elif change == "inactive":
        user.is_active = False
    else:
        user.role = User.Role.ADMINISTRADOR
    user.save()
    with pytest.raises(InvalidVerification):
        confirm_email(token=token)


@pytest.mark.django_db
def test_verification_event_failure_rolls_back_consumption(data):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    with patch("apps.users.services.RegistrationEvent.objects.create", side_effect=IntegrityError):
        with pytest.raises(IntegrityError):
            confirm_email(token=verification_token(job))
    user.refresh_from_db()
    job.refresh_from_db()
    assert not user.is_email_verified and job.consumed_at is None


@pytest.mark.django_db
def test_database_limits_verification_lifetime(data):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    for lifetime in [timedelta(0), timedelta(hours=24, seconds=1)]:
        with pytest.raises(IntegrityError), transaction.atomic():
            EmailVerification.objects.filter(pk=job.pk).update(expires_at=job.created_at + lifetime)


def run_independently(function):
    close_old_connections()
    try:
        return function()
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_simultaneous_registrations_return_one_success_and_one_conflict(data, monkeypatch):
    barrier = Barrier(2)
    original_save = User.save

    def simultaneous_save(self, *args, **kwargs):
        barrier.wait(timeout=15)
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(User, "save", simultaneous_save)

    def register():
        try:
            register_customer(data=data)
            return 201
        except EmailAlreadyRegistered:
            return 409

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_independently, register) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [201, 409]
    assert User.objects.count() == Wallet.objects.count() == EmailVerification.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_confirmations_apply_one_effect(data):
    user = register_customer(data=data)
    token = verification_token(EmailVerification.objects.get(user=user))
    barrier = Barrier(2)

    def confirm():
        barrier.wait(timeout=15)
        try:
            confirm_email(token=token)
            return 200
        except UsedVerification:
            return 409

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_independently, confirm) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [200, 409]
    assert RegistrationEvent.objects.filter(kind="verified").count() == 1


@pytest.mark.django_db(transaction=True)
def test_mail_failure_retains_account_and_retries_durable_job(data, monkeypatch):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    with patch("apps.users.mail.send_mail", side_effect=RuntimeError("private-smtp-details")):
        assert process_verification_emails() == (0, 1)
    job.refresh_from_db()
    user.refresh_from_db()
    assert not user.is_email_verified and user.wallet.balance == 0
    assert job.sent_at is None and job.attempts == 1 and job.last_error == "mail_unavailable"
    assert process_verification_emails() == (0, 0)
    monkeypatch.setattr("apps.users.mail.timezone.now", lambda: job.next_attempt_at)
    assert process_verification_emails() == (1, 0)
    job.refresh_from_db()
    assert job.attempts == 2 and job.sent_at and not job.last_error
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    link = mail.outbox[0].body.split()[1]
    token = parse_qs(urlsplit(link).fragment)["token"][0]
    confirm_email(token=token)
    assert process_verification_emails() == (0, 0)
    events = str(list(RegistrationEvent.objects.values()))
    assert token not in events and PASSWORD not in events and user.email not in events
    assert "private-smtp-details" not in events


@pytest.mark.django_db(transaction=True)
def test_abandoned_lease_is_recovered_only_after_timeout(data, monkeypatch):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    lease_end = timezone.now() + timedelta(minutes=5)
    EmailVerification.objects.filter(pk=job.pk).update(lease_id=uuid4(), lease_until=lease_end)
    assert process_verification_emails() == (0, 0)
    monkeypatch.setattr("apps.users.mail.timezone.now", lambda: lease_end)
    assert process_verification_emails() == (1, 0)


@pytest.mark.django_db(transaction=True)
def test_two_processors_do_not_send_the_same_claimed_job(data, monkeypatch):
    register_customer(data=data)
    sending = Event()
    release = Event()
    real_send = mail.send_mail

    def send(*args, **kwargs):
        assert not transaction.get_connection().in_atomic_block
        sending.set()
        assert release.wait(timeout=15)
        return real_send(*args, **kwargs)

    monkeypatch.setattr("apps.users.mail.send_mail", send)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run_independently, lambda: process_verification_emails(batch_size=1))
        assert sending.wait(timeout=15)
        second = pool.submit(run_independently, lambda: process_verification_emails(batch_size=1))
        try:
            second_result = second.result(timeout=15)
        finally:
            release.set()
        results = [first.result(timeout=30), second_result]
    assert sum(result[0] for result in results) == 1
    assert EmailVerification.objects.get().attempts == 1


@pytest.mark.django_db
def test_processor_refuses_uncommitted_work(data):
    register_customer(data=data)
    with pytest.raises(RuntimeError, match="commit"):
        process_verification_emails()


@pytest.mark.django_db(transaction=True)
def test_command_does_not_send_expired_or_consumed_verifications(data, capsys):
    register_customer(data=data)
    job = EmailVerification.objects.get()
    confirm_email(token=verification_token(job))
    call_command("process_verification_emails", batch_size=1)
    assert "Enviados: 0" in capsys.readouterr().out
    assert not getattr(mail, "outbox", [])


@pytest.mark.django_db(transaction=True)
def test_expired_delivery_is_not_sent_or_renewed(data, monkeypatch):
    register_customer(data=data)
    job = EmailVerification.objects.get()
    monkeypatch.setattr("apps.users.mail.timezone.now", lambda: job.expires_at)
    assert process_verification_emails() == (0, 0)
    job.refresh_from_db()
    assert job.attempts == 0 and job.sent_at is None
    assert User.objects.count() == Wallet.objects.count() == EmailVerification.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_processor_rejects_missing_or_unsafe_frontend_url(registration_settings):
    for value in [
        "",
        "https://example.invalid/page?token=x",
        "https://example.invalid/#x",
        "http://example.invalid",
    ]:
        registration_settings.EMAIL_VERIFICATION_FRONTEND_URL = value
        with pytest.raises(ImproperlyConfigured):
            process_verification_emails()


@pytest.mark.django_db
def test_unapproved_policy_disables_production_registration(data, csrf_client, settings):
    settings.REGISTRATION_PRODUCTION = True
    response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 503
    assert response.json()["code"] == "registration_unavailable"
    assert not User.objects.exists()


@pytest.mark.django_db
def test_api_contract_of_prepared_registration_has_no_secrets_or_automatic_login(
    data,
    csrf_client,
    settings,
):
    # Documento sintético y HTTP simulado; no se atribuye aprobación legal.
    response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 201
    assert response.json() == {"status": "unverified", "delivery": "pending"}
    assert "sessionid" not in csrf_client.cookies
    assert PASSWORD not in response.content.decode()
    response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "email_already_registered"


@pytest.mark.django_db
def test_api_persistence_failure_has_no_partial_data_or_sensitive_error(
    data,
    csrf_client,
    settings,
    caplog,
):
    with patch("apps.users.services.Wallet.objects.create", side_effect=IntegrityError("private")):
        response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Error interno del servidor.",
        "details": {},
    }
    for secret in ["private", data["email"], PASSWORD]:
        assert secret not in response.content.decode()
        assert secret not in caplog.text
    assert not User.objects.exists() and not Wallet.objects.exists()


@pytest.mark.django_db
def test_public_post_csrf_requires_cookie_header_and_valid_origin(data, settings):
    client = APIClient(enforce_csrf_checks=True)
    for route in ["register", "verify-email"]:
        path = f"/api/v1/auth/{route}/"
        assert client.post(path, data, format="json").json()["code"] == "csrf_failed"
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/register/",
        data,
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://foreign.example.invalid",
    )
    assert response.status_code == 403 and response.json()["code"] == "csrf_failed"
    assert not User.objects.exists()


@pytest.mark.django_db
def test_confirmation_http_statuses_and_get_cannot_consume(data, csrf_client, monkeypatch):
    user = register_customer(data=data)
    job = EmailVerification.objects.get(user=user)
    path = "/api/v1/auth/verify-email/"
    token = verification_token(job)
    assert csrf_client.get(path, {"token": token}).status_code == 405
    assert csrf_client.post(path, {"token": "bad"}, format="json").status_code == 400
    monkeypatch.setattr("apps.users.services.timezone.now", lambda: job.expires_at)
    response = csrf_client.post(path, {"token": token}, format="json")
    assert response.status_code == 410 and response.json()["code"] == "verification_expired"
    monkeypatch.setattr("apps.users.services.timezone.now", lambda: job.created_at)
    assert csrf_client.post(path, {"token": token}, format="json").json() == {"status": "verified"}
    response = csrf_client.post(path, {"token": token}, format="json")
    assert response.status_code == 409 and response.json()["code"] == "verification_used"
    assert token not in response.content.decode()


@pytest.mark.django_db
def test_non_object_json_returns_field_validation_error(data, settings, csrf_client):
    for value in [[], [{"email": "test@example.invalid"}], "invalid", None]:
        response = csrf_client.post("/api/v1/auth/register/", value, format="json")
        assert response.status_code == 400


def test_reusable_verification_permission_includes_active_account():
    permission = HasVerifiedEmail()
    assert not permission.has_permission(SimpleNamespace(user=AnonymousUser()), None)
    user = User(is_email_verified=False)
    assert not permission.has_permission(SimpleNamespace(user=user), None)
    user.is_email_verified = True
    assert permission.has_permission(SimpleNamespace(user=user), None)
    user.is_active = False
    assert not permission.has_permission(SimpleNamespace(user=user), None)


def test_service_cannot_accept_an_unpublished_policy(data, settings):
    settings.REGISTRATION_POLICY_URL = ""
    with pytest.raises(RegistrationUnavailable):
        register_customer(data=data)



@pytest.mark.django_db
def test_registration_accepts_phone(data, csrf_client, settings):
    payload = {
        **data,
        "email": "customer_phone@example.invalid",
        "username": "customer_phone",
        "phone": "+57 300 1234567",
    }
    response = csrf_client.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == 201
    assert response.json() == {"status": "unverified", "delivery": "pending"}
    user = User.objects.get(email="customer_phone@example.invalid")
    assert user.role == User.Role.CLIENTE
