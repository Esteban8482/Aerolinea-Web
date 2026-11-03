from decimal import Decimal

from rest_framework import serializers

from .models import MovimientoBilletera, Wallet


class MovimientoBilleteraSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoBilletera
        fields = ["id", "tipo", "valor", "saldo_resultante", "referencia", "creado_en"]


class WalletSerializer(serializers.ModelSerializer):
    movimientos = MovimientoBilleteraSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "balance", "movimientos"]


class DepositarSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("1000.00"))
    referencia = serializers.CharField(max_length=120, required=False, default="Depósito manual")
