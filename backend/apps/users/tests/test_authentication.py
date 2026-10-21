from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.sessions.models import Session
from django.db import close_old_connections, connections
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.auth_services import private_key
from apps.users.limits import bucket_key
from apps.users.models import (
    AccountSession,
    AuthenticationEvent,
    LoginGuard,
    RegistrationRateBucket,
    User,
)

PASSWORD = "acceso-largo-sintetico-para-pruebas-2026"
AUTH = "/api/v1/auth/"


@pytest.fixture
def clock(monkeypatch):
    value = SimpleNamespace(now=timezone.now())
    monkeypatch.setattr(timezone, "now", lambda: value.now)
    return value


@pytest.fixture
def account():
    return User.objects.create_user(
        email="login@example.invalid", password=PASSWORD, role="ADMINISTRADOR"
    )


def csrf(client):
    token = client.get(AUTH + "csrf/").json()["csrf_token"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return token


@pytest.fixture
def client():
    value = APIClient(enforce_csrf_checks=True)
    csrf(value)
    return value


def login(client, user, password=PASSWORD):
    credentials = (
        {"root_id": user.root_id} if user.role == User.Role.ROOT else {"email": user.email}
    )
    return client.post(AUTH + "login/", {**credentials, "password": password}, format="json")


def independently(function):
    close_old_connections()
    try:
        return function()
    finally:
        connections.close_all()


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["ROOT", "ADMINISTRADOR", "CLIENTE"])
def test_roles_can_login_with_business_credentials_without_technical_privileges(client, role):
    if role == "ROOT":
        user = User.objects.create_root(root_id="root-test", password=PASSWORD)
    else:
        # El manager valida perfil; un objeto de persistencia permite aislar aquí el login.
        user = User(email="person@example.invalid", role=role, is_email_verified=False)
        user.set_password(PASSWORD)
        user.save()
    assert not user.is_staff and not user.is_superuser
    response = login(client, user)
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "role": role, "is_email_verified": False}
    assert client.get(AUTH + "session/").json() == response.json()
    assert AuthenticationEvent.objects.get(kind="login").user == user
    assert AccountSession.objects.get().user == user


@pytest.mark.django_db
def test_email_normalization_and_root_email_cannot_be_used_as_login(client, account):
    assert (
        client.post(
            AUTH + "login/",
            {"email": " LOGIN@EXAMPLE.INVALID ", "password": PASSWORD},
            format="json",
        ).status_code
        == 200
    )
    csrf(client)
    root = User.objects.create_root(
        root_id="root-test", email="root@example.invalid", password=PASSWORD
    )
    assert (
        client.post(
            AUTH + "login/", {"email": root.email, "password": PASSWORD}, format="json"
        ).status_code
        == 401
    )


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["wrong_password", "inactive", "missing"])
def test_failed_credentials_have_same_status_body_and_do_not_create_session(client, account, kind):
    email = account.email
    password = PASSWORD
    if kind == "inactive":
        account.is_active = False
        account.save(update_fields=["is_active"])
    elif kind == "missing":
        email = "missing@example.invalid"
    else:
        password = "incorrect-synthetic-password"
    response = client.post(AUTH + "login/", {"email": email, "password": password}, format="json")
    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_credentials",
        "message": "No se pudo iniciar sesión con las credenciales enviadas.",
        "details": {},
    }
    assert not AccountSession.objects.exists()
    assert client.get(AUTH + "session/").json()["authenticated"] is False
    assert len(LoginGuard.objects.get().failures) == 1


