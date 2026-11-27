"""Breach-provider behavior was retired by the cumulative-delivery request."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.users.password_check import validate_account_password
from apps.users.tests.test_registration import csrf_client as csrf_client
from apps.users.tests.test_registration import data as data
from apps.users.tests.test_registration import registration_settings as registration_settings


@pytest.mark.parametrize("password", ["short", "1234567890123456", "password"])
def test_local_password_validation_preserved(password):
    with pytest.raises(ValidationError):
        validate_account_password(password)


@pytest.mark.django_db
def test_registration_does_not_depend_on_external_password_service(csrf_client, data):
    with patch("http.client.HTTPSConnection", side_effect=AssertionError("Unexpected network")):
        response = csrf_client.post("/api/v1/auth/register/", data, format="json")
    assert response.status_code == 201


def test_long_password_does_not_require_a_digit():
    validate_account_password("long-synthetic-local-passphrase")
