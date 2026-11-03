from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.limits import request_origin
from apps.users.permissions import IsAdminOrRoot

from .errors import FlightNotFound
from .models import Ciudad, Ruta, Vuelo
from .serializers import (
    CancelarVueloSerializer,
    CiudadSerializer,
    EditarVueloSerializer,
    ProgramarVueloSerializer,
    RutaSerializer,
    RutaUpdateSerializer,
    RutaWriteSerializer,
    VueloDetalleSerializer,
    VueloListSerializer,
)
from .services import cancelar_vuelo, editar_vuelo, programar_vuelo


class CitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CiudadSerializer(many=True)})
    def get(self, request):
        todos = request.query_params.get("todos") == "1"
        queryset = Ciudad.objects.all().order_by("nombre")
        if not (todos and request.user.is_authenticated and request.user.role in ("ADMINISTRADOR", "ROOT")):
            queryset = queryset.filter(activa=True)
        return Response(CiudadSerializer(queryset, many=True).data)


class RoutesView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrRoot()]
        return [AllowAny()]

    @extend_schema(responses={200: RutaSerializer(many=True)})
    def get(self, request):
        todos = request.query_params.get("todos") == "1"
        queryset = (
            Ruta.objects.all()
            .select_related("origen", "destino")
            .order_by("origen__nombre", "destino__nombre")
        )
        if not (todos and request.user.is_authenticated and request.user.role in ("ADMINISTRADOR", "ROOT")):
            queryset = queryset.filter(activa=True)
        return Response(RutaSerializer(queryset, many=True).data)

    @extend_schema(request=RutaWriteSerializer, responses={201: RutaSerializer})
    def post(self, request):
        serializer = RutaWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        origen_id = serializer.validated_data["origen_id"]
        destino_id = serializer.validated_data["destino_id"]

        try:
            origen = Ciudad.objects.get(pk=origen_id)
            destino = Ciudad.objects.get(pk=destino_id)
        except Ciudad.DoesNotExist:
            return Response(
                {"code": "city_not_found", "message": "Ciudad de origen o destino no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ruta, created = Ruta.objects.update_or_create(
            origen=origen,
            destino=destino,
            defaults={
                "tipo_vuelo": serializer.validated_data["tipo_vuelo"],
                "duracion_min": serializer.validated_data["duracion_min"],
                "activa": serializer.validated_data.get("activa", True),
            },
        )
        return Response(
            RutaSerializer(ruta).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RouteDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrRoot]

    @extend_schema(request=RutaUpdateSerializer, responses={200: RutaSerializer})
    def patch(self, request, pk):
        try:
            ruta = Ruta.objects.select_related("origen", "destino").get(pk=pk)
        except Ruta.DoesNotExist:
            return Response(
                {"code": "route_not_found", "message": "Ruta no encontrada en el catálogo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if "activa" in request.data:
            ruta.activa = bool(request.data["activa"])
        if "duracion_min" in request.data:
            try:
                duracion = int(request.data["duracion_min"])
                if duracion <= 0:
                    return Response(
                        {"code": "invalid_duration", "message": "La duración debe ser mayor a 0 minutos."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                ruta.duracion_min = duracion
            except (ValueError, TypeError):
                return Response(
                    {"code": "invalid_duration", "message": "La duración debe ser un número entero válido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        ruta.save()
        return Response(RutaSerializer(ruta).data, status=status.HTTP_200_OK)


class FlightsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrRoot()]
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
            return [IsAuthenticated(), IsAdminOrRoot()]
        return [AllowAny()]

    @extend_schema(responses={200: VueloDetalleSerializer})
    def get(self, request, pk):
        try:
            vuelo = (
                Vuelo.objects.select_related("ruta__origen", "ruta__destino", "creado_por")
                .prefetch_related("sillas", "noticias")
                .get(pk=pk)
            )
        except Vuelo.DoesNotExist:
            raise FlightNotFound() from None
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
    permission_classes = [IsAuthenticated, IsAdminOrRoot]

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
