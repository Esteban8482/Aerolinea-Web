"""Commercial selectors are restricted to bookable, direct scheduled flights."""

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.reference.catalogue import normalized

from .models import Ciudad, ClaseTiquete, EstadoVuelo, Vuelo


class FlightCityQuery(serializers.Serializer):
    side = serializers.ChoiceField(choices=["origin", "destination"])
    selected_id = serializers.IntegerField(min_value=1, required=False)
    origin_id = serializers.IntegerField(min_value=1, required=False)
    destination_id = serializers.IntegerField(min_value=1, required=False)
    q = serializers.CharField(max_length=100, required=False, allow_blank=True)
    date = serializers.DateField(required=False)
    passengers = serializers.IntegerField(min_value=1, max_value=5, default=1)
    travel_class = serializers.ChoiceField(choices=ClaseTiquete.choices, required=False)
    page = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        if attrs["side"] == "origin" and "origin_id" in attrs:
            raise serializers.ValidationError({"origin_id": "Filtra orígenes por destination_id."})
        if attrs["side"] == "destination" and "destination_id" in attrs:
            raise serializers.ValidationError({"destination_id": "Filtra destinos por origin_id."})
        return attrs


class FlightCityOptionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    country = serializers.CharField(source="locality.country.name")
    country_id = serializers.IntegerField(source="locality.country_id")
    subdivision = serializers.SerializerMethodField()
    subdivision_id = serializers.IntegerField(source="locality.subdivision_id", allow_null=True)
    locality_id = serializers.IntegerField()

    def get_subdivision(self, obj) -> str:
        return obj.locality.subdivision.name if obj.locality.subdivision else ""

    def get_label(self, obj) -> str:
        return ", ".join(
            x for x in [obj.nombre, self.get_subdivision(obj), obj.locality.country.name] if x
        )

    class Meta:
        model = Ciudad
        fields = [
            "id",
            "nombre",
            "label",
            "codigo_pais",
            "country",
            "country_id",
            "subdivision",
            "subdivision_id",
            "locality_id",
        ]


class FlightCityPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = FlightCityOptionSerializer(many=True)


def available_city_options(params):
    flights = Vuelo.objects.filter(
        estado=EstadoVuelo.PROGRAMADO,
        salida_utc__gt=timezone.now(),
        ruta__activa=True,
        ruta__origen__activa=True,
        ruta__destino__activa=True,
    )
    if "date" in params:
        flights = flights.filter(fecha_salida=params["date"])
    people = params.get("passengers", 1)
    travel_class = params.get("travel_class")
    if travel_class == ClaseTiquete.ECONOMICA:
        flights = flights.filter(cupos_disponibles_economica__gte=people)
    elif travel_class == ClaseTiquete.PRIMERA_CLASE:
        flights = flights.filter(cupos_disponibles_primera__gte=people)
    else:
        flights = flights.filter(
            Q(cupos_disponibles_economica__gte=people) | Q(cupos_disponibles_primera__gte=people)
        )
    if "origin_id" in params:
        flights = flights.filter(ruta__origen_id=params["origin_id"])
    if "destination_id" in params:
        flights = flights.filter(ruta__destino_id=params["destination_id"])
    column = "ruta__origen_id" if params["side"] == "origin" else "ruta__destino_id"
    cities = (
        Ciudad.objects.filter(
            pk__in=flights.values(column),
            activa=True,
            locality__active=True,
            locality__country__active=True,
        )
        .filter(Q(locality__subdivision__isnull=True) | Q(locality__subdivision__active=True))
        .select_related("locality__country", "locality__subdivision")
    )
    if "selected_id" in params:
        cities = cities.filter(pk=params["selected_id"])
    # Airline coverage is small. Python folding matches Spanish accents without requiring
    # an unaccent extension or altering the worldwide catalogue's search contract.
    tokens = normalized(params.get("q", "")).split()
    return [
        city
        for city in cities
        if all(
            token in normalized(f"{city.nombre} {city.locality.search_text}") for token in tokens
        )
    ]


class FlightCityOptionsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[FlightCityQuery], responses=FlightCityPageSerializer)
    def get(self, request):
        query = FlightCityQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(available_city_options(query.validated_data), request)
        return paginator.get_paginated_response(FlightCityOptionSerializer(page, many=True).data)