@pytest.mark.django_db
def test_missing_account_still_performs_password_hash_work(client):
    original = User.set_password
    calls = []

    def tracked(self, value):
        calls.append(True)
        return original(self, value)

    with patch.object(User, "set_password", tracked):
        response = client.post(
            AUTH + "login/",
            {"email": "missing@example.invalid", "password": PASSWORD},
            format="json",
        )
    assert response.status_code == 401 and calls == [True]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route", ["login/", "logout/", "session/activity/", "password-recovery/", "password-reset/"]
)
def test_all_public_mutations_require_real_csrf_and_reject_foreign_origin(route):
    client = APIClient(enforce_csrf_checks=True)
    assert client.post(AUTH + route, {}, format="json").status_code == 403
    token = csrf(client)
    response = client.post(
        AUTH + route,
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://foreign.example.invalid",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    assert not LoginGuard.objects.exists() and not RegistrationRateBucket.objects.exists()


@pytest.mark.django_db
def test_login_rotates_anonymous_and_existing_authenticated_sessions_and_csrf(client, account):
    session = client.session
    session["synthetic"] = "retained"
    session.save()
    before = client.cookies["sessionid"].value
    old_csrf = client.cookies["csrftoken"].value
    assert login(client, account).status_code == 200
    after = client.cookies["sessionid"].value
    assert before != after and not Session.objects.filter(pk=before).exists()
    assert client.cookies["csrftoken"].value != old_csrf
    assert client.post(AUTH + "logout/", {}, format="json").status_code == 403
    csrf(client)
    assert login(client, account).status_code == 200
    assert client.cookies["sessionid"].value != after
    assert not Session.objects.filter(pk=after).exists()
    assert AccountSession.objects.count() == 1


@pytest.mark.django_db
def test_logout_revokes_server_session_and_replayed_cookie(client, account):
    assert login(client, account).status_code == 200
    key = client.cookies["sessionid"].value
    csrf(client)
    assert client.post(AUTH + "logout/", {}, format="json").json() == {"status": "logged_out"}
    assert not Session.objects.filter(pk=key).exists() and not AccountSession.objects.exists()
    replay = APIClient()
    replay.cookies["sessionid"] = key
    assert replay.get(AUTH + "session/").json()["authenticated"] is False
    csrf(client)
    assert client.post(AUTH + "logout/", {}, format="json").status_code == 200
    assert AuthenticationEvent.objects.filter(kind="logout").count() == 1


@pytest.mark.django_db
def test_polling_and_other_requests_never_extend_idle_deadline(client, account, clock):
    assert login(client, account).status_code == 200
    started = clock.now
    key = client.cookies["sessionid"].value
    initial_expiry = Session.objects.get(pk=key).expire_date
    for offset in [60, 900, 1799]:
        clock.now = started + timedelta(seconds=offset)
        assert client.get(AUTH + "session/").json()["authenticated"]
        assert client.get("/api/health/").status_code == 200
        csrf(client)
        assert AccountSession.objects.get().last_activity_at == started
        assert Session.objects.get(pk=key).expire_date == initial_expiry
    clock.now = started + timedelta(seconds=1800)
    assert client.get(AUTH + "session/").json()["authenticated"] is False
    assert not Session.objects.filter(pk=key).exists() and not AccountSession.objects.exists()
    assert AuthenticationEvent.objects.filter(kind="session_expired").count() == 1
    assert client.post(AUTH + "session/activity/", {}, format="json").status_code == 403


@pytest.mark.django_db
def test_only_explicit_activity_renews_the_deadline_once_per_minute(client, account, clock):
    assert login(client, account).status_code == 200
    started = clock.now
    csrf(client)
    response = client.post(AUTH + "session/activity/", {}, format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) == 60
    clock.now = started + timedelta(seconds=60)
    assert client.post(AUTH + "session/activity/", {}, format="json").status_code == 200
    assert AccountSession.objects.get().last_activity_at == clock.now
    assert Session.objects.get().expire_date == clock.now + timedelta(seconds=1800)
    clock.now = started + timedelta(seconds=1800)
    assert client.get(AUTH + "session/").json()["authenticated"]
    clock.now = started + timedelta(seconds=1860)
    assert client.get(AUTH + "session/").json()["authenticated"] is False


@pytest.mark.django_db
def test_deactivation_revokes_existing_session(client, account):
    assert login(client, account).status_code == 200
    key = client.cookies["sessionid"].value
    account.is_active = False
    account.save(update_fields=["is_active"])
    assert client.get(AUTH + "session/").json()["authenticated"] is False
    assert not Session.objects.filter(pk=key).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("exists", [True, False])
def test_account_lockout_is_shared_by_origins_and_does_not_extend(client, account, clock, exists):
    email = account.email if exists else "missing@example.invalid"
    data = {"email": email, "password": "wrong-synthetic-password"}
    for i in range(4):
        assert (
            client.post(
                AUTH + "login/", data, format="json", REMOTE_ADDR=f"192.0.2.{i + 1}"
            ).status_code
            == 401
        )
    response = client.post(AUTH + "login/", data, format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) == 900
    deadline = LoginGuard.objects.get().blocked_until
    clock.now += timedelta(seconds=30)
    data["password"] = PASSWORD
    response = client.post(AUTH + "login/", data, format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) == 870
    assert LoginGuard.objects.get().blocked_until == deadline
    assert len(LoginGuard.objects.get().failures) == 5
    clock.now = deadline
    assert client.post(AUTH + "login/", data, format="json").status_code == (200 if exists else 401)
    assert LoginGuard.objects.get().failures == ([] if exists else [clock.now.timestamp()])


@pytest.mark.django_db
def test_success_and_observation_window_reset_consecutive_failures(client, account, clock):
    for _ in range(4):
        assert login(client, account, "wrong-password").status_code == 401
    clock.now += timedelta(seconds=900)
    assert login(client, account, "wrong-password").status_code == 401
    assert len(LoginGuard.objects.get().failures) == 1
    assert login(client, account).status_code == 200
    assert LoginGuard.objects.get().failures == []


@pytest.mark.django_db
def test_origin_limit_counts_invalid_requests_and_expires_after_15_minutes(client, clock):
    for _ in range(30):
        assert client.post(AUTH + "login/", {}, format="json").status_code == 400
    response = client.post(AUTH + "login/", {}, format="json")
    assert response.status_code == 429 and int(response["Retry-After"]) == 900
    clock.now += timedelta(seconds=900)
    assert client.post(AUTH + "login/", {}, format="json").status_code == 400
    assert len(RegistrationRateBucket.objects.get().timestamps) == 1


@pytest.mark.django_db
def test_auth_events_and_counters_have_no_credentials_identifiers_or_session_material(
    client, account, caplog
):
    assert login(client, account, "wrong-password").status_code == 401
    assert login(client, account).status_code == 200
    serialized = (
        str(list(AuthenticationEvent.objects.values()))
        + str(list(LoginGuard.objects.values()))
        + str(list(RegistrationRateBucket.objects.values()))
        + caplog.text
    )
    for sensitive in [
        PASSWORD,
        "wrong-password",
        account.email,
        "127.0.0.1",
        client.cookies["sessionid"].value,
    ]:
        assert sensitive not in serialized
    assert LoginGuard.objects.get().key == private_key("login.email", account.email)
    assert RegistrationRateBucket.objects.get().key == bucket_key("HU008.login_origin", "127.0.0.1")


@pytest.mark.django_db(transaction=True)
def test_concurrent_failed_logins_serialize_the_lockout(account):
    key = private_key("login.email", account.email)
    now = timezone.now()
    LoginGuard.objects.create(key=key, failures=[now.timestamp()] * 4)
    barrier = Barrier(2)

    def attempt():
        client = APIClient(enforce_csrf_checks=True)
        csrf(client)
        barrier.wait(timeout=15)
        return login(client, account, "wrong-password").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(independently, attempt) for _ in range(2)]
        assert [f.result(timeout=30) for f in futures] == [429, 429]
    assert len(LoginGuard.objects.get().failures) == 5
    assert AuthenticationEvent.objects.filter(kind="login_blocked").count() == 1


@pytest.mark.django_db(transaction=True)
def test_logout_during_activity_response_never_recreates_server_session(account, client, clock):
    from threading import Event

    from apps.users.session_middleware import ApiSessionMiddleware

    assert login(client, account).status_code == 200
    csrf_token = csrf(client)
    key = client.cookies["sessionid"].value
    activity_client = APIClient(enforce_csrf_checks=True)
    activity_client.cookies = client.cookies.copy()
    activity_client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
    clock.now += timedelta(seconds=60)
    ready, finish = Event(), Event()
    original = ApiSessionMiddleware.process_response

    def delayed(self, request, response):
        if request.path == AUTH + "session/activity/":
            ready.set()
            assert finish.wait(timeout=15)
        return original(self, request, response)

    with patch.object(ApiSessionMiddleware, "process_response", delayed):
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                independently,
                lambda: activity_client.post(AUTH + "session/activity/", {}, format="json"),
            )
            assert ready.wait(timeout=15)
            assert client.post(AUTH + "logout/", {}, format="json").status_code == 200
            finish.set()
            response = pending.result(timeout=15)
    assert response.status_code == 409 and response.json()["code"] == "session_invalidated"
    assert not Session.objects.filter(pk=key).exists() and not AccountSession.objects.exists()
