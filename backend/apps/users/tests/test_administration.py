from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.users import administration_services
from apps.users.administration_services import change_root_password, create_administrator
from apps.users.administrator_mail import process_administrator_notifications
from apps.users.auth_services import private_key
from apps.users.errors import CredentialsChanged, EmailAlreadyRegistered
from apps.users.models import (
    AccountSession,
    AdministrationEvent,
    AdministratorNotification,
    LoginGuard,
    User,
)
from apps.users.permissions import HasVerifiedEmail, IsAdministrator, IsClient
from apps.users.services import provision_root
from apps.users.tests.conftest import range_body
from apps.users.tests.test_authentication import (
    PASSWORD,
    csrf,
    independently,
    login,
)
from apps.users.tests.test_authentication import (
    client as client,
)
from apps.users.tests.test_authentication import (
    clock as clock,
)
from apps.wallets.models import Wallet

URL = "/api/v1/users/administrators/"
PASSWORD_URL = "/api/v1/users/root/password/"
NEW_PASSWORD = "otra-credencial-larga-sintetica-2026"


@pytest.fixture
def root():
    return provision_root(root_id="root-test", password=PASSWORD)[0]


@pytest.fixture
def root_client(client, root, provider):
    assert login(client, root).status_code == 200
    csrf(client)
    return client


@pytest.fixture
def data():
    return {
        "email": "Admin@Example.invalid",
        "password": NEW_PASSWORD,
        "first_name": "Persona",
        "last_name": "De Prueba",
        "document_number": "000009",
    }


def password_data(current=PASSWORD, new=NEW_PASSWORD):
    return {"current_password": current, "password": new, "password_confirmation": new}


@pytest.mark.django_db
def test_create_is_atomic_and_sets_only_business_role(root, root_client, data):
    response = root_client.post(URL, data, format="json")
    assert response.status_code == 201
    user = User.objects.get(role="ADMINISTRADOR")
    assert response.json() == {
        "id": user.pk,
        "email": "admin@example.invalid",
        "first_name": "Persona",
        "last_name": "De Prueba",
        "role": "ADMINISTRADOR",
        "delivery": "pending",
    }
    assert (
        user.is_active
        and not user.is_staff
        and not user.is_superuser
        and not user.is_email_verified
    )
    assert user.document_number == "000009" and user.root_id is None
    assert user.password.startswith("argon2$argon2id$") and user.check_password(data["password"])
    assert Wallet.objects.get(user=user).balance == 0
    assert AdministratorNotification.objects.get(user=user).sent_at is None
    event = AdministrationEvent.objects.get(kind="administrator_created")
    assert event.actor == root and event.target == user
    assert not getattr(mail, "outbox", [])
    administrator = APIClient(enforce_csrf_checks=True)
    csrf(administrator)
    assert login(administrator, user, data["password"]).status_code == 200
    assert administrator.get("/api/v1/auth/session/").json()["role"] == "ADMINISTRADOR"


