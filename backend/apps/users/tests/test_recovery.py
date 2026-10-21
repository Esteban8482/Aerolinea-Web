from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.core import mail, signing
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users import auth_services
from apps.users.auth_services import recovery_token, request_recovery, reset_password
from apps.users.errors import (
    ExpiredRecovery,
    InvalidRecovery,
    UsedRecovery,
)
from apps.users.models import AccountSession, AuthenticationEvent, PasswordRecovery, User
from apps.users.recovery_mail import process_recovery_emails
from apps.users.tests.conftest import range_body
from apps.users.tests.test_authentication import (
    AUTH,
    PASSWORD,
    csrf,
    independently,
    login,
)
from apps.users.tests.test_authentication import (
    account as account,
)
from apps.users.tests.test_authentication import (
    client as client,
)
from apps.users.tests.test_authentication import (
    clock as clock,
)

NEW_PASSWORD = "nueva-clave-sintetica-distinta-para-pruebas-2026"


@pytest.fixture
def recovery_settings(settings, provider):
    settings.PASSWORD_RECOVERY_FRONTEND_URL = "https://example.invalid/restablecer"
    return settings


@pytest.fixture
def job(account, recovery_settings):
    request_recovery(email=account.email, origin="192.0.2.1")
    return PasswordRecovery.objects.get()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind", ["active", "unverified", "inactive", "unknown", "unusable", "root"]
)
def test_request_is_generic_and_delivery_is_only_for_eligible_accounts(
    client, account, recovery_settings, kind
):
    email = account.email
    if kind == "root":
        account = User.objects.create_root(
            root_id="root", email="root@example.invalid", password=PASSWORD
        )
        email = account.email
    elif kind == "unknown":
        email = "unknown@example.invalid"
    elif kind == "inactive":
        account.is_active = False
        account.save(update_fields=["is_active"])
    elif kind == "unusable":
        account.set_unusable_password()
        account.save(update_fields=["password"])
    response = client.post(AUTH + "password-recovery/", {"email": email.upper()}, format="json")
    assert response.status_code == 202 and response.json() == {"status": "requested"}
    eligible = kind in {"active", "unverified", "root"}
    assert PasswordRecovery.objects.count() == int(eligible)
    if eligible:
        job = PasswordRecovery.objects.get()
        assert job.expires_at - job.created_at == timedelta(minutes=30)
        assert job.recipient == email and job.sent_at is None and job.attempts == 0
        assert job.password_fingerprint != account.password
        assert recovery_token(job) not in response.content.decode()
    assert not getattr(mail, "outbox", [])


@pytest.mark.django_db
def test_root_without_email_has_no_alternative_recovery_contract(client, recovery_settings):
    root = User.objects.create_root(root_id="no-email-root", password=PASSWORD)
    assert root.email is None
    assert (
        client.post(
            AUTH + "password-recovery/", {"root_id": root.root_id}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            AUTH + "password-recovery/", {"email": "unknown@example.invalid"}, format="json"
        ).status_code
        == 202
    )
    assert not PasswordRecovery.objects.exists()


@pytest.mark.django_db
def test_recovery_limits_apply_to_unknown_accounts_and_new_link_replaces_old(
    client, account, recovery_settings, clock
):
    start = clock.now
    data = {"email": account.email}
    path = AUTH + "password-recovery/"
    assert client.post(path, data, format="json").status_code == 202
    old = PasswordRecovery.objects.get()
    assert client.post(path, data, format="json").status_code == 429
    clock.now = start + timedelta(seconds=60)
    assert client.post(path, data, format="json").status_code == 202
    old.refresh_from_db()
    assert old.superseded_at
    with pytest.raises(InvalidRecovery):
        reset_password(token=recovery_token(old), password=NEW_PASSWORD, origin="test")
    clock.now = start + timedelta(seconds=120)
    assert client.post(path, data, format="json").status_code == 202
    clock.now = start + timedelta(seconds=180)
    assert client.post(path, data, format="json", REMOTE_ADDR="192.0.2.9").status_code == 429
    assert PasswordRecovery.objects.count() == 3
    unknown = {"email": "unknown@example.invalid"}
    assert client.post(path, unknown, format="json").status_code == 202
    assert client.post(path, unknown, format="json").status_code == 429


