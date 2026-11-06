
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.flights.models import ClaseTiquete
from apps.flights.serializers import SillaSerializer, VueloListSerializer

from .models import (
    Compra,
    HistorialBusqueda,
    Reserva,
    TipoTrayecto,
    Tiquete,
    Viajero,
)


class ViajeroInputSerializer(serializers.Serializer):
    documento = serializers.CharField(max_length=30)
    tipo_documento = serializers.CharField(max_length=20, default="CC", required=False)
    nombres = serializers.CharField(max_length=80)
    apellidos = serializers.CharField(max_length=80)
    fecha_nacimiento = serializers.DateField()
    genero = serializers.CharField(max_length=20, default="OTRO", required=False)
    telefono = serializers.CharField(max_length=30, default="", required=False, allow_blank=True)
    correo = serializers.EmailField()
    nombre_contacto = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    telefono_contacto = serializers.CharField(
        max_length=30, required=False, allow_blank=True, default=""
    )


class ViajeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Viajero
        fields = [
            "id",
            "documento",
            "tipo_documento",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "genero",
            "telefono",
            "correo",
            "nombre_contacto",
            "telefono_contacto",
        ]


class CrearReservaSerializer(serializers.Serializer):
    vuelo_id = serializers.IntegerField(min_value=1)
    clase = serializers.ChoiceField(
        choices=ClaseTiquete.choices, default=ClaseTiquete.ECONOMICA
    )
    tipo_trayecto = serializers.ChoiceField(
        choices=TipoTrayecto.choices, default=TipoTrayecto.UNICO
    )
    vuelo_regreso_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    viajeros = ViajeroInputSerializer(many=True)

    def validate_viajeros(self, value):
        if not (1 <= len(value) <= 5):
            raise serializers.ValidationError("La cantidad de viajeros debe estar entre 1 y 5.")
        return value


class ReservaDetailSerializer(serializers.ModelSerializer):
    vuelo = VueloListSerializer(read_only=True)
    vuelo_regreso = VueloListSerializer(read_only=True)
    viajeros = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = [
            "id",
            "vuelo",
            "vuelo_regreso",
            "tipo_trayecto",
            "clase",
            "limite_vigencia",
            "estado",
            "creada_en",
            "viajeros",
        ]

    @extend_schema_field(ViajeroSerializer(many=True))
    def get_viajeros(self, obj):
        rvs = obj.viajeros_reserva.select_related("viajero")
        return [ViajeroSerializer(rv.viajero).data for rv in rvs]


class ComprarTiquetesSerializer(serializers.Serializer):
    vuelo_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    clase = serializers.ChoiceField(
        choices=ClaseTiquete.choices, default=ClaseTiquete.ECONOMICA, required=False
    )
    tipo_trayecto = serializers.ChoiceField(
        choices=TipoTrayecto.choices, default=TipoTrayecto.UNICO, required=False
    )
    vuelo_regreso_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reserva_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    viajeros = ViajeroInputSerializer(many=True, required=False)

    def validate(self, attrs):
        reserva_id = attrs.get("reserva_id")
        viajeros = attrs.get("viajeros")
        vuelo_id = attrs.get("vuelo_id")

        if not reserva_id:
            if not vuelo_id:
                raise serializers.ValidationError(
                    "Debes indicar un vuelo_id si no proporcionas una reserva_id."
                )
            if not viajeros or not (1 <= len(viajeros) <= 5):
                raise serializers.ValidationError(
                    "Debes indicar entre 1 y 5 viajeros para la compra directa."
                )
        return attrs


class TiqueteSerializer(serializers.ModelSerializer):
    vuelo = VueloListSerializer(read_only=True)
    viajero = ViajeroSerializer(read_only=True)
    silla = SillaSerializer(read_only=True)

    class Meta:
        model = Tiquete
        fields = [
            "id",
            "codigo_tiquete",
            "vuelo",
            "viajero",
            "silla",
            "clase",
            "precio_pagado",
            "numero_cambios_silla",
            "estado_checkin",
            "fecha_checkin",
            "estado",
        ]


class CompraDetailSerializer(serializers.ModelSerializer):
    tiquetes = TiqueteSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = [
            "id",
            "localizador",
            "valor_pagado",
            "tipo_trayecto",
            "estado",
            "fecha_compra",
            "fecha_cancelacion",
            "tiquetes",
        ]


class CambiarSillaSerializer(serializers.Serializer):
    nueva_silla_id = serializers.IntegerField(min_value=1)


class HistorialBusquedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialBusqueda
        fields = [
            "id",
            "origen",
            "destino",
            "tipo_trayecto",
            "fecha_salida",
            "fecha_regreso",
            "pasajeros",
            "clase",
            "creado_en",
        ]
