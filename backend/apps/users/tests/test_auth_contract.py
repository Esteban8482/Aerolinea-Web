import pytest

from apps.users.auth_serializers import LoginSerializer, ResetPasswordSerializer


@pytest.mark.parametrize(
    "data",
    [
        {"password": "synthetic-password"},
        {"email": "a@example.invalid", "root_id": "root", "password": "synthetic-password"},
        {"username": "profile-name", "password": "synthetic-password"},
        {"root_id": "root", "password": "synthetic-password", "is_staff": True},
        {"email": "invalid", "password": "synthetic-password"},
        {"root_id": "", "password": "synthetic-password"},
        {"root_id": "root", "password": ""},
        [],
    ],
)
def test_login_rejects_ambiguous_or_unsupported_credentials(data):
    serializer = LoginSerializer(data=data)
    assert not serializer.is_valid()


def test_login_normalizes_email_without_altering_password():
    serializer = LoginSerializer(
        data={"email": " Account@Example.invalid ", "password": "  contraseña-sintética  "}
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data == {
        "email": "account@example.invalid",
        "password": "  contraseña-sintética  ",
    }
    assert "password" not in serializer.data


def test_root_identifier_is_case_sensitive_and_is_not_a_profile_name():
    serializer = LoginSerializer(data={"root_id": " Root-ID ", "password": "synthetic-password"})
    assert serializer.is_valid()
    assert serializer.validated_data["root_id"] == "Root-ID"


def test_reset_requires_matching_explicit_password_confirmation():
    serializer = ResetPasswordSerializer(
        data={
            "token": "synthetic-token",
            "password": "synthetic-password",
            "password_confirmation": "other",
        }
    )
    assert not serializer.is_valid()
    assert "password_confirmation" in serializer.errors
