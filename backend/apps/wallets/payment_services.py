"""Simulated funding: private instruments, owner checks and atomic, repeat-safe deposits."""

import hashlib
import json
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import MovimientoBilletera, PaymentMethod, Wallet
from .services import depositar

MAX_BALANCE = Decimal(
    "999999999999.99"
)  # Existing DecimalField storage capacity, not a banking limit.
MIN_DEPOSIT = Decimal("1000.00")  # Preserve the existing public API minimum.


def authorized_user(actor):
    if not (
        actor
        and actor.is_authenticated
        and actor.is_active
        and actor.is_email_verified
        and actor.role == "CLIENTE"
    ):
        raise PermissionDenied("Se requiere una cuenta activa con correo verificado.")


def validate_expiry(method):
    if method.tipo == PaymentMethod.Kind.CARD:
        today = timezone.localdate()
        if (method.anio_vencimiento, method.mes_vencimiento) < (today.year, today.month):
            raise ValidationError({"medio_pago_id": "La tarjeta está vencida."})


@transaction.atomic
def register_method(*, actor, data):
    from .serializers import PaymentMethodCreateSerializer

    authorized_user(actor)
    serializer = PaymentMethodCreateSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    # All funding/management paths lock wallet before instrument; no inventory lock.
    Wallet.objects.select_for_update().get(user=actor)
    attrs = dict(serializer.validated_data)
    number = attrs.pop("numero")
    digest = salted_hmac(
        "wallet-payment-number", f"{actor.pk}:{attrs['tipo']}:{number}", algorithm="sha256"
    ).hexdigest()
    existing = PaymentMethod.objects.filter(
        user=actor, tipo=attrs["tipo"], fingerprint=digest
    ).first()
    if existing:
        raise ValidationError(
            {"numero": "Este medio ya está registrado, incluso si fue desactivado."}
        )
    method = PaymentMethod(user=actor, fingerprint=digest, ultimos_cuatro=number[-4:], **attrs)
    validate_expiry(method)
    method.save()
    return method


@transaction.atomic
def manage_method(*, actor, method_id, alias=None, deactivate=False):
    authorized_user(actor)
    Wallet.objects.select_for_update().get(user=actor)
    method = PaymentMethod.objects.select_for_update().filter(pk=method_id, user=actor).first()
    if method is None:
        raise NotFound()
    if deactivate:
        method.activo = False
    elif alias is not None:
        method.alias = alias
    method.save(update_fields=["alias", "activo"])
    return method


@transaction.atomic
def deposit_from_method(*, actor, method_id, amount, key, reference="Depósito simulado"):
    from apps.sales.rules import money

    authorized_user(actor)
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValidationError({"Idempotency-Key": "Envía una clave de 1 a 128 caracteres."})
    amount = money(amount).quantize(Decimal("0.01"))
    if amount < MIN_DEPOSIT:
        raise ValidationError({"monto": "El depósito mínimo es 1000.00."})
    fingerprint = hashlib.sha256(
        json.dumps(
            [method_id, str(amount), reference], ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    wallet = Wallet.objects.select_for_update().get(user=actor)
    previous = MovimientoBilletera.objects.filter(wallet=wallet, idempotency_key=key).first()
    if previous:
        if previous.request_fingerprint != fingerprint:
            raise ValidationError({"Idempotency-Key": "La clave ya se usó con datos diferentes."})
        return wallet, previous
    method = PaymentMethod.objects.select_for_update().filter(pk=method_id, user=actor).first()
    if method is None:
        raise NotFound()
    if not method.activo:
        raise ValidationError({"medio_pago_id": "El medio fue desactivado."})
    validate_expiry(method)
    if wallet.balance + amount > MAX_BALANCE:
        raise ValidationError({"monto": "El saldo resultante excede la capacidad de la billetera."})
    movement = depositar(wallet.pk, amount, reference)
    movement.medio_pago = method
    movement.idempotency_key = key
    movement.request_fingerprint = fingerprint
    movement.save(update_fields=["medio_pago", "idempotency_key", "request_fingerprint"])
    wallet.refresh_from_db()
    return wallet, movement
