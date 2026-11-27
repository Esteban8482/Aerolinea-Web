"""Current local password policy; no breach database or external HTTP dependency."""

from django.contrib.auth.password_validation import validate_password


def validate_account_password(password, user=None):
    validate_password(password, user=user)