@pytest.mark.django_db
def test_only_email_and_initial_password_are_required_for_later_profile_completion(root_client):
    response = root_client.post(
        URL, {"email": "minimal@example.invalid", "password": NEW_PASSWORD}, format="json"
    )
    assert response.status_code == 201
    user = User.objects.get(role="ADMINISTRADOR")
    assert user.username == user.first_name == user.last_name == user.document_number == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,technical",
    [(None, False), ("CLIENTE", False), ("ADMINISTRADOR", False), ("ADMINISTRADOR", True)],
)
@pytest.mark.parametrize("operation", ["create", "list", "password"])
def test_other_roles_and_superusers_are_denied_and_audited(
    client, data, role, technical, operation, provider
):
    if role:
        user = User(
            email="outsider@example.invalid", role=role, is_staff=technical, is_superuser=technical
        )
        user.set_password(PASSWORD)
        user.save()
        assert login(client, user).status_code == 200
        csrf(client)
    before = User.objects.count()
    if operation == "list":
        response = client.get(URL)
    else:
        response = client.post(
            URL if operation == "create" else PASSWORD_URL,
            data if operation == "create" else password_data(),
            format="json",
        )
    assert response.status_code == 403
    assert User.objects.count() == before and not AdministratorNotification.objects.exists()
    assert AdministrationEvent.objects.filter(kind="access_denied").count() == 1
    assert not provider["factory"].called


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "role",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "is_active",
        "root_id",
        "id",
        "user_id",
        "wallet",
        "balance",
        "profile_image_url",
        "image",
        "groups",
        "user_permissions",
        "username",
    ],
)
def test_create_rejects_fields_outside_allowlist(root_client, data, field):
    data[field] = True
    response = root_client.post(URL, data, format="json")
    assert response.status_code == 400 and field in response.json()["details"]
    assert not User.objects.filter(role="ADMINISTRADOR").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value",
    [
        {},
        {"email": "bad", "password": NEW_PASSWORD},
        {"email": "a@example.invalid", "password": "short"},
        {"email": "a@example.invalid", "password": NEW_PASSWORD, "document_number": "x" * 21},
        [],
    ],
)
def test_invalid_inputs_never_create_partial_accounts(root_client, value):
    response = root_client.post(URL, value, format="json")
    assert response.status_code == 400
    assert User.objects.count() == Wallet.objects.count() == 1
    assert not AdministratorNotification.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["ROOT", "CLIENTE", "ADMINISTRADOR"])
def test_duplicate_email_is_case_insensitive_across_roles(root, root_client, data, role):
    if role == "ROOT":
        root.email = data["email"].lower()
        root.save(update_fields=["email"])
    else:
        User.objects.create(email=data["email"].lower(), role=role)
    before = User.objects.count()
    response = root_client.post(URL, data, format="json")
    assert response.status_code == 409 and response.json()["code"] == "email_already_registered"
    assert User.objects.count() == before and not AdministratorNotification.objects.exists()


@pytest.mark.django_db
def test_document_can_repeat_and_listing_contains_only_authorized_admin_fields(root_client, data):
    for i in range(2):
        data["email"] = f"admin{i}@example.invalid"
        assert root_client.post(URL, data, format="json").status_code == 201
    User.objects.create(email="client@example.invalid", role="CLIENTE")
    response = root_client.get(URL, {"role": "CLIENTE"})
    assert response.status_code == 200
    assert response.json()["count"] == 2
    for item in response.json()["results"]:
        assert set(item) == {"id", "email", "first_name", "last_name", "role"}
        assert item["role"] == "ADMINISTRADOR"
    assert User.objects.filter(document_number="000009").count() == 2
    assert root_client.get(URL + "1/").status_code == 404
    for method in ["put", "patch", "delete"]:
        assert getattr(root_client, method)(URL, {}, format="json").status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["provider", "compromised"])
def test_compromised_password_or_provider_failure_has_no_partial_persistence(
    root_client, data, provider, kind
):
    import hashlib

    if kind == "provider":
        provider["error"] = TimeoutError("private-provider-failure")
    else:
        value = hashlib.sha1(data["password"].encode(), usedforsecurity=False).hexdigest().upper()
        provider["body"] = range_body(suffix=value[5:])
    response = root_client.post(URL, data, format="json")
    assert response.status_code == (503 if kind == "provider" else 400)
    assert User.objects.count() == Wallet.objects.count() == 1
    assert (
        not AdministratorNotification.objects.exists() and not AdministrationEvent.objects.exists()
    )


