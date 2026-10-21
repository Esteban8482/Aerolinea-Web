import hashlib
import http.client
import ssl
from threading import Event
from time import monotonic

import pytest

from apps.users.errors import PasswordCheckUnavailable
from apps.users.models import EmailVerification, RegistrationConsent, RegistrationEvent, User
from apps.users.password_check import is_compromised, validate_registration_password
from apps.users.tests.conftest import range_body
from apps.users.tests.test_registration import csrf_client as csrf_client
from apps.users.tests.test_registration import data as data
from apps.users.tests.test_registration import registration_settings as registration_settings
from apps.users.tests.test_registration_agreements import image_upload
from apps.wallets.models import Wallet


def digest(password):
    return hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()


@pytest.mark.parametrize("count,expected", [(42, True), (0, False)])
def test_matching_suffix_requires_positive_frequency(provider, count, expected):
    password = "  contraseña-sintética-áé-2026  "
    value = digest(password)
    provider["body"] = range_body(suffix=value[5:], count=count)
    assert is_compromised(password) is expected
    factory = provider["factory"]
    assert factory.call_count == 1
    assert factory.call_args.args == ("api.pwnedpasswords.com",)
    assert factory.call_args.kwargs["timeout"] == 3
    context = factory.call_args.kwargs["context"]
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    request = provider["connections"][0].request
    assert request.call_count == 1
    assert request.call_args.args == ("GET", "/range/" + value[:5])
    headers = request.call_args.kwargs["headers"]
    assert headers["Add-Padding"] == "true"
    sent = str(request.call_args)
    for sensitive in [password, value, value[5:], "@"]:
        assert sensitive not in sent
    provider["connections"][0].close.assert_called_once()


def test_absent_password_and_more_than_1000_records_are_supported(provider):
    provider["body"] = b"\r\n".join(f"{i:035x}:1".encode() for i in range(1900)) + b"\r\n"
    assert not is_compromised("synthetic-unlisted-value")


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError,
        ConnectionError,
        ssl.SSLError,
        OSError,
        http.client.IncompleteRead,
        http.client.BadStatusLine,
    ],
)
def test_network_failures_are_closed_without_retries(provider, error):
    provider["error"] = error(b"private-provider-error")
    with pytest.raises(PasswordCheckUnavailable):
        is_compromised("synthetic-failure-password")
    assert provider["factory"].call_count == 1


@pytest.mark.parametrize("status", [204, 301, 302, 400, 429, 500, 503])
def test_unexpected_status_including_redirects_is_not_followed(provider, status):
    provider["status"] = status
    provider["headers"]["Location"] = "https://unexpected.example.invalid/"
    with pytest.raises(PasswordCheckUnavailable):
        is_compromised("synthetic-http-failure")
    assert provider["factory"].call_count == 1


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "short",
        "invalid",
        "duplicate",
        "non_ascii",
        "negative",
        "truncated",
        "oversized",
        "html",
        "gzip",
        "unframed",
        "bad_length",
        "cut_record",
        "lf_only",
    ],
)
def test_invalid_or_incomplete_response_never_means_safe(provider, kind):
    if kind == "empty":
        provider["body"] = b""
    elif kind == "short":
        provider["body"] = b"A" * 35 + b":0"
    elif kind == "invalid":
        provider["body"] += b"\r\ninvalid"
    elif kind == "duplicate":
        provider["body"] += b"\r\n" + provider["body"].split(b"\r\n")[0]
    elif kind == "non_ascii":
        provider["body"] += b"\r\n\xff:2"
    elif kind == "negative":
        provider["body"] += b"\r\n" + b"F" * 35 + b":-1"
    elif kind == "truncated":
        provider["headers"]["Content-Length"] = str(len(provider["body"]) + 10)
    elif kind == "oversized":
        provider["body"] = b"x" * (1024 * 1024 + 1)
    elif kind == "html":
        provider["headers"]["Content-Type"] = "text/html"
    elif kind == "gzip":
        provider["headers"]["Content-Encoding"] = "gzip"
    elif kind == "unframed":
        provider["headers"]["Content-Length"] = None
    elif kind == "bad_length":
        provider["headers"]["Content-Length"] = "bogus"
    elif kind == "cut_record":
        provider["body"] = provider["body"][:-2]
    else:
        provider["body"] = provider["body"].replace(b"\r\n", b"\n")
    with pytest.raises(PasswordCheckUnavailable):
        is_compromised("synthetic-malformed-password")


def test_fully_framed_chunked_response_is_supported(provider):
    provider["headers"]["Content-Length"] = None
    provider["chunked"] = True
    assert not is_compromised("synthetic-chunked-password")


def test_invalid_record_after_positive_match_still_fails_closed(provider):
    password = "synthetic-compromised-password-2026"
    provider["body"] = range_body(suffix=digest(password)[5:]) + b"\r\nbad"
    with pytest.raises(PasswordCheckUnavailable):
        validate_registration_password(password)


def test_total_budget_includes_blocked_dns(provider, monkeypatch, settings):
    settings.PWNED_PASSWORDS_TIMEOUT_SECONDS = 0.05
    release = Event()
    original = provider["factory"].side_effect

    def slow_connection(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.connect.side_effect = lambda: release.wait(1)
        return connection

    provider["factory"].side_effect = slow_connection
    started = monotonic()
    try:
        with pytest.raises(PasswordCheckUnavailable):
            is_compromised("synthetic-time-budget")
        assert monotonic() - started < 0.5
    finally:
        release.set()
    # El hilo detecta presupuesto agotado antes de enviar la petición tras DNS.
    assert not provider["connections"][0].request.called


@pytest.mark.django_db
def test_registration_rejects_compromised_password_without_leaking_it(data, csrf_client, provider):
    provider["body"] = range_body(suffix=digest(data["password"])[5:])
    response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 400 and "password" in response.json()["details"]
    assert data["password"] not in response.content.decode()
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("failure", ["timeout", "tls", "status", "invalid", "truncated"])
def test_provider_failure_leaves_no_business_records_or_image(
    data, csrf_client, provider, settings, caplog, failure
):
    if failure == "timeout":
        provider["error"] = TimeoutError("sensitive-provider-data")
    elif failure == "tls":
        provider["error"] = ssl.SSLError("sensitive-provider-data")
    elif failure == "status":
        provider["status"] = 503
    elif failure == "truncated":
        provider["headers"]["Content-Length"] = str(len(provider["body"]) + 1)
    else:
        provider["body"] += b"\r\nprivate-invalid-response"
    data["image"] = image_upload()
    response = csrf_client.post("/api/v1/auth/register/", data, format="multipart")
    assert response.status_code == 503
    assert response.json() == {
        "code": "password_check_unavailable",
        "message": "No se pudo comprobar la contraseña. Intenta de nuevo más tarde.",
        "details": {},
    }
    for model in [User, Wallet, RegistrationConsent, EmailVerification, RegistrationEvent]:
        assert not model.objects.exists()
    assert not list(settings.PRIVATE_MEDIA_ROOT.rglob("*.png"))
    for sensitive in [
        data["password"],
        digest(data["password"]),
        digest(data["password"])[:5],
        data["email"],
        "sensitive-provider-data",
        "private-invalid-response",
    ]:
        assert sensitive not in caplog.text + response.content.decode()
    assert csrf_client.get("/api/health/").status_code == 200
