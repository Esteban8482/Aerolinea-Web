from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.wallets.models import Wallet

from .models import User


def provision_root(*, root_id, password, email=None):
    """Bootstrap técnico idempotente; no es el registro público de HU-007."""
    existing = User.objects.filter(role=User.Role.ROOT).first()
    if existing:
        return existing, False
    candidate = User(root_id=root_id, email=email, role=User.Role.ROOT)
    validate_password(password, user=candidate)
    try:
        with transaction.atomic():
            root = User.objects.create_root(root_id=root_id, password=password, email=email)
            Wallet.objects.create(user=root)
            return root, True
    except (IntegrityError, ValidationError):
        # La restricción de la cuenta inicial resuelve dos bootstrap simultáneos.
        existing = User.objects.filter(role=User.Role.ROOT).first()
        if existing:
            return existing, False
        raise
