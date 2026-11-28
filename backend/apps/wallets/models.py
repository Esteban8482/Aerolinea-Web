from decimal import Decimal

from django.conf import settings
from django.db import models


class PaymentMethod(models.Model):
    class Kind(models.TextChoices):
        CARD = "TARJETA", "Tarjeta"
        BANK = "CUENTA_BANCARIA", "Cuenta bancaria"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_methods"
    )
    tipo = models.CharField(max_length=20, choices=Kind.choices)
    alias = models.CharField(max_length=80)
    titular = models.CharField(max_length=160)
    entidad = models.CharField(max_length=100)
    cardholder_first_name = models.CharField(max_length=80, blank=True, default="")
    cardholder_last_name = models.CharField(max_length=80, blank=True, default="")
    marca = models.CharField(max_length=20, blank=True, default="")
    billing_country = models.ForeignKey(
        "reference.Country",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="billing_payment_methods",
    )
    billing_subdivision = models.ForeignKey(
        "reference.Subdivision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="billing_payment_methods",
    )
    billing_city = models.ForeignKey(
        "reference.Locality",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="billing_payment_methods",
    )
    billing_address = models.CharField(max_length=200, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    # Simulation never needs the original number again. Keep only a keyed fingerprint
    # for deduplication and its last four digits; no PAN/account number or CVV at rest.
    fingerprint = models.CharField(max_length=64, editable=False)
    ultimos_cuatro = models.CharField(max_length=4, editable=False)
    mes_vencimiento = models.PositiveSmallIntegerField(null=True, blank=True)
    anio_vencimiento = models.PositiveSmallIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tipo", "fingerprint"], name="unique_owner_payment_fingerprint"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        tipo="CUENTA_BANCARIA",
                        mes_vencimiento__isnull=True,
                        anio_vencimiento__isnull=True,
                    )
                    | models.Q(
                        tipo="TARJETA",
                        mes_vencimiento__gte=1,
                        mes_vencimiento__lte=12,
                        mes_vencimiento__isnull=False,
                        anio_vencimiento__isnull=False,
                    )
                ),
                name="payment_method_valid_expiry",
            ),
        ]


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="wallet"
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Billetera"
        verbose_name_plural = "Billeteras"
        constraints = [
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="wallet_balance_gte_0")
        ]

    def __str__(self):
        return f"Billetera de {self.user} - Saldo: ${self.balance}"


class MovimientoBilletera(models.Model):
    class Tipo(models.TextChoices):
        DEPOSITO = "DEPOSITO", "Depósito"
        RETIRO = "RETIRO", "Retiro"
        COMPRA = "COMPRA", "Compra"
        REEMBOLSO = "REEMBOLSO", "Reembolso"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_resultante = models.DecimalField(max_digits=14, decimal_places=2)
    referencia = models.CharField(max_length=120, blank=True, default="")
    medio_pago = models.ForeignKey(
        PaymentMethod, null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos"
    )
    idempotency_key = models.CharField(max_length=128, null=True, blank=True, editable=False)
    request_fingerprint = models.CharField(max_length=64, blank=True, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de Billetera"
        verbose_name_plural = "Movimientos de Billetera"
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["wallet", "idempotency_key"], name="unique_wallet_deposit_key"
            ),
            models.CheckConstraint(condition=models.Q(valor__gt=0), name="movement_positive"),
            models.CheckConstraint(
                condition=models.Q(saldo_resultante__gte=0), name="movement_balance_nonnegative"
            ),
        ]

    def __str__(self):
        return f"{self.tipo} - ${self.valor} ({self.wallet.user}) [Saldo: ${self.saldo_resultante}]"
