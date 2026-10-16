from unittest.mock import patch

import pytest
from django.db import OperationalError
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_checks_postgresql_and_declares_both_response_types():
    client = APIClient()
    health = client.get("/api/health/")
    schema = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "application": "ok", "database": "ok"}
    assert schema.status_code == 200
    operation = schema.json()["paths"]["/api/health/"]["get"]
    assert {"200", "503"} <= operation["responses"].keys()
    assert client.get("/api/docs/").status_code == 200


def test_database_failure_is_reported_without_sensitive_details():
    with patch(
        "config.views.connection.cursor", side_effect=OperationalError("secret-db-host-password")
    ):
        response = APIClient().get("/api/health/")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "application": "ok",
        "database": "unavailable",
    }
    assert "secret-db-host-password" not in response.content.decode()


def test_no_admin_or_business_flow_is_exposed():
    client = APIClient()
    for path in ("/admin/", "/api/v1/login/", "/api/v1/register/", "/api/v1/wallets/"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
