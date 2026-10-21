import io
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils import timezone
from PIL import Image, PngImagePlugin
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.test import APIClient, APIRequestFactory

from apps.users.errors import InvalidVerification
from apps.users.limits import consume_limit, request_origin
from apps.users.mail import process_verification_emails
from apps.users.models import EmailVerification, RegistrationEvent, RegistrationRateBucket, User
from apps.users.services import confirm_email, register_customer, verification_token
from apps.users.tests.test_registration import csrf_client as csrf_client
from apps.users.tests.test_registration import data as data
from apps.users.tests.test_registration import registration_settings as registration_settings
from apps.users.tests.test_registration import run_independently
from apps.wallets.models import Wallet


def image_upload(format="PNG", size=(10, 12), metadata=False):
    stream = io.BytesIO()
    image = Image.new("RGB", size, color="blue")
    options = {}
    if metadata and format == "PNG":
        info = PngImagePlugin.PngInfo()
        info.add_text("private", "original-personal-metadata")
        options["pnginfo"] = info
    image.save(stream, format=format, **options)
    return SimpleUploadedFile("untrusted-name.bin", stream.getvalue(), "application/octet-stream")


@pytest.mark.django_db
def test_server_publishes_current_test_policy_and_records_its_version(
    data, csrf_client, monkeypatch
):
    response = csrf_client.get("/api/v1/auth/registration-policy/")
    assert response.status_code == 200
    assert response.json() == {
        "reference": "synthetic-policy-test-v1",
        "version": "test-v1",
        "url": "https://example.invalid/synthetic-policy",
        "is_test_document": True,
    }
    assert csrf_client.get("/api/v1/auth/registration-policy/test-document/").status_code == 200
    before = timezone.now()
    # El reloj de pared del host puede corregirse durante el hashing. La fecha
    # persistida debe ser la del servidor; comprobarla con un reloj controlado.
    monkeypatch.setattr(timezone, "now", lambda: before)
    register_customer(data=data)
    consent = User.objects.get().registration_consent
    assert consent.policy_reference == response.json()["reference"]
    assert consent.policy_version == response.json()["version"]
    assert consent.accepted_at == before


@pytest.mark.django_db
@pytest.mark.parametrize("value", ["arbitrary-version", "test-v0", ""])
def test_client_cannot_choose_a_different_policy_version(data, value):
    data["policy_version"] = value
    with pytest.raises(ValidationError) as exc:
        register_customer(data=data)
    assert "policy_version" in exc.value.detail
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "missing",
    ["REGISTRATION_POLICY_REFERENCE", "REGISTRATION_POLICY_VERSION", "REGISTRATION_POLICY_URL"],
)
def test_missing_policy_configuration_blocks_registration(data, csrf_client, settings, missing):
    setattr(settings, missing, "")
    assert csrf_client.get("/api/v1/auth/registration-policy/").status_code == 503
    assert csrf_client.post("/api/v1/auth/register/", data, format="json").status_code == 503
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("approved,is_test", [(False, True), (False, False), (True, True)])
def test_production_requires_approved_non_test_policy(
    data, csrf_client, settings, approved, is_test
):
    settings.REGISTRATION_PRODUCTION = True
    settings.REGISTRATION_POLICY_APPROVED = approved
    settings.REGISTRATION_POLICY_IS_TEST = is_test
    assert csrf_client.post("/api/v1/auth/register/", data, format="json").status_code == 503
    assert csrf_client.get("/api/v1/auth/registration-policy/test-document/").status_code == 404
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_optional_image_is_validated_recoded_and_kept_private(data, csrf_client, settings, format):
    data["image"] = image_upload(format=format, metadata=True)
    response = csrf_client.post("/api/v1/auth/register/", data, format="multipart")
    assert response.status_code == 201
    user = User.objects.get()
    assert user.profile_image.name.startswith("profiles/") and user.profile_image.name.endswith(
        ".png"
    )
    assert "untrusted-name" not in user.profile_image.name
    with user.profile_image.open("rb") as content, Image.open(content) as saved:
        assert saved.format == "PNG" and saved.size == (10, 12)
        assert "private" not in saved.info
    with pytest.raises(ValueError, match="privadas"):
        _ = user.profile_image.url
    assert user.profile_image.name not in response.content.decode()
    assert csrf_client.get("/media/" + user.profile_image.name).status_code == 404
    assert user.registration_consent.policy_version == "test-v1"


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["bad", "svg", "gif", "truncated", "oversized", "dimensions"])
def test_invalid_images_never_create_accounts(data, kind):
    if kind == "dimensions":
        upload = image_upload(size=(4097, 1))
    elif kind == "gif":
        upload = image_upload(format="GIF")
    elif kind == "truncated":
        valid = image_upload()
        upload = SimpleUploadedFile("bad.png", valid.read()[:30], "image/png")
    elif kind == "oversized":
        upload = SimpleUploadedFile("big.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")
    else:
        upload = SimpleUploadedFile(
            "image.png", b"<svg/>" if kind == "svg" else b"bad", "image/png"
        )
    data["image"] = upload
    with pytest.raises(ValidationError) as exc:
        register_customer(data=data)
    assert "image" in exc.value.detail and not User.objects.exists()


