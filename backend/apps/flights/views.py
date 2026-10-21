from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.limits import request_origin
from apps.users.permissions import IsAdministrator

from .models import Ciudad, Ruta, Vuelo
from .serializers import (
    CancelarVueloSerializer,
    CiudadSerializer,
    EditarVueloSerializer,
    ProgramarVueloSerializer,
    RutaSerializer,
    VueloDetalleSerializer,
    VueloListSerializer,
)
from .services import cancelar_vuelo, editar_vuelo, programar_vuelo


class CitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CiudadSerializer(many=True)})
    def get(self, request):
        ciudades = Ciudad.objects.filter(activa=True).order_by("nombre")
        return Response(CiudadSerializer(ciudades, many=True).data)


class RoutesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: RutaSerializer(many=True)})
    def get(self, request):
        rutas = (
            Ruta.objects.filter(activa=True)
            .select_related("origen", "destino")
            .order_by("origen__nombre", "destino__nombre")
        )
        return Response(RutaSerializer(rutas, many=True).data)


class FlightsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdministrator()]
        return [AllowAny()]

    @extend_schema(responses={200: VueloListSerializer(many=True)})
    def get(self, request):
        queryset = Vuelo.objects.select_related("ruta__origen", "ruta__destino").order_by(
            "-salida_utc"
        )
        estado = request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado.upper())
        tipo_vuelo = request.query_params.get("tipo_vuelo")
        if tipo_vuelo:
            queryset = queryset.filter(tipo_vuelo=tipo_vuelo.upper())
        origen = request.query_params.get("origen")
        if origen:
            queryset = queryset.filter(ruta__origen__nombre__icontains=origen)
        destino = request.query_params.get("destino")
        if destino:
            queryset = queryset.filter(ruta__destino__nombre__icontains=destino)
        return Response(VueloListSerializer(queryset, many=True).data)

    @extend_schema(request=ProgramarVueloSerializer, responses={201: VueloDetalleSerializer})
    def post(self, request):
        serializer = ProgramarVueloSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vuelo = programar_vuelo(
            origen_id=serializer.validated_data["origen_id"],
            destino_id=serializer.validated_data["destino_id"],
            fecha_salida=serializer.validated_data["fecha_salida"],
            hora_salida=serializer.validated_data["hora_salida"],
            costo_persona_economica=serializer.validated_data["costo_persona_economica"],
            costo_persona_primera=serializer.validated_data.get("costo_persona_primera"),
            actor=request.user,
            ip_origen=request_origin(request),
        )
        return Response(VueloDetalleSerializer(vuelo).data, status=status.HTTP_201_CREATED)


class FlightDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsAdministrator()]
        return [AllowAny()]

    @extend_schema(responses={200: VueloDetalleSerializer})
    def get(self, request, pk):
        vuelo = (
            Vuelo.objects.select_related("ruta__origen", "ruta__destino", "creado_por")
            .prefetch_related("sillas", "noticias")
            .get(pk=pk)
        )
        return Response(VueloDetalleSerializer(vuelo).data)

    @extend_schema(request=EditarVueloSerializer, responses={200: VueloDetalleSerializer})
    def patch(self, request, pk):
        serializer = EditarVueloSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vuelo = editar_vuelo(
            vuelo_id=pk,
            fecha_salida=serializer.validated_data.get("fecha_salida"),
            hora_salida=serializer.validated_data.get("hora_salida"),
            costo_persona_economica=serializer.validated_data.get("costo_persona_economica"),
            costo_persona_primera=serializer.validated_data.get("costo_persona_primera"),
            actor=request.user,
            ip_origen=request_origin(request),
        )
        return Response(VueloDetalleSerializer(vuelo).data, status=status.HTTP_200_OK)


class FlightCancelView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(request=CancelarVueloSerializer, responses={200: VueloDetalleSerializer})
    def post(self, request, pk):
        serializer = CancelarVueloSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vuelo = cancelar_vuelo(
            vuelo_id=pk,
            motivo=serializer.validated_data["motivo"],
            alternativa=serializer.validated_data.get("alternativa", "REINTEGRO"),
            actor=request.user,
            ip_origen=request_origin(request),
        )
        return Response(VueloDetalleSerializer(vuelo).data, status=status.HTTP_200_OK)