@pytest.mark.django_db
def test_recovery_origin_limit_is_shared_and_applies_to_unknown_addresses(
    client, recovery_settings
):
    for i in range(20):
        assert (
            client.post(
                AUTH + "password-recovery/", {"email": f"unknown{i}@example.invalid"}, format="json"
            ).status_code
            == 202
        )
    response = client.post(
        AUTH + "password-recovery/", {"email": "last@example.invalid"}, format="json"
    )
    assert response.status_code == 429 and int(response["Retry-After"]) <= 3600
    assert not PasswordRecovery.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "token_kind",
    [
        "bad",
        "purpose",
        "shape",
        "wrong_account",
        "expired",
        "used",
        "inactive",
        "email_changed",
        "password_changed",
    ],
)
def test_invalid_expired_used_and_wrong_purpose_tokens(job, account, token_kind, clock):
    token = recovery_token(job)
    error = InvalidRecovery
    if token_kind == "bad":
        token += "tampered"
    elif token_kind == "purpose":
        token = signing.Signer(salt="users.HU007.email-verification.v1").sign_object(
            {"recovery": job.pk, "account": account.pk}
        )
    elif token_kind == "shape":
        token = signing.Signer(salt=auth_services.RECOVERY_SALT).sign_object([job.pk, account.pk])
    elif token_kind == "wrong_account":
        token = signing.Signer(salt=auth_services.RECOVERY_SALT).sign_object(
            {"recovery": job.pk, "account": account.pk + 999}
        )
    elif token_kind == "expired":
        clock.now = job.expires_at
        error = ExpiredRecovery
    elif token_kind == "used":
        job.consumed_at = timezone.now()
        job.save(update_fields=["consumed_at"])
        error = UsedRecovery
    elif token_kind == "inactive":
        account.is_active = False
        account.save(update_fields=["is_active"])
    elif token_kind == "email_changed":
        account.email = "changed@example.invalid"
        account.save(update_fields=["email"])
    else:
        account.set_password("another-synthetic-password")
        account.save(update_fields=["password"])
    with pytest.raises(error):
        reset_password(token=token, password=NEW_PASSWORD, origin="test")
    assert not account.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_reset_consumes_token_once_and_keeps_mail_unverified(job, account, client):
    token = recovery_token(job)
    assert client.get(AUTH + "password-reset/", {"token": token}).status_code == 405
    job.refresh_from_db()
    assert job.consumed_at is None
    response = client.post(
        AUTH + "password-reset/",
        {"token": token, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200 and response.json() == {"status": "password_reset"}
    account.refresh_from_db()
    assert account.check_password(NEW_PASSWORD) and not account.check_password(PASSWORD)
    assert account.password.startswith("argon2$argon2id$") and not account.is_email_verified
    assert client.get(AUTH + "session/").json()["authenticated"] is False
    assert (
        client.post(
            AUTH + "password-reset/",
            {"token": token, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
            format="json",
        ).status_code
        == 409
    )
    assert AuthenticationEvent.objects.filter(kind="password_reset").count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("failure", ["weak", "compromised", "provider"])
def test_failed_password_check_keeps_old_password_and_unused_token(
    job, account, client, provider, failure
):
    password = NEW_PASSWORD
    if failure == "weak":
        password = "short"
    elif failure == "compromised":
        import hashlib

        value = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()
        provider["body"] = range_body(suffix=value[5:])
    else:
        provider["error"] = TimeoutError("private-failure")
    response = client.post(
        AUTH + "password-reset/",
        {"token": recovery_token(job), "password": password, "password_confirmation": password},
        format="json",
    )
    assert response.status_code == (503 if failure == "provider" else 400)
    if failure == "provider":
        assert response.json()["code"] == "password_check_unavailable"
    account.refresh_from_db()
    job.refresh_from_db()
    assert account.check_password(PASSWORD) and job.consumed_at is None
    assert not AuthenticationEvent.objects.filter(kind="password_reset").exists()


@pytest.mark.django_db
def test_reset_invalidates_every_session_including_requester(job, account, client):
    second = APIClient(enforce_csrf_checks=True)
    csrf(second)
    assert login(client, account).status_code == 200
    assert login(second, account).status_code == 200
    assert AccountSession.objects.count() == 2
    csrf(client)
    assert (
        client.post(
            AUTH + "password-reset/",
            {
                "token": recovery_token(job),
                "password": NEW_PASSWORD,
                "password_confirmation": NEW_PASSWORD,
            },
            format="json",
        ).status_code
        == 200
    )
    assert client.get(AUTH + "session/").json()["authenticated"] is False
    assert second.get(AUTH + "session/").json()["authenticated"] is False
    assert not AccountSession.objects.exists()


@pytest.mark.django_db
def test_reset_persistence_failure_rolls_back_password_token_and_audit(job, account):
    with patch("apps.users.auth_services.audit", side_effect=IntegrityError("synthetic")):
        with pytest.raises(IntegrityError):
            reset_password(token=recovery_token(job), password=NEW_PASSWORD, origin="test")
    account.refresh_from_db()
    job.refresh_from_db()
    assert account.check_password(PASSWORD) and job.consumed_at is None


@pytest.mark.django_db(transaction=True)
def test_concurrent_consumption_has_one_effect_and_external_check_holds_no_locks(
    job, account, monkeypatch
):
    barrier = Barrier(2)
    original = auth_services.validate_registration_password

    def checked(password):
        assert not connection.in_atomic_block
        barrier.wait(timeout=15)
        return original(password)

    monkeypatch.setattr(auth_services, "validate_registration_password", checked)

    def run():
        try:
            reset_password(token=recovery_token(job), password=NEW_PASSWORD, origin="test")
            return 200
        except UsedRecovery:
            return 409

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(independently, run) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [200, 409]
    assert AuthenticationEvent.objects.filter(kind="password_reset").count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("change", ["inactive", "superseded", "email", "expired"])
def test_token_and_account_are_revalidated_after_external_check(
    job, account, monkeypatch, clock, change
):
    original = auth_services.validate_registration_password

    def checked(password):
        assert not connection.in_atomic_block
        original(password)
        if change == "inactive":
            User.objects.filter(pk=account.pk).update(is_active=False)
        elif change == "superseded":
            PasswordRecovery.objects.filter(pk=job.pk).update(superseded_at=timezone.now())
        elif change == "email":
            User.objects.filter(pk=account.pk).update(email="changed@example.invalid")
        else:
            clock.now = job.expires_at

    monkeypatch.setattr(auth_services, "validate_registration_password", checked)
    with pytest.raises(ExpiredRecovery if change == "expired" else InvalidRecovery):
        reset_password(token=recovery_token(job), password=NEW_PASSWORD, origin="test")
    account.refresh_from_db()
    job.refresh_from_db()
    assert account.check_password(PASSWORD) and job.consumed_at is None


@pytest.mark.django_db(transaction=True)
def test_recovery_mail_after_commit_retries_without_exposing_exception(job, account, clock, caplog):
    original = __import__("django.core.mail", fromlist=["send_mail"]).send_mail

    def send(*args, **kwargs):
        assert not connection.in_atomic_block
        return original(*args, **kwargs)

    with patch(
        "apps.users.recovery_mail.send_mail",
        side_effect=RuntimeError("secret-password token recipient"),
    ):
        assert process_recovery_emails() == (0, 1)
    job.refresh_from_db()
    assert job.last_error == "mail_unavailable" and job.attempts == 1
    assert process_recovery_emails() == (0, 0)
    clock.now = job.next_attempt_at
    with patch("apps.users.recovery_mail.send_mail", side_effect=send):
        assert process_recovery_emails() == (1, 0)
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [account.email]
    link = mail.outbox[0].body.split("Abre ", 1)[1].splitlines()[0]
    assert urlsplit(link).query == "" and "token" in parse_qs(urlsplit(link).fragment)
    token = parse_qs(urlsplit(link).fragment)["token"][0]
    assert token == recovery_token(job)
    serialized = str(list(AuthenticationEvent.objects.values())) + caplog.text
    for sensitive in [PASSWORD, token, account.email, "secret-password"]:
        assert sensitive not in serialized


@pytest.mark.django_db(transaction=True)
def test_recovery_mail_lease_recovery_and_superseded_or_inactive_jobs(job, account, clock):
    job.lease_until = clock.now + timedelta(minutes=5)
    job.save(update_fields=["lease_until"])
    assert process_recovery_emails() == (0, 0)
    clock.now = job.lease_until
    assert process_recovery_emails() == (1, 0)
    request_recovery(email=account.email, origin="test")
    job = PasswordRecovery.objects.latest("pk")
    account.is_active = False
    account.save(update_fields=["is_active"])
    assert process_recovery_emails() == (0, 0)
    account.is_active = True
    account.save(update_fields=["is_active"])
    request_recovery(email=account.email, origin="test")
    assert process_recovery_emails() == (1, 0)
    job.refresh_from_db()
    assert job.superseded_at and job.sent_at is None


@pytest.mark.django_db(transaction=True)
def test_concurrent_mail_processors_do_not_claim_the_same_job(job):
    claimed = Event()
    release = Event()

    def send(*args, **kwargs):
        assert not connection.in_atomic_block
        claimed.set()
        assert release.wait(timeout=15)
        return 1

    with patch("apps.users.recovery_mail.send_mail", side_effect=send):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(independently, lambda: process_recovery_emails(batch_size=1))
            assert claimed.wait(timeout=15)
            second = pool.submit(independently, lambda: process_recovery_emails(batch_size=1))
            assert second.result(timeout=15) == (0, 0)
            release.set()
            assert first.result(timeout=15) == (1, 0)
    job.refresh_from_db()
    assert job.attempts == 1


@pytest.mark.django_db
def test_processor_rejects_uncommitted_delivery(job):
    with transaction.atomic():
        with pytest.raises(RuntimeError, match="commit"):
            process_recovery_emails()
