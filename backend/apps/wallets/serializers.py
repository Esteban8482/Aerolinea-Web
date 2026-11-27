from decimal import Decimal

from rest_framework import serializers

from apps.users.serializers import StrictSerializer

from .models import MovimientoBilletera, PaymentMethod, Wallet


class PaymentMethodSerializer(serializers.ModelSerializer):
    numero_enmascarado = serializers.SerializerMethodField()

    def get_numero_enmascarado(self, obj) -> str:
        return "**** " + obj.ultimos_cuatro

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "tipo",
            "alias",
            "titular",
            "entidad",
            "numero_enmascarado",
            "mes_vencimiento",
            "anio_vencimiento",
            "activo",
            "creado_en",
        ]
        read_only_fields = fields


class PaymentMethodCreateSerializer(StrictSerializer):
    tipo = serializers.ChoiceField(choices=PaymentMethod.Kind.choices)
    alias = serializers.CharField(max_length=80)
    titular = serializers.CharField(max_length=160)
    entidad = serializers.CharField(max_length=100)
    numero = serializers.CharField(max_length=40, write_only=True, trim_whitespace=False)
    mes_vencimiento = serializers.IntegerField(min_value=1, max_value=12, required=False)
    anio_vencimiento = serializers.IntegerField(min_value=2000, max_value=9999, required=False)

    def validate(self, attrs):
        # Formatting separators are accepted; never echo back an invalid number.
        number = attrs["numero"].replace(" ", "").replace("-", "")
        minimum, maximum = (13, 19) if attrs["tipo"] == "TARJETA" else (6, 34)
        if not (number.isascii() and number.isdigit() and minimum <= len(number) <= maximum):
            raise serializers.ValidationError({"numero": "Número simulado inválido."})
        attrs["numero"] = number
        expiry = {"mes_vencimiento", "anio_vencimiento"}
        if attrs["tipo"] == "TARJETA" and not expiry.issubset(attrs):
            raise serializers.ValidationError({"mes_vencimiento": "La tarjeta requiere mes y año."})
        if attrs["tipo"] == "CUENTA_BANCARIA" and expiry.intersection(attrs):
            raise serializers.ValidationError({"tipo": "La cuenta bancaria no tiene vencimiento."})
        return attrs


class PaymentMethodUpdateSerializer(StrictSerializer):
    alias = serializers.CharField(max_length=80)


class MovimientoBilleteraSerializer(serializers.ModelSerializer):
    medio_pago = PaymentMethodSerializer(read_only=True)

    class Meta:
        model = MovimientoBilletera
        fields = [
            "id",
            "tipo",
            "valor",
            "saldo_resultante",
            "referencia",
            "creado_en",
            "medio_pago",
        ]


class WalletSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(default="COP", read_only=True)
    movimientos = MovimientoBilleteraSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "balance", "currency", "movimientos"]


class DepositResultSerializer(WalletSerializer):
    deposit = MovimientoBilleteraSerializer(read_only=True)

    class Meta(WalletSerializer.Meta):
        fields = [*WalletSerializer.Meta.fields, "deposit"]


class PaymentMethodPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = PaymentMethodSerializer(many=True)


class MovementPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = MovimientoBilleteraSerializer(many=True)


class DepositarSerializer(StrictSerializer):
    monto = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("1000.00"))
    medio_pago_id = serializers.IntegerField(min_value=1)
    referencia = serializers.CharField(max_length=120, required=False, default="Depósito simulado")
