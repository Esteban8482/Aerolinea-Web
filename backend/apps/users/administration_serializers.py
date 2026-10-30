from rest_framework import serializers

from .models import User
from .serializers import StrictSerializer


class AdministratorCreateSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    document_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        return value.strip().lower()


class AdministratorSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=User.Role.values, read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]
        read_only_fields = fields


class AdministratorCreatedSerializer(AdministratorSerializer):
    delivery = serializers.ChoiceField(choices=["pending"], read_only=True)

    class Meta(AdministratorSerializer.Meta):
        fields = AdministratorSerializer.Meta.fields + ["delivery"]


class RootPasswordSerializer(StrictSerializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": ["Las contraseñas no coinciden."]}
            )
        return attrs


class RootPasswordResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["password_changed"])


class AdministratorPasswordChangeSerializer(StrictSerializer):
    admin_id = serializers.IntegerField(required=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": ["Las contraseñas no coinciden."]}
            )
        return attrs
