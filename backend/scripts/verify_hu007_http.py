"""Ensayo explícito: HTTP real + API oficial, cuenta sintética conservada y correo en memoria.

Ejecutar en Docker de desarrollo: python -m scripts.verify_hu007_http
No es parte de pytest. Consume cuotas normales y espera el intervalo real de reenvío.
"""

import http.cookiejar
import json
import os
import re
import secrets
import time
import traceback
import urllib.error
import urllib.request
from datetime import timedelta
from urllib.parse import parse_qs, unquote, urlsplit

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth.password_validation import validate_password  # noqa: E402
from django.core import mail  # noqa: E402
from django.db import connection  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.users.mail import process_verification_emails  # noqa: E402
from apps.users.models import (  # noqa: E402
    EmailVerification,
    RegistrationConsent,
    RegistrationEvent,
    User,
)
from apps.users.password_check import is_compromised  # noqa: E402
from apps.wallets.models import Wallet  # noqa: E402

ORIGIN = "http://127.0.0.1:8000"
AUTH = "/api/v1/auth/"


def run():
    assert not settings.REGISTRATION_PRODUCTION
    assert settings.EMAIL_BACKEND.endswith(("console.EmailBackend", "locmem.EmailBackend"))
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version")
        assert cursor.fetchone()[0].split()[0] == "17.11"
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    csrf = None

    def request(path, data=None):
        headers = {"Content-Type": "application/json", "Origin": ORIGIN}
        if csrf:
            headers["X-CSRFToken"] = csrf
        incoming = urllib.request.Request(
            ORIGIN + path,
            data=None if data is None else json.dumps(data).encode(),
            headers=headers,
        )
        try:
            response = client.open(incoming, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response), response.headers

    assert request(AUTH + "register/", {})[0] == 403
    status, body, _ = request(AUTH + "csrf/")
    assert status == 200
    csrf = body["csrf_token"]
    status, policy, _ = request(AUTH + "registration-policy/")
    assert status == 200 and policy["is_test_document"]
    print("HTTP: CSRF 200, POST sin CSRF 403 y política de prueba 200", flush=True)
    identifier = secrets.token_hex(8)
    data = {
        "email": f"hu007-{identifier}@example.invalid",
        "username": "ensayo" + identifier,
        "first_name": "Ensayo",
        "last_name": "Sintético",
        "document_number": "000TEST007",
        "birth_date": "1995-06-15",
        "birth_place": "Lugar ficticio",
        "billing_address": "Dirección ficticia",
        "gender": "prueba",
        "password": "HU007-" + secrets.token_urlsafe(30),
        "accepts_data_policy": True,
        "policy_reference": policy["reference"],
        "policy_version": policy["version"],
    }
    models = [User, Wallet, RegistrationConsent, EmailVerification, RegistrationEvent]
    baseline = [model.objects.count() for model in models]
    compromised = None
    for synthetic in ["CorrectHorseBatteryStaple!", "ThisIsAPassword123!", "qwertyuiop1234567890!"]:
        try:
            validate_password(synthetic, user=User(username=data["username"], email=data["email"]))
        except django.core.exceptions.ValidationError:
            continue
        if is_compromised(synthetic):
            compromised = synthetic
            break
    assert compromised is not None
    status, error, _ = request(AUTH + "register/", {**data, "password": compromised})
    assert status == 400 and "password" in error["details"]
    assert [model.objects.count() for model in models] == baseline
    assert request(AUTH + "register/", {**data, "is_staff": True})[0] == 400
    assert request(AUTH + "register/", {**data, "policy_version": "obsolete-test"})[0] == 400
    print("HTTP: contraseña comprometida 400, privilegios 400 y política obsoleta 400", flush=True)
    status, body, _ = request(AUTH + "register/", data)
    assert status == 201 and body == {"status": "unverified", "delivery": "pending"}
    assert [model.objects.count() for model in models] == [count + 1 for count in baseline]
    user = User.objects.get(email=data["email"])
    assert user.role == User.Role.CLIENTE and not user.is_email_verified
    assert user.wallet.balance == 0 and user.password.startswith("argon2$")
    consent = user.registration_consent
    assert (consent.policy_reference, consent.policy_version, consent.policy_url) == (
        policy["reference"],
        policy["version"],
        policy["url"],
    )
    assert consent.accepted_at is not None
    first = EmailVerification.objects.get(user=user)
    assert first.sent_at is None and first.attempts == 0 and not connection.in_atomic_block
    assert request(AUTH + "register/", data)[0] == 409
    status, error, headers = request(AUTH + "resend-verification/", {"email": user.email})
    assert status == 429 and error["code"] == "throttled" and int(headers["Retry-After"]) > 0
    print(
        "HTTP: registro 201, cuenta/billetera únicas, consentimiento y outbox; "
        "duplicado 409, reenvío inmediato 429",
        flush=True,
    )

    def deliver_and_token():
        # Nunca reclamar trabajos de otras cuentas al hacer este ensayo manual.
        pending = EmailVerification.objects.filter(
            sent_at__isnull=True,
            consumed_at__isnull=True,
            superseded_at__isnull=True,
            expires_at__gt=timezone.now(),
            next_attempt_at__lte=timezone.now(),
            user__is_email_verified=False,
            user__is_active=True,
            user__role=User.Role.CLIENTE,
        )
        assert not pending.exclude(user=user).exists()
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            EMAIL_VERIFICATION_FRONTEND_URL="https://example.invalid/verificar",
        ):
            assert process_verification_emails(batch_size=1) == (1, 0)
        message = mail.outbox[-1]
        assert message.to == [user.email]
        link = re.search(r"https://example\.invalid/verificar#token=\S+", message.body).group()
        return unquote(parse_qs(urlsplit(link).fragment)["token"][0])

    old_token = deliver_and_token()
    first.refresh_from_db()
    assert first.sent_at is not None and first.attempts == 1
    assert request(AUTH + "verify-email/", {"token": "invalid-synthetic-token"})[0] == 400
    assert (
        request(AUTH + "resend-verification/", {"email": f"unknown-{identifier}@example.invalid"})[
            0
        ]
        == 202
    )
    remaining = max(0, 61 - (timezone.now() - first.created_at).total_seconds())
    print(
        f"Correo en memoria después del commit; espera real de reenvío: {remaining:.0f} s",
        flush=True,
    )
    # Pausas breves facilitan observar el proceso; no se alteran reloj, cuotas ni BD.
    while remaining > 0:
        pause = min(remaining, 5)
        time.sleep(pause)
        remaining = max(
            0, (first.created_at + timedelta(seconds=61) - timezone.now()).total_seconds()
        )
    assert request(AUTH + "resend-verification/", {"email": user.email})[0] == 202
    first.refresh_from_db()
    assert first.superseded_at is not None
    assert request(AUTH + "verify-email/", {"token": old_token})[0] == 400
    new_token = deliver_and_token()
    assert request(AUTH + "verify-email/", {"token": new_token})[:2] == (
        200,
        {"status": "verified"},
    )
    status, error, _ = request(AUTH + "verify-email/", {"token": new_token})
    assert status == 409 and error["code"] == "verification_used"
    user.refresh_from_db()
    assert user.is_email_verified and Wallet.objects.filter(user=user).count() == 1
    assert EmailVerification.objects.filter(user=user).count() == 2
    assert RegistrationEvent.objects.filter(user=user, kind="verified").count() == 1
    for private in [data["password"], old_token, new_token, user.email]:
        assert private not in str(list(RegistrationEvent.objects.filter(user=user).values()))
    assert request("/api/health/")[0] == 200
    print(
        "HTTP: reenvío 202, enlace sustituido 400, confirmación POST 200, "
        "reutilización 409, salud 200",
        flush=True,
    )
    print(
        "Ensayo completo; cuenta sintética conservada; dos correos solo en memoria; "
        "sin tokens ni credenciales en salida",
        flush=True,
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        # No mostrar traceback, cuerpo, enlace ni credenciales, tampoco ante fallos.
        print(
            f"Ensayo detenido: {type(exc).__name__}, "
            f"línea {traceback.extract_tb(exc.__traceback__)[-1].lineno}. "
            "Revisar la etapa anterior sin publicar datos."
        )
        raise SystemExit(1) from None