@pytest.mark.django_db
@pytest.mark.parametrize("stage", ["wallet", "notification", "event"])
def test_creation_rolls_back_every_business_record(root, root_client, data, stage):
    paths = {
        "wallet": "Wallet.objects.create",
        "notification": "AdministratorNotification.objects.create",
        "event": "AdministrationEvent.objects.create",
    }
    with patch(
        "apps.users.administration_services." + paths[stage],
        side_effect=IntegrityError("private-details"),
    ):
        response = root_client.post(URL, data, format="json")
    assert response.status_code == 500 and response.json()["code"] == "internal_error"
    assert User.objects.count() == Wallet.objects.count() == 1
    assert (
        not AdministratorNotification.objects.exists() and not AdministrationEvent.objects.exists()
    )


@pytest.mark.django_db
def test_create_quotas_are_shared_by_root_sessions_and_exclude_denied_roles(
    root, root_client, clock
):
    for _ in range(10):
        assert root_client.post(URL, {}, format="json").status_code == 400
    response = root_client.post(URL, {}, format="json", REMOTE_ADDR="192.0.2.7")
    assert response.status_code == 429 and int(response["Retry-After"]) == 3600
    clock.now += timedelta(seconds=3600)
    # La sesión venció antes que la cuota: volver a autenticar no reinicia los contadores.
    assert login(root_client, root).status_code == 200
    csrf(root_client)
    assert root_client.post(URL, {}, format="json").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("path", [URL, PASSWORD_URL])
