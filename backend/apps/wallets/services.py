from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import APIException, PermissionDenied

from .models import MovimientoBilletera, Wallet


class InsufficientBalance(APIException):
    status_code = 400
    default_code = "insufficient_wallet_balance"
    default_detail = "Saldo insuficiente en la billetera para completar la operación."


class InvalidAmount(APIException):
    status_code = 400
    default_code = "invalid_amount"
    default_detail = "El monto debe ser un valor positivo."


@transaction.atomic
def depositar(wallet_id: int, monto: Decimal, referencia: str = "") -> MovimientoBilletera:
    from apps.sales.rules import money

    monto = money(monto)
    if monto <= Decimal("0.00"):
        raise InvalidAmount()

    wallet = Wallet.objects.select_for_update(of=("self",)).select_related("user").get(pk=wallet_id)
    if wallet.user.role == "ROOT":
        raise PermissionDenied("ROOT no tiene acceso a operaciones financieras.")
    if wallet.balance + monto > Decimal("999999999999.99"):
        raise InvalidAmount("El saldo resultante excede la capacidad de la billetera.")
    wallet.balance += monto
    wallet.save(update_fields=["balance"])

    return MovimientoBilletera.objects.create(
        wallet=wallet,
        tipo=MovimientoBilletera.Tipo.DEPOSITO,
        valor=monto,
        saldo_resultante=wallet.balance,
        referencia=referencia,
    )


@transaction.atomic
def debitar_para_compra(
    wallet_id: int, monto: Decimal, referencia: str = ""
) -> MovimientoBilletera:
    from apps.sales.rules import money

    monto = money(monto)
    if monto <= Decimal("0.00"):
        raise InvalidAmount()

    wallet = Wallet.objects.select_for_update(of=("self",)).select_related("user").get(pk=wallet_id)
    if wallet.user.role == "ROOT":
        raise PermissionDenied("ROOT no tiene acceso a operaciones financieras.")
    if wallet.balance < monto:
        raise InsufficientBalance()

    wallet.balance -= monto
    wallet.save(update_fields=["balance"])

    return MovimientoBilletera.objects.create(
        wallet=wallet,
        tipo=MovimientoBilletera.Tipo.COMPRA,
        valor=monto,
        saldo_resultante=wallet.balance,
        referencia=referencia,
    )


@transaction.atomic
def reembolsar_a_billetera(
    wallet_id: int, monto: Decimal, referencia: str = ""
) -> MovimientoBilletera:
    from apps.sales.rules import money

    monto = money(monto)
    if monto <= Decimal("0.00"):
        raise InvalidAmount()

    wallet = Wallet.objects.select_for_update(of=("self",)).select_related("user").get(pk=wallet_id)
    if wallet.user.role == "ROOT":
        raise PermissionDenied("ROOT no tiene acceso a operaciones financieras.")
    if wallet.balance + monto > Decimal("999999999999.99"):
        raise InvalidAmount("El saldo resultante excede la capacidad de la billetera.")
    wallet.balance += monto
    wallet.save(update_fields=["balance"])

    return MovimientoBilletera.objects.create(
        wallet=wallet,
        tipo=MovimientoBilletera.Tipo.REEMBOLSO,
        valor=monto,
        saldo_resultante=wallet.balance,
        referencia=referencia,
    )
