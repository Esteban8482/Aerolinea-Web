import io
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rest_framework.test import APIClient

from apps.users.models import AccountSession, User
from config.logging import SafeEventFormatter


@pytest.mark.django_db
def test_session_authentication_rejects_missing_csrf_and_foreign_origins(settings):
    settings.ROOT_URLCONF = "config.tests.urls"
    client = APIClient(enforce_csrf_checks=True)
    response = client.post("/_test/protected/", {}, format="json")
    assert response.status_code == 403
    assert response.json()["code"] == "not_authenticated"
    user = User.objects.create_user(email="security@example.com", role="ADMINISTRADOR")
    client.force_login(user)
    AccountSession.objects.create(session_id=client.session.session_key, user=user)
    response = client.post("/_test/protected/", {}, format="json")
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    client.get("/_test/csrf/")
    token = client.cookies["csrftoken"].value
    response = client.post("/_test/protected/", {}, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    response = client.post(
        "/_test/protected/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://foreign.example.invalid",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"


def test_logging_never_serializes_messages_arguments_or_tracebacks():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeEventFormatter())
    logger = logging.Logger("audit-test")
    logger.addHandler(handler)
    try:
        raise ValueError("private-exception-content")
    except ValueError:
        logger.exception("private-query=%s", "private-password")
    output = stream.getvalue()
    assert "ERROR audit-test event" in output
    assert "private" not in output
    assert "Traceback" not in output


@pytest.fixture
def production_env():
    return {
        "PATH": os.defpath,
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "synthetic-test-secret-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDE",
        "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/test_config",
        "DJANGO_ALLOWED_HOSTS": "api.example.invalid",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://api.example.invalid",
        "DJANGO_SECURE_HSTS_SECONDS": "3600",
        "EMAIL_HOST": "smtp.example.invalid",
        "EMAIL_PORT": "587",
        "EMAIL_HOST_USER": "test",
        "EMAIL_HOST_PASSWORD": "synthetic-test-password",
        "EMAIL_USE_TLS": "true",
        "EMAIL_USE_SSL": "false",
        "DEFAULT_FROM_EMAIL": "test@example.invalid",
    }


def configure_in_subprocess(env, script="import django; django.setup()"):
    return subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "missing",
    [
        "DJANGO_SECRET_KEY",
        "DATABASE_URL",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "EMAIL_HOST_PASSWORD",
    ],
)
def test_production_requires_explicit_secrets_and_parameters(production_env, missing):
    production_env.pop(missing)
    result = configure_in_subprocess(production_env)
    assert result.returncode != 0
    assert missing in result.stderr


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("DATABASE_URL", "sqlite:///tmp/db.sqlite3"),
        ("DJANGO_SECRET_KEY", "short"),
        ("DJANGO_ALLOWED_HOSTS", "*"),
        ("DJANGO_CSRF_TRUSTED_ORIGINS", "http://insecure.invalid"),
        ("EMAIL_USE_SSL", "true"),
    ],
)
def test_production_rejects_unsafe_configuration(production_env, variable, value):
    production_env[variable] = value
    assert configure_in_subprocess(production_env).returncode != 0


def test_production_passes_deployment_checks_without_exposing_admin_or_docs(production_env):
    result = configure_in_subprocess(
        production_env,
        """
import django
django.setup()
from django.core.management import call_command
from django.core.checks import run_checks
from django.test import Client
from django.conf import settings
issues = run_checks(include_deployment_checks=True)
# Preload y todos los subdominios requieren una decisión real de despliegue.
assert {issue.id for issue in issues} == {"security.W005", "security.W021"}
call_command("check", deploy=True, fail_level="ERROR")
client = Client(HTTP_HOST="api.example.invalid")
assert client.get("/api/docs/", secure=True).status_code == 404
assert client.get("/admin/", secure=True).status_code == 404
assert client.get("/api/v1/auth/registration-policy/", secure=True).status_code == 503
assert client.get("/api/v1/auth/registration-policy/test-document/", secure=True).status_code == 404
response = client.post("/api/v1/auth/register/", {}, content_type="application/json", secure=True)
assert response.status_code == 503
assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
assert settings.SECURE_PROXY_SSL_HEADER is None
""",
    )
    assert result.returncode == 0, result.stderr


def test_test_settings_never_fall_back_to_development_database(production_env):
    production_env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    result = configure_in_subprocess(production_env)
    assert result.returncode != 0
    assert "TEST_DATABASE_URL" in result.stderr
    production_env["TEST_DATABASE_URL"] = production_env["DATABASE_URL"].replace(
        "test_config", "aerolinea"
    )
    assert configure_in_subprocess(production_env).returncode != 0
