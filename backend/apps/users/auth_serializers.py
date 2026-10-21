"""Contratos HTTP de HU-008; los identificadores de acceso son explícitos."""

from rest_framework import serializers

from .serializers import StrictSerializer


class LoginSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254, required=False)
    root_id = serializers.CharField(max_length=254, required=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if ("email" in attrs) == ("root_id" in attrs):
            raise serializers.ValidationError(
                "Envía correo y contraseña, o ID root y contraseña, sin combinarlos."
            )
        return attrs


class EmptySerializer(StrictSerializer):
    pass


class SessionStateSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    role = serializers.ChoiceField(choices=["ROOT", "ADMINISTRADOR", "CLIENTE"], allow_null=True)
    is_email_verified = serializers.BooleanField()


class LogoutResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["logged_out"])


class RecoveryRequestSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(StrictSerializer):
    token = serializers.CharField(max_length=2048, write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": ["Las contraseñas no coinciden."]}
            )
        return attrs


class ResetPasswordResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["password_reset"])