@pytest.mark.django_db
def test_image_is_removed_if_registration_persistence_rolls_back(data, settings):
    from pathlib import Path

    data["image"] = image_upload()
    with patch("apps.users.services.Wallet.objects.create", side_effect=IntegrityError):
        with pytest.raises(IntegrityError):
            register_customer(data=data)
    assert not User.objects.exists() and not Wallet.objects.exists()
    assert not list(Path(settings.PRIVATE_MEDIA_ROOT).rglob("*.png"))


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["palette_alpha", "exif_orientation"])
def test_image_recoding_preserves_transparency_and_applies_orientation(data, kind):
    output = io.BytesIO()
    if kind == "palette_alpha":
        image = Image.new("P", (2, 3))
        image.putpalette([255, 0, 0] * 256)
        image.save(output, format="PNG", transparency=0)
    else:
        image = Image.new("RGB", (2, 3), "red")
        exif = Image.Exif()
        exif[274] = 6
        image.save(output, format="JPEG", exif=exif)
    data["image"] = SimpleUploadedFile("image.bin", output.getvalue())
    user = register_customer(data=data)
    with user.profile_image.open("rb") as content, Image.open(content) as saved:
        if kind == "palette_alpha":
            assert saved.mode == "RGBA" and saved.getpixel((0, 0))[3] == 0
        else:
            assert saved.size == (3, 2) and not saved.getexif()


@pytest.mark.django_db
def test_valid_http_requests_are_limited_per_origin_with_retry_after(data, csrf_client):
    for _ in range(10):
        response = csrf_client.post("/api/v1/auth/register/", {"invalid": True}, format="json")
        assert response.status_code == 400
    response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 429 and response.json()["code"] == "throttled"
    assert 1 <= int(response["Retry-After"]) <= 3600
    assert not User.objects.exists()
    assert RegistrationRateBucket.objects.count() == 1


@pytest.mark.django_db
def test_registration_origin_quota_is_shared_across_clients(data):
    clients = [APIClient(enforce_csrf_checks=True), APIClient(enforce_csrf_checks=True)]
    for client in clients:
        token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
        client.credentials(HTTP_X_CSRFTOKEN=token)
    for i in range(10):
        assert clients[i % 2].post("/api/v1/auth/register/", {}, format="json").status_code == 400
    assert clients[0].post("/api/v1/auth/register/", data, format="json").status_code == 429


@pytest.mark.django_db
def test_sliding_window_expires_at_3600_seconds_and_hashes_subjects(monkeypatch):
    now = timezone.now()
    monkeypatch.setattr("apps.users.limits.timezone.now", lambda: now)
    consume_limit(scope="test", subject="private@example.invalid", maximum=1)
    with pytest.raises(Throttled):
        consume_limit(scope="test", subject="private@example.invalid", maximum=1)
    assert "private" not in str(list(RegistrationRateBucket.objects.values()))
    monkeypatch.setattr("apps.users.limits.timezone.now", lambda: now + timedelta(seconds=3599))
    with pytest.raises(Throttled):
        consume_limit(scope="test", subject="private@example.invalid", maximum=1)
    monkeypatch.setattr("apps.users.limits.timezone.now", lambda: now + timedelta(seconds=3600))
    consume_limit(scope="test", subject="private@example.invalid", maximum=1)


def test_origin_header_is_used_only_for_explicitly_trusted_proxy(settings):
    factory = APIRequestFactory()
    request = factory.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_REAL_IP="192.0.2.10")
    settings.REGISTRATION_TRUSTED_PROXIES = []
    assert request_origin(request) == "127.0.0.1"
    settings.REGISTRATION_TRUSTED_PROXIES = ["127.0.0.1"]
    assert request_origin(request) == "192.0.2.10"
    request.META["HTTP_X_REAL_IP"] = "invalid"
    assert request_origin(request) == "unknown"


@pytest.mark.django_db
def test_resend_waits_60_seconds_then_replaces_token_without_duplicate_account(
    data,
    csrf_client,
    monkeypatch,
):
    user = register_customer(data=data)
    original = EmailVerification.objects.get(user=user)
    original_token = verification_token(original)
    path = "/api/v1/auth/resend-verification/"
    assert csrf_client.post(path, {"email": user.email}, format="json").status_code == 429
    monkeypatch.setattr(
        "apps.users.limits.timezone.now", lambda: original.created_at + timedelta(seconds=60)
    )
    response = csrf_client.post(path, {"email": user.email.upper()}, format="json")
    assert response.status_code == 202 and response.json() == {"status": "requested"}
    original.refresh_from_db()
    assert original.superseded_at
    assert User.objects.count() == Wallet.objects.count() == 1
    assert EmailVerification.objects.count() == 2
    with pytest.raises(InvalidVerification):
        confirm_email(token=original_token)
    new = EmailVerification.objects.latest("pk")
    assert new.expires_at - new.created_at == timedelta(hours=24)
    confirm_email(token=verification_token(new))
    user.refresh_from_db()
    assert user.is_email_verified


