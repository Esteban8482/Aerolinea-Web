from decimal import Decimal

from rest_framework import serializers
from apps.reference.models import Country, Locality, Subdivision

from apps.users.serializers import StrictSerializer

from .models import MovimientoBilletera, PaymentMethod, Wallet


class PaymentMethodSerializer(serializers.ModelSerializer):
    numero_enmascarado = serializers.SerializerMethodField()
    disponibilidad = serializers.SerializerMethodField()

    def get_numero_enmascarado(self, obj) -> str:
        return "**** " + obj.ultimos_cuatro

    def get_disponibilidad(self, obj) -> str:
        if not obj.activo:
            return "INACTIVO"
        if obj.tipo == "TARJETA":
            from django.utils import timezone
            today = timezone.localdate()
            if (obj.anio_vencimiento or 0, obj.mes_vencimiento or 0) < (today.year, today.month):
                return "VENCIDO"
        return "DISPONIBLE"

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "tipo",
            "alias",
            "titular",
            "entidad",
            "marca",
            "cardholder_first_name",
            "cardholder_last_name",
            "numero_enmascarado",
            "mes_vencimiento",
            "anio_vencimiento",
            "activo",
            "disponibilidad",
            "creado_en",
            "billing_country",
            "billing_subdivision",
            "billing_city",
            "billing_address",
            "postal_code",
        ]
        read_only_fields = fields


class PaymentMethodCreateSerializer(StrictSerializer):
    tipo = serializers.ChoiceField(choices=PaymentMethod.Kind.choices)
    alias = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    titular = serializers.CharField(max_length=160)
    entidad = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    numero = serializers.CharField(max_length=40, write_only=True, trim_whitespace=False)
    mes_vencimiento = serializers.IntegerField(min_value=1, max_value=12, required=False)
    anio_vencimiento = serializers.IntegerField(min_value=2000, max_value=9999, required=False)
    cardholder_first_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    cardholder_last_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    billing_country_id = serializers.PrimaryKeyRelatedField(
        source="billing_country",
        queryset=Country.objects.filter(active=True),
        required=False,
        allow_null=True,
    )
    billing_subdivision_id = serializers.PrimaryKeyRelatedField(
        source="billing_subdivision",
        queryset=Subdivision.objects.filter(active=True),
        required=False,
        allow_null=True,
    )
    billing_city_id = serializers.PrimaryKeyRelatedField(
        source="billing_city",
        queryset=Locality.objects.filter(active=True, country__active=True),
        required=False,
        allow_null=True,
    )
    billing_address = serializers.CharField(max_length=200, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    def validate(self, attrs):
        number = attrs["numero"].replace(" ", "").replace("-", "")
        if attrs["tipo"] == "TARJETA":
            synthetic_cards = {
                "4111111111111111": "VISA",
                "5555555555554444": "MASTERCARD",
            }
            if not (number.isascii() and number.isdigit() and len(number) == 16):
                raise serializers.ValidationError(
                    {"numero": "La tarjeta debe contener exactamente 16 dígitos ASCII."}
                )
            brand = synthetic_cards.get(number)
            if brand is None:
                raise serializers.ValidationError(
                    {"numero": "Usa únicamente una tarjeta sintética documentada: Visa 4111 1111 1111 1111 o Mastercard 5555 5555 5555 4444."}
                )
            attrs["marca"] = brand
        else:
            if not (number.isascii() and number.isdigit() and 6 <= len(number) <= 34):
                raise serializers.ValidationError({"numero": "Número de cuenta simulado inválido."})
        attrs["numero"] = number
        expiry = {"mes_vencimiento", "anio_vencimiento"}
        if attrs["tipo"] == "TARJETA" and not expiry.issubset(attrs):
            raise serializers.ValidationError({"mes_vencimiento": "La tarjeta requiere mes y año."})
        if attrs["tipo"] == "CUENTA_BANCARIA" and expiry.intersection(attrs):
            raise serializers.ValidationError({"tipo": "La cuenta bancaria no tiene vencimiento."})
        if attrs["tipo"] == "TARJETA":
            first = attrs.get("cardholder_first_name", "").strip()
            last = attrs.get("cardholder_last_name", "").strip()
            if not first or not last:
                parts = attrs["titular"].strip().split()
                if len(parts) < 2:
                    raise serializers.ValidationError(
                        {"titular": "Ingresa nombres y apellidos del titular."}
                    )
                first = first or " ".join(parts[:-1])
                last = last or parts[-1]
            attrs["cardholder_first_name"] = first
            attrs["cardholder_last_name"] = last
            attrs["titular"] = f"{first} {last}".strip()
            country = attrs.get("billing_country")
            city = attrs.get("billing_city")
            subdivision = attrs.get("billing_subdivision")
            if country is None:
                raise serializers.ValidationError({"billing_country_id": "El país de facturación es obligatorio."})
            if city is None:
                raise serializers.ValidationError({"billing_city_id": "La ciudad de facturación es obligatoria."})
            if city.country_id != country.id:
                raise serializers.ValidationError(
                    {"billing_city_id": "La ciudad no pertenece al país seleccionado."}
                )
            if city.subdivision_id:
                if subdivision is None or city.subdivision_id != subdivision.id:
                    raise serializers.ValidationError(
                        {"billing_subdivision_id": "La división no corresponde a la ciudad seleccionada."}
                    )
                if subdivision.country_id != country.id:
                    raise serializers.ValidationError(
                        {"billing_subdivision_id": "La división no pertenece al país seleccionado."}
                    )
            elif subdivision is not None:
                raise serializers.ValidationError(
                    {"billing_subdivision_id": "Esta ciudad no requiere una división territorial."}
                )
            if not attrs.get("billing_address", "").strip():
                raise serializers.ValidationError(
                    {"billing_address": "La dirección de facturación es obligatoria."}
                )
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
    referencia = serializers.CharField(max_length=120, required=False, default="Dinero añadido")
