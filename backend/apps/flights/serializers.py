from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Ciudad, ClaseTiquete, Ruta, Silla, TipoVuelo, Vuelo


class SillaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Silla
        fields = ["id", "numero_silla", "clase", "estado", "espacio_extra"]


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


class RutaWriteSerializer(serializers.Serializer):
    origen_id = serializers.IntegerField(min_value=1)
    destino_id = serializers.IntegerField(min_value=1)
    duracion_min = serializers.IntegerField(min_value=1, max_value=2880)
    tipo_vuelo = serializers.ChoiceField(choices=TipoVuelo.choices)
    activa = serializers.BooleanField(default=True, required=False)

    def validate(self, attrs):
        origen_id = attrs.get("origen_id")
        destino_id = attrs.get("destino_id")
        if origen_id and destino_id and origen_id == destino_id:
            raise serializers.ValidationError(
                {"destino_id": "El origen y el destino no pueden ser iguales."}
            )
        return attrs


class RutaUpdateSerializer(serializers.Serializer):
    duracion_min = serializers.IntegerField(min_value=1, max_value=2880, required=False)
    activa = serializers.BooleanField(required=False)


class ProgramarVueloSerializer(serializers.Serializer):
    origen_id = serializers.IntegerField(min_value=1)
    destino_id = serializers.IntegerField(min_value=1)
    fecha_salida = serializers.DateField()
    hora_salida = serializers.TimeField()
    costo_persona_economica = serializers.DecimalField(max_digits=12, decimal_places=2)
    costo_persona_primera = serializers.DecimalField(max_digits=12, decimal_places=2)


class EditarVueloSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: "Campo no editable." for key in unknown})
        return super().to_internal_value(data)

    fecha_salida = serializers.DateField(required=False, allow_null=True)
    hora_salida = serializers.TimeField(required=False, allow_null=True)
    costo_persona_economica = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    costo_persona_primera = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, attrs):
        if not any(v is not None for k, v in attrs.items() if k != "motivo"):
            raise serializers.ValidationError("Debes indicar al menos un campo para modificar.")
        return attrs


class CancelarVueloSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=500, min_length=3, trim_whitespace=True)
    alternativa = serializers.ChoiceField(
        choices=["REINTEGRO", "REUBICACION"], default="REINTEGRO", required=False
    )


class EffectivePriceMixin:
    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_precio_vigente_economica(self, obj):
        from apps.sales.services import resolver_precio_vigente

        return str(resolver_precio_vigente(obj, ClaseTiquete.ECONOMICA))

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_precio_vigente_primera(self, obj):
        from apps.sales.services import resolver_precio_vigente

        return str(resolver_precio_vigente(obj, ClaseTiquete.PRIMERA_CLASE))


class VueloListSerializer(EffectivePriceMixin, serializers.ModelSerializer):
    currency = serializers.CharField(default="COP", read_only=True)
    precio_vigente_economica = serializers.SerializerMethodField()
    precio_vigente_primera = serializers.SerializerMethodField()

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
            "currency",
            "precio_vigente_economica",
            "precio_vigente_primera",
            "costo_persona_economica",
            "costo_persona_primera",
            "capacidad_total",
            "cupos_disponibles_primera",
            "cupos_disponibles_economica",
            "estado",
        ]


class VueloDetalleSerializer(EffectivePriceMixin, serializers.ModelSerializer):
    currency = serializers.CharField(default="COP", read_only=True)
    precio_vigente_economica = serializers.SerializerMethodField()
    precio_vigente_primera = serializers.SerializerMethodField()

    ruta = RutaSerializer(read_only=True)
    creado_por = serializers.IntegerField(source="creado_por_id", read_only=True)

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
            "currency",
            "precio_vigente_economica",
            "precio_vigente_primera",
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


class FlightSearchRequestSerializer(serializers.Serializer):
    origen_id = serializers.IntegerField(required=False, allow_null=True)
    destino_id = serializers.IntegerField(required=False, allow_null=True)
    origen = serializers.CharField(required=False, allow_blank=True)
    destino = serializers.CharField(required=False, allow_blank=True)
    fecha_salida = serializers.DateField(required=False, allow_null=True)
    fecha_regreso = serializers.DateField(required=False, allow_null=True)
    tipo_trayecto = serializers.ChoiceField(
        choices=["UNICO", "COMPLETO"], default="UNICO", required=False
    )
    pasajeros = serializers.IntegerField(min_value=1, max_value=5, default=1, required=False)
    clase = serializers.ChoiceField(
        choices=ClaseTiquete.choices, required=False, allow_blank=True, default=""
    )
    tipo_vuelo = serializers.ChoiceField(
        choices=TipoVuelo.choices, required=False, allow_blank=True, default=""
    )
    precio_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, attrs):
        tipo_trayecto = attrs.get("tipo_trayecto", "UNICO")
        fecha_salida = attrs.get("fecha_salida")
        fecha_regreso = attrs.get("fecha_regreso")

        if tipo_trayecto == "COMPLETO" and fecha_salida and fecha_regreso:
            if fecha_regreso < fecha_salida:
                raise serializers.ValidationError(
                    {
                        "fecha_regreso": (
                            "La fecha de regreso no puede ser anterior a la fecha de salida."
                        )
                    }
                )

        origen_id = attrs.get("origen_id")
        destino_id = attrs.get("destino_id")
        if origen_id and destino_id and origen_id == destino_id:
            raise serializers.ValidationError(
                {"destino_id": "El origen y el destino deben ser diferentes."}
            )
        return attrs


class FlightSearchResultSerializer(serializers.Serializer):
    tipo_trayecto = serializers.CharField()
    pasajeros = serializers.IntegerField()
    clase = serializers.CharField()
    vuelos_ida = VueloListSerializer(many=True)
    vuelos_regreso = VueloListSerializer(many=True)


class CrearRutaSerializer(serializers.Serializer):
    origen_id = serializers.IntegerField(min_value=1, required=False)
    destino_id = serializers.IntegerField(min_value=1, required=False)
    origen = serializers.IntegerField(min_value=1, required=False)
    destino = serializers.IntegerField(min_value=1, required=False)
    tipo_vuelo = serializers.ChoiceField(choices=TipoVuelo.choices)
    duracion_min = serializers.IntegerField(min_value=1, max_value=2880)
    activa = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        origen_id = attrs.get("origen_id") or attrs.get("origen")
        destino_id = attrs.get("destino_id") or attrs.get("destino")
        if not origen_id:
            raise serializers.ValidationError({"origen_id": "Este campo es requerido."})
        if not destino_id:
            raise serializers.ValidationError({"destino_id": "Este campo es requerido."})
        if origen_id == destino_id:
            raise serializers.ValidationError(
                {"destino_id": "El origen y el destino no pueden ser iguales."}
            )
        attrs["origen_id"] = origen_id
        attrs["destino_id"] = destino_id
        return attrs
