from decimal import Decimal

from django.conf import settings
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="wallet"
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="wallet_balance_gte_0")
        ]