def test_mutations_require_csrf_and_reject_foreign_origins(root, root_client, path):
    root_client.credentials()
    assert root_client.post(path, {}, format="json").status_code == 403
    token = csrf(root_client)
    assert (
        root_client.post(
            path,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://foreign.example.invalid",
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_password_change_invalidates_all_root_sessions_and_only_changes_own_account(
    root_client, root
):
    second = APIClient(enforce_csrf_checks=True)
    csrf(second)
    assert login(second, root).status_code == 200
    csrf(second)
    assert AccountSession.objects.filter(user=root).count() == 2
    assert root_client.post(PASSWORD_URL, password_data(), format="json").json() == {
        "status": "password_changed"
    }
    root.refresh_from_db()
    assert root.check_password(NEW_PASSWORD) and not root.is_email_verified
    assert root_client.get("/api/v1/auth/session/").json()["authenticated"] is False
    assert second.get("/api/v1/auth/session/").json()["authenticated"] is False
    assert (
        AdministrationEvent.objects.filter(
            kind="root_password_changed", actor=root, target=root
        ).count()
        == 1
    )


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["user_id", "id", "root_id", "email", "role"])
def test_root_cannot_target_another_account_via_password_contract(root_client, field):
    data = password_data()
    data[field] = "other-user"
    response = root_client.post(PASSWORD_URL, data, format="json")
    assert response.status_code == 400 and field in response.json()["details"]


@pytest.mark.django_db
@pytest.mark.parametrize("failure", ["current", "weak", "confirmation", "provider"])
def test_failed_password_change_keeps_password_and_session(root, root_client, provider, failure):
    data = password_data()
    if failure == "current":
        data["current_password"] = "wrong-password"
    elif failure == "weak":
        data["password"] = data["password_confirmation"] = "short"
    elif failure == "confirmation":
        data["password_confirmation"] = "different"
    else:
        provider["error"] = TimeoutError("private-provider-failure")
    response = root_client.post(PASSWORD_URL, data, format="json")
    assert response.status_code == (
        401 if failure == "current" else 503 if failure == "provider" else 400
    )
    root.refresh_from_db()
    assert root.check_password(PASSWORD)
    assert root_client.get("/api/v1/auth/session/").json()["authenticated"]
    assert not AdministrationEvent.objects.filter(kind="root_password_changed").exists()


@pytest.mark.django_db
def test_current_password_verification_never_rehashes_before_provider_success(
    root, root_client, provider
):
    root.password = make_password(PASSWORD, hasher="pbkdf2_sha256")
    root.save(update_fields=["password"])
    # Crear una sesión ligada al hash heredado, que el login podría actualizar por sí mismo.
    from django.contrib.auth import HASH_SESSION_KEY

    session = root_client.session
    session[HASH_SESSION_KEY] = root.get_session_auth_hash()
    session.save()
    old_hash = root.password
    provider["error"] = TimeoutError()
    assert root_client.post(PASSWORD_URL, password_data(), format="json").status_code == 503
    root.refresh_from_db()
    assert root.password == old_hash
    assert root_client.get("/api/v1/auth/session/").json()["authenticated"]


@pytest.mark.django_db
def test_password_block_is_separate_from_login_does_not_extend_and_expires(
    root_client, root, clock
):
    for _ in range(4):
        assert (
            root_client.post(
                PASSWORD_URL, password_data(current="wrong-password"), format="json"
            ).status_code
            == 401
        )
    response = root_client.post(
        PASSWORD_URL, password_data(current="wrong-password"), format="json"
    )
    assert response.status_code == 429 and int(response["Retry-After"]) == 900
    key = private_key("HU009.root-password", str(root.pk))
    blocked = LoginGuard.objects.get(key=key).blocked_until
    clock.now += timedelta(seconds=30)
    response = root_client.post(PASSWORD_URL, password_data(), format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) == 870
    assert LoginGuard.objects.get(key=key).blocked_until == blocked
    assert login(root_client, root).status_code == 200
    csrf(root_client)
    clock.now = blocked
    assert root_client.post(PASSWORD_URL, password_data(), format="json").status_code == 200
    assert LoginGuard.objects.get(key=key).failures == []


@pytest.mark.django_db
def test_password_origin_quota_is_independent_and_counts_invalid_input(root_client, clock):
    for _ in range(30):
        assert root_client.post(PASSWORD_URL, {}, format="json").status_code == 400
    response = root_client.post(PASSWORD_URL, {}, format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) == 900
    clock.now += timedelta(seconds=900)
    assert root_client.post(PASSWORD_URL, {}, format="json").status_code == 400


@pytest.mark.django_db
def test_password_change_rolls_back_on_audit_failure(root_client, root):
    with patch(
        "apps.users.administration_services.administration_event",
        side_effect=IntegrityError("private"),
    ):
        assert root_client.post(PASSWORD_URL, password_data(), format="json").status_code == 500
    root.refresh_from_db()
    assert root.check_password(PASSWORD)


@pytest.mark.django_db
def test_shared_role_permissions_enforce_rn02_and_rn03_even_for_technical_superusers(root):
    for role in ["ROOT", "ADMINISTRADOR", "CLIENTE"]:
        user = User(
            role=role, is_active=True, is_staff=True, is_superuser=True, is_email_verified=True
        )
        request = SimpleNamespace(user=user)
        assert IsAdministrator().has_permission(request, None) == (role == "ADMINISTRADOR")
        assert IsClient().has_permission(request, None) == (role == "CLIENTE")
        assert (
            IsClient().has_permission(request, None)
            and HasVerifiedEmail().has_permission(request, None)
        ) == (role == "CLIENTE")
        user.is_active = False
        assert not IsAdministrator().has_permission(
            request, None
        ) and not IsClient().has_permission(request, None)


@pytest.mark.django_db(transaction=True)
def test_concurrent_creation_with_same_email_has_one_account_wallet_and_notification(
    root, data, provider, monkeypatch
):
    barrier = Barrier(2)
    original = administration_services.check_new_password

    def checked(*args):
        assert not connection.in_atomic_block
        barrier.wait(timeout=15)
        return original(*args)

    monkeypatch.setattr(administration_services, "check_new_password", checked)

    def run():
        try:
            create_administrator(actor=root, data=data, origin="test")
            return 201
        except EmailAlreadyRegistered:
            return 409

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(independently, run) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [201, 409]
    assert User.objects.count() == Wallet.objects.count() == 2
    assert AdministratorNotification.objects.count() == 1
    assert AdministrationEvent.objects.filter(kind="administrator_created").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_root_password_changes_have_one_effect(root, provider, monkeypatch):
    barrier = Barrier(2)
    original = administration_services.check_new_password

    def checked(*args):
        assert not connection.in_atomic_block
        barrier.wait(timeout=15)
        return original(*args)

    monkeypatch.setattr(administration_services, "check_new_password", checked)

    def run():
        try:
            change_root_password(
                actor=root, current_password=PASSWORD, password=NEW_PASSWORD, origin="test"
            )
            return 200
        except CredentialsChanged:
            return 409

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(independently, run) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [200, 409]
    assert AdministrationEvent.objects.filter(kind="root_password_changed").count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("operation", ["create", "password"])
def test_permission_is_rechecked_after_provider_returns(
    root, data, provider, monkeypatch, operation
):
    original = administration_services.check_new_password

    def checked(*args):
        assert not connection.in_atomic_block
        original(*args)
        User.objects.filter(pk=root.pk).update(is_active=False)

    monkeypatch.setattr(administration_services, "check_new_password", checked)
    with pytest.raises(PermissionDenied):
        if operation == "create":
            create_administrator(actor=root, data=data, origin="test")
        else:
            change_root_password(
                actor=root, current_password=PASSWORD, password=NEW_PASSWORD, origin="test"
            )
    assert not AdministratorNotification.objects.exists()
    assert AdministrationEvent.objects.filter(kind="access_denied").count() == 1
    root.refresh_from_db()
    assert root.check_password(PASSWORD)


@pytest.mark.django_db(transaction=True)
def test_mail_retry_recovery_and_privacy(root, data, provider, clock, caplog):
    user = create_administrator(actor=root, data=data, origin="192.0.2.1")
    job = AdministratorNotification.objects.get()

    def unavailable(*args, **kwargs):
        assert not connection.in_atomic_block
        raise RuntimeError("private-credentials-recipient")

    with patch("apps.users.administrator_mail.send_mail", side_effect=unavailable):
        assert process_administrator_notifications() == (0, 1)
    job.refresh_from_db()
    assert job.last_error == "mail_unavailable" and job.attempts == 1
    assert process_administrator_notifications() == (0, 0)
    clock.now = job.next_attempt_at
    call_command("process_administrator_notifications", batch_size=1)
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [user.email]
    serialized = str(list(AdministrationEvent.objects.values())) + mail.outbox[0].body + caplog.text
    for private in [
        data["password"],
        PASSWORD,
        user.email,
        "192.0.2.1",
        "private-credentials-recipient",
    ]:
        assert private not in serialized
    assert process_administrator_notifications() == (0, 0)


@pytest.mark.django_db(transaction=True)
def test_mail_processors_claim_one_notification_and_recover_abandoned_lease(
    root, data, provider, clock
):
    create_administrator(actor=root, data=data, origin="test")
    job = AdministratorNotification.objects.get()
    job.lease_until = clock.now + timedelta(minutes=5)
    job.save(update_fields=["lease_until"])
    assert process_administrator_notifications() == (0, 0)
    clock.now = job.lease_until
    entered, release = Event(), Event()

    def send(*args, **kwargs):
        assert not connection.in_atomic_block
        entered.set()
        assert release.wait(timeout=15)
        return 1

    with patch("apps.users.administrator_mail.send_mail", side_effect=send):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                independently, lambda: process_administrator_notifications(batch_size=1)
            )
            assert entered.wait(timeout=15)
            second = pool.submit(
                independently, lambda: process_administrator_notifications(batch_size=1)
            )
            assert second.result(timeout=15) == (0, 0)
            release.set()
            assert first.result(timeout=15) == (1, 0)
    job.refresh_from_db()
    assert job.sent_at is not None and job.attempts == 1


@pytest.mark.django_db
def test_mail_never_runs_inside_registration_transaction(root, data, provider):
    create_administrator(actor=root, data=data, origin="test")
    with transaction.atomic():
        with pytest.raises(RuntimeError, match="commit"):
            process_administrator_notifications()