@pytest.mark.django_db
def test_resend_account_limit_is_five_and_independent_of_origin(data, csrf_client, monkeypatch):
    user = register_customer(data=data)
    start = EmailVerification.objects.get().created_at
    path = "/api/v1/auth/resend-verification/"
    for i in range(1, 6):
        monkeypatch.setattr(
            "apps.users.limits.timezone.now", lambda i=i: start + timedelta(seconds=60 * i)
        )
        assert csrf_client.post(path, {"email": user.email}, format="json").status_code == 202
    monkeypatch.setattr("apps.users.limits.timezone.now", lambda: start + timedelta(seconds=360))
    response = csrf_client.post(path, {"email": user.email}, format="json", REMOTE_ADDR="192.0.2.2")
    assert response.status_code == 429
    assert User.objects.count() == Wallet.objects.count() == 1
    assert EmailVerification.objects.count() == 6
    assert RegistrationEvent.objects.filter(kind="resent").count() == 5


@pytest.mark.django_db
def test_resend_origin_limit_applies_even_for_unknown_accounts(data, csrf_client):
    path = "/api/v1/auth/resend-verification/"
    for i in range(20):
        response = csrf_client.post(path, {"email": f"unknown{i}@example.invalid"}, format="json")
        assert response.status_code == 202 and response.json() == {"status": "requested"}
    assert (
        csrf_client.post(path, {"email": "last@example.invalid"}, format="json").status_code == 429
    )
    assert not User.objects.exists() and not EmailVerification.objects.exists()


@pytest.mark.django_db
def test_resend_verified_account_has_same_response_and_creates_no_delivery(data, csrf_client):
    user = register_customer(data=data)
    job = EmailVerification.objects.get()
    confirm_email(token=verification_token(job))
    # El intervalo inicial ya pasó; también se aplica a cuentas verificadas.
    with patch(
        "apps.users.limits.timezone.now", return_value=job.created_at + timedelta(seconds=60)
    ):
        response = csrf_client.post(
            "/api/v1/auth/resend-verification/", {"email": user.email}, format="json"
        )
    assert response.status_code == 202 and response.json() == {"status": "requested"}
    assert EmailVerification.objects.count() == 1


@pytest.mark.django_db
def test_failed_resend_rolls_back_replacement_but_preserves_rate_limit(data, csrf_client):
    user = register_customer(data=data)
    job = EmailVerification.objects.get()
    path = "/api/v1/auth/resend-verification/"
    with patch(
        "apps.users.limits.timezone.now", return_value=job.created_at + timedelta(seconds=60)
    ):
        with patch(
            "apps.users.services.RegistrationEvent.objects.create", side_effect=IntegrityError
        ):
            response = csrf_client.post(path, {"email": user.email}, format="json")
        assert response.status_code == 500 and response.json()["code"] == "internal_error"
        assert csrf_client.post(path, {"email": user.email}, format="json").status_code == 429
    job.refresh_from_db()
    assert job.superseded_at is None and EmailVerification.objects.count() == 1
    assert User.objects.count() == Wallet.objects.count() == 1
    confirm_email(token=verification_token(job))


@pytest.mark.django_db
def test_resend_public_post_requires_csrf_and_denies_foreign_origin(data):
    client = APIClient(enforce_csrf_checks=True)
    path = "/api/v1/auth/resend-verification/"
    assert client.post(path, {"email": data["email"]}, format="json").status_code == 403
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    response = client.post(
        path,
        {"email": data["email"]},
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://foreign.example.invalid",
    )
    assert response.status_code == 403
    assert not RegistrationRateBucket.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_quota_reservations_cannot_exceed_maximum():
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=15)
        try:
            consume_limit(scope="concurrent", subject="same-origin", maximum=1)
            return "accepted"
        except Throttled:
            return "limited"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_independently, run) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == ["accepted", "limited"]
    assert len(RegistrationRateBucket.objects.get().timestamps) == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_resends_create_only_one_new_notification(data):
    user = register_customer(data=data)
    start = EmailVerification.objects.get().created_at
    barrier = Barrier(2)

    def run():
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
        barrier.wait(timeout=15)
        return client.post(
            "/api/v1/auth/resend-verification/",
            {"email": user.email},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code

    with patch("apps.users.limits.timezone.now", return_value=start + timedelta(seconds=60)):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_independently, run) for _ in range(2)]
            assert sorted(f.result(timeout=30) for f in futures) == [202, 429]
    assert EmailVerification.objects.count() == 2
    assert User.objects.count() == Wallet.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_superseded_email_is_not_processed(data, csrf_client):
    register_customer(data=data)
    original = EmailVerification.objects.get()
    with patch(
        "apps.users.limits.timezone.now", return_value=original.created_at + timedelta(seconds=60)
    ):
        assert (
            csrf_client.post(
                "/api/v1/auth/resend-verification/", {"email": data["email"]}, format="json"
            ).status_code
            == 202
        )
        assert process_verification_emails() == (1, 0)
    original.refresh_from_db()
    assert original.sent_at is None and original.attempts == 0
