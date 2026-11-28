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
    confirmed = serializers.BooleanField()

    def validate_confirmed(self, value):
        if not value:
            raise serializers.ValidationError("Confirma expresamente la cancelación.")
        return value


class EffectivePriceMixin:
    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_precio_vigente_economica(self, obj):
        from apps.sales.services import resolver_precio_vigente

        return str(resolver_precio_vigente(obj, ClaseTiquete.ECONOMICA))

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_precio_vigente_primera(self, obj):
        from apps.sales.services import resolver_precio_vigente

        return str(resolver_precio_vigente(obj, ClaseTiquete.PRIMERA_CLASE))

    @extend_schema_field(serializers.CharField())
    def get_clase_aplicable(self, obj):
        clase = self.context.get("clase")
        if clase:
            return clase
        passengers = self.context.get("pasajeros", 1)
        candidates = []
        if obj.cupos_disponibles_economica >= passengers:
            candidates.append((self.get_precio_vigente_economica(obj), ClaseTiquete.ECONOMICA))
        if obj.cupos_disponibles_primera >= passengers:
            candidates.append((self.get_precio_vigente_primera(obj), ClaseTiquete.PRIMERA_CLASE))
        if not candidates:
            return ""
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][1]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_precio_por_persona(self, obj):
        clase = self.context.get("clase") or self.get_clase_aplicable(obj)
        if not clase:
            return "0.00"
        from apps.sales.services import resolver_precio_vigente

        return str(resolver_precio_vigente(obj, clase, self.context.get("now")))

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_precio_original(self, obj):
        clase = self.context.get("clase") or self.get_clase_aplicable(obj)
        if not clase:
            return "0.00"
        field = (
            obj.costo_persona_primera
            if clase == ClaseTiquete.PRIMERA_CLASE
            else obj.costo_persona_economica
        )
        return str(field)

    @extend_schema_field(serializers.BooleanField())
    def get_tiene_promocion(self, obj):
        from apps.sales.services import resolver_precio_vigente

        clase = self.context.get("clase") or self.get_clase_aplicable(obj)
        if not clase:
            return False
        return resolver_precio_vigente(
            obj, clase, self.context.get("now")
        ) < (
            obj.costo_persona_primera
            if clase == ClaseTiquete.PRIMERA_CLASE
            else obj.costo_persona_economica
        )

    @extend_schema_field(serializers.IntegerField())
    def get_asientos_disponibles(self, obj):
        clase = self.context.get("clase") or self.get_clase_aplicable(obj)
        if clase == ClaseTiquete.PRIMERA_CLASE:
            return obj.cupos_disponibles_primera
        if clase == ClaseTiquete.ECONOMICA:
            return obj.cupos_disponibles_economica
        return max(obj.cupos_disponibles_primera, obj.cupos_disponibles_economica)


class VueloListSerializer(EffectivePriceMixin, serializers.ModelSerializer):
    currency = serializers.CharField(default="COP", read_only=True)
    precio_vigente_economica = serializers.SerializerMethodField()
    precio_vigente_primera = serializers.SerializerMethodField()
    clase_aplicable = serializers.SerializerMethodField()
    precio_por_persona = serializers.SerializerMethodField()
    precio_original = serializers.SerializerMethodField()
    tiene_promocion = serializers.SerializerMethodField()
    asientos_disponibles = serializers.SerializerMethodField()

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
            "clase_aplicable",
            "precio_por_persona",
            "precio_original",
            "tiene_promocion",
            "asientos_disponibles",
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
    selected_outbound_id = serializers.IntegerField(required=False, min_value=1)
    precio_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    precio_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    orden = serializers.ChoiceField(
        choices=[
            "precio_asc",
            "precio_desc",
            "salida_asc",
            "salida_desc",
        ],
        required=False,
        default="salida_asc",
    )

    def validate(self, attrs):
        if "origen" in self.initial_data or "destino" in self.initial_data:
            raise serializers.ValidationError(
                "Selecciona origen_id/destino_id del catálogo de vuelos."
            )
        for field in ("origen_id", "destino_id"):
            if (
                attrs.get(field) is not None
                and not Ciudad.objects.filter(pk=attrs[field], activa=True).exists()
            ):
                raise serializers.ValidationError({field: "Selecciona una ciudad con cobertura."})

        tipo_trayecto = attrs.get("tipo_trayecto", "UNICO")
        fecha_salida = attrs.get("fecha_salida")
        fecha_regreso = attrs.get("fecha_regreso")

        if tipo_trayecto == "COMPLETO":
            if not fecha_salida:
                raise serializers.ValidationError(
                    {"fecha_salida": "La búsqueda ida y regreso requiere fecha de salida."}
                )
            if not fecha_regreso:
                raise serializers.ValidationError(
                    {"fecha_regreso": "La búsqueda ida y regreso requiere fecha de regreso."}
                )
            if fecha_regreso < fecha_salida:
                raise serializers.ValidationError(
                    {
                        "fecha_regreso": (
                            "La fecha de regreso no puede ser anterior a la fecha de salida."
                        )
                    }
                )

        precio_min = attrs.get("precio_min")
        precio_max = attrs.get("precio_max")
        if precio_min is not None and precio_max is not None and precio_min > precio_max:
            raise serializers.ValidationError(
                {"precio_min": "El precio mínimo no puede superar el precio máximo."}
            )

        origen_id = attrs.get("origen_id")
        destino_id = attrs.get("destino_id")
        if origen_id and destino_id and origen_id == destino_id:
            raise serializers.ValidationError(
                {"destino_id": "El origen y el destino deben ser diferentes."}
            )
        selected_outbound_id = attrs.get("selected_outbound_id")
        if selected_outbound_id is not None:
            if not Vuelo.objects.filter(pk=selected_outbound_id, estado="PROGRAMADO").exists():
                raise serializers.ValidationError(
                    {"selected_outbound_id": "Selecciona un vuelo de ida válido."}
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
