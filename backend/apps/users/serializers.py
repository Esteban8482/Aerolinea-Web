from collections.abc import Mapping
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .images import sanitize_profile_image
from .models import User
from .password_check import validate_registration_password
from .policy import current_registration_policy

DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "yopmail.com", "trashmail.com", "temp-mail.org", "sharklasers.com",
    "guerrillamail.net", "dispostable.com",
}

class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        unexpected = set(data) - set(self.fields)
        if unexpected:
            raise serializers.ValidationError(
                {field: ["Este campo no está admitido."] for field in sorted(unexpected)}
            )
        return super().to_internal_value(data)


class RegistrationSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    username = serializers.CharField(max_length=40)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    document_number = serializers.CharField(max_length=20)
    document_type = serializers.CharField(max_length=20, required=False, allow_blank=True)
    birth_date = serializers.DateField()
    birth_place = serializers.CharField(max_length=100)
    billing_address = serializers.CharField(max_length=200)
    gender = serializers.CharField(max_length=20)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    accepts_data_policy = serializers.BooleanField()
    policy_reference = serializers.CharField(max_length=200)
    policy_version = serializers.CharField(max_length=100)
    image = serializers.FileField(required=False, write_only=True)

    MIN_AGE_YEARS = 18
    MAX_AGE_YEARS = 120

    def validate_birth_date(self, value):
        today = date.today()
        if value > today:
            raise serializers.ValidationError("La fecha de nacimiento no puede ser futura.")
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < self.MIN_AGE_YEARS:
            raise serializers.ValidationError("No supera la edad minima para registrarse.")
        if age > self.MAX_AGE_YEARS:
            raise serializers.ValidationError("La fecha de nacimiento no es plausible.")
        return value
    
    def validate_email(self, value):
        value = value.strip().lower()
        domain = value.rsplit("@", 1)[-1]
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise serializers.ValidationError(
                "No se admiten correos temporales o desechables."
            )
        return value

    def validate_accepts_data_policy(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar la política de tratamiento de datos.")
        return value

    def validate_policy_reference(self, value):
        if value != current_registration_policy()["reference"]:
            raise serializers.ValidationError(
                "Consulta y acepta la versión vigente de la política."
            )
        return value

    def validate_policy_version(self, value):
        if value != current_registration_policy()["version"]:
            raise serializers.ValidationError(
                "Consulta y acepta la versión vigente de la política."
            )
        return value

    def validate_image(self, value):
        return sanitize_profile_image(value)

    def validate(self, attrs):
        profile = {
            k: v
            for k, v in attrs.items()
            if k
            not in {
                "password",
                "phone",
                "accepts_data_policy",
                "policy_reference",
                "policy_version",
                "image",
            }
        }
        try:
            validate_password(attrs["password"], user=User(**profile))
            validate_registration_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from None
        return attrs


class VerificationSerializer(StrictSerializer):
    token = serializers.CharField(max_length=2048, write_only=True, trim_whitespace=False)


class RegistrationResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["unverified"])
    delivery = serializers.ChoiceField(choices=["pending"])


class VerificationResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["verified"])


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class PolicySerializer(serializers.Serializer):
    reference = serializers.CharField()
    version = serializers.CharField()
    url = serializers.URLField()
    is_test_document = serializers.BooleanField()


class ResendSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return value.strip().lower()


class ResendResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["requested"])


class RegistrationErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()


class ProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    document_number = serializers.CharField()
    document_type = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    birth_place = serializers.CharField()
    billing_address = serializers.CharField()
    gender = serializers.CharField()
    role = serializers.CharField()
    is_email_verified = serializers.BooleanField()
    wallet_balance = serializers.CharField()
