from decimal import Decimal

from django.conf import settings
from django.db import models


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
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de Billetera"
        verbose_name_plural = "Movimientos de Billetera"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.tipo} - ${self.valor} ({self.wallet.user}) [Saldo: ${self.saldo_resultante}]"
