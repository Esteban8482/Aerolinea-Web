import logging
from uuid import uuid4

from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.wallets.models import Wallet

from .errors import (
    EmailAlreadyRegistered,
    ExpiredVerification,
    InvalidVerification,
    UsedVerification,
)
from .limits import initial_verification_cooldown
from .models import EmailVerification, RegistrationConsent, RegistrationEvent, User
from .policy import current_registration_policy
from .serializers import RegistrationSerializer

VERIFICATION_SALT = "users.HU007.email-verification.v1"


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


def register_customer(*, data):
    """Registro con consentimiento de la versión vigente y persistencia coordinada."""
    policy = current_registration_policy()
    serializer = RegistrationSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    attrs = dict(serializer.validated_data)
    password = attrs.pop("password")
    attrs.pop("phone", "")
    attrs.pop("accepts_data_policy")
    attrs.pop("policy_reference")
    attrs.pop("policy_version")
    image = attrs.pop("image", None)
    user = User(**attrs, role=User.Role.CLIENTE, is_email_verified=False)
    user.set_password(password)
    user.full_clean(validate_unique=False, validate_constraints=False)
    now = timezone.now()
    stored_image = None
    try:
        with transaction.atomic():
            if image is not None:
                storage = User._meta.get_field("profile_image").storage
                stored_image = storage.save(f"profiles/{uuid4().hex}.png", image)
                user.profile_image = stored_image
            user.save(force_insert=True)
            Wallet.objects.create(user=user)
            RegistrationConsent.objects.create(
                user=user,
                policy_reference=policy["reference"],
                policy_version=policy["version"],
                policy_url=policy["url"],
                accepted_at=now,
            )
            verification = EmailVerification.objects.create(
                user=user,
                recipient=user.email,
                created_at=now,
                expires_at=now + timezone.timedelta(hours=24),
                next_attempt_at=now,
            )
            RegistrationEvent.objects.create(
                user=user,
                verification=verification,
                kind=RegistrationEvent.Kind.REGISTERED,
            )
            initial_verification_cooldown(user.email, now)
    except Exception as exc:
        if stored_image:
            try:
                storage.delete(stored_image)
            except OSError:
                logging.getLogger(__name__).error("profile_image_cleanup_failed")
        constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
        if isinstance(exc, IntegrityError) and constraint in {
            "users_user_email_243f6e77_uniq",
            "users_email_ci_unique",
        }:
            raise EmailAlreadyRegistered() from None
        raise
    return user


def verification_token(verification):
    # Firma del framework con propósito separado; no contiene datos personales.
    return signing.Signer(salt=VERIFICATION_SALT).sign_object(
        {"delivery": verification.pk, "account": verification.user_id}
    )


def confirm_email(*, token):
    try:
        payload = signing.Signer(salt=VERIFICATION_SALT).unsign_object(token)
        if (
            not isinstance(payload, dict)
            or set(payload) != {"delivery", "account"}
            or type(payload["delivery"]) is not int
            or type(payload["account"]) is not int
            or not 0 < payload["delivery"] < 2**63
            or not 0 < payload["account"] < 2**63
        ):
            raise InvalidVerification()
    except (signing.BadSignature, ValueError, TypeError, UnicodeError):
        raise InvalidVerification() from None
    with transaction.atomic():
        # Orden común: usuario -> verificación, también para futuros reenvíos.
        user = User.objects.select_for_update().filter(pk=payload["account"]).first()
        verification = (
            EmailVerification.objects.select_for_update()
            .filter(
                pk=payload["delivery"],
                user=user,
            )
            .first()
            if user
            else None
        )
        if (
            not verification
            or verification.superseded_at
            or not user.is_active
            or user.role != User.Role.CLIENTE
            or verification.recipient != user.email
        ):
            raise InvalidVerification()
        if verification.consumed_at or user.is_email_verified:
            raise UsedVerification()
        now = timezone.now()
        if now >= verification.expires_at:
            raise ExpiredVerification()
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        verification.consumed_at = now
        verification.save(update_fields=["consumed_at"])
        RegistrationEvent.objects.create(
            user=user,
            verification=verification,
            kind=RegistrationEvent.Kind.VERIFIED,
        )


def resend_verification(*, email):
    """Los límites se consumen antes desde la vista; no revela existencia de cuenta."""
    with transaction.atomic():
        user = (
            User.objects.select_for_update()
            .filter(
                email=email,
                role=User.Role.CLIENTE,
                is_active=True,
                is_email_verified=False,
            )
            .first()
        )
        if not user:
            return
        now = timezone.now()
        EmailVerification.objects.filter(
            user=user,
            consumed_at__isnull=True,
            superseded_at__isnull=True,
        ).update(superseded_at=now)
        verification = EmailVerification.objects.create(
            user=user,
            recipient=user.email,
            created_at=now,
            expires_at=now + timezone.timedelta(hours=24),
            next_attempt_at=now,
        )
        RegistrationEvent.objects.create(
            user=user,
            verification=verification,
            kind=RegistrationEvent.Kind.RESENT,
        )
