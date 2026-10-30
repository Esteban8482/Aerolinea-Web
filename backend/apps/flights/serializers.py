from decimal import Decimal

from rest_framework import serializers

from .models import Ciudad, Ruta, Vuelo


class CiudadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ciudad
        fields = [
            "id",
            "nombre",
            "codigo_pais",
            "zona_horaria",
            "es_capital_principal",
            "origen_internacional",
            "destino_internacional",
        ]


class RutaSerializer(serializers.ModelSerializer):
    origen = CiudadSerializer(read_only=True)
    destino = CiudadSerializer(read_only=True)

    class Meta:
        model = Ruta
        fields = ["id", "origen", "destino", "tipo_vuelo", "duracion_min", "activa"]


class ProgramarVueloSerializer(serializers.Serializer):
    origen_id = serializers.IntegerField(min_value=1)
    destino_id = serializers.IntegerField(min_value=1)
    fecha_salida = serializers.DateField()
    hora_salida = serializers.TimeField()
    costo_persona_economica = serializers.DecimalField(
        max_digits=12, decimal_places=2
    )
    costo_persona_primera = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class EditarVueloSerializer(serializers.Serializer):
    fecha_salida = serializers.DateField(required=False, allow_null=True)
    hora_salida = serializers.TimeField(required=False, allow_null=True)
    costo_persona_economica = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    costo_persona_primera = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, attrs):
        if not any(v is not None for v in attrs.values()):
            raise serializers.ValidationError("Debes indicar al menos un campo para modificar.")
        return attrs


class CancelarVueloSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=500, min_length=3, trim_whitespace=True)
    alternativa = serializers.ChoiceField(
        choices=["REINTEGRO", "REUBICACION"], default="REINTEGRO", required=False
    )


class VueloListSerializer(serializers.ModelSerializer):
    origen = serializers.CharField(source="ruta.origen.nombre", read_only=True)
    destino = serializers.CharField(source="ruta.destino.nombre", read_only=True)

    class Meta:
        model = Vuelo
        fields = [
            "id",
            "codigo_vuelo",
            "tipo_vuelo",
            "origen",
            "destino",
            "fecha_salida",
            "hora_salida",
            "salida_utc",
            "tiempo_vuelo_min",
            "fecha_llegada",
            "hora_llegada",
            "llegada_utc",
            "costo_persona_economica",
            "costo_persona_primera",
            "capacidad_total",
            "cupos_disponibles_primera",
            "cupos_disponibles_economica",
            "estado",
        ]


class VueloDetalleSerializer(serializers.ModelSerializer):
    ruta = RutaSerializer(read_only=True)
    creado_por = serializers.CharField(source="creado_por.email", read_only=True)

    class Meta:
        model = Vuelo
        fields = [
            "id",
            "codigo_vuelo",
            "ruta",
            "tipo_vuelo",
            "fecha_salida",
            "hora_salida",
            "salida_utc",
            "tiempo_vuelo_min",
            "fecha_llegada",
            "hora_llegada",
            "llegada_utc",
            "costo_persona_economica",
            "costo_persona_primera",
            "capacidad_total",
            "cupos_primera_clase",
            "cupos_economica",
            "cupos_disponibles_primera",
            "cupos_disponibles_economica",
            "estado",
            "motivo_cancelacion",
            "cancelado_en",
            "creado_por",
            "creado_en",
            "actualizado_en",
        ]
