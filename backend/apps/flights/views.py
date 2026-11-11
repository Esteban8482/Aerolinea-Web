from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.limits import request_origin
from apps.users.permissions import IsAdministrator

from .errors import FlightNotFound
from .models import Ciudad, EstadoVuelo, Ruta, Vuelo
from .serializers import (
    CancelarVueloSerializer,
    CiudadSerializer,
    CrearRutaSerializer,
    EditarVueloSerializer,
    FlightSearchRequestSerializer,
    FlightSearchResultSerializer,
    ProgramarVueloSerializer,
    RutaSerializer,
    VueloDetalleSerializer,
    VueloListSerializer,
)
from .services import cancelar_vuelo, crear_ruta, editar_vuelo, programar_vuelo


class CitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CiudadSerializer(many=True)})
    def get(self, request):
        ciudades = Ciudad.objects.filter(activa=True).order_by("nombre")
        return Response(CiudadSerializer(ciudades, many=True).data)


class RoutesView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdministrator()]
        return [AllowAny()]

    @extend_schema(responses={200: RutaSerializer(many=True)})
    def get(self, request):
        rutas = (
            Ruta.objects.filter(activa=True)
            .select_related("origen", "destino")
            .order_by("origen__nombre", "destino__nombre")
        )
        return Response(RutaSerializer(rutas, many=True).data)

    @extend_schema(request=CrearRutaSerializer, responses={201: RutaSerializer})
    def post(self, request):
        serializer = CrearRutaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ruta = crear_ruta(**serializer.validated_data)
        return Response(RutaSerializer(ruta).data, status=status.HTTP_201_CREATED)


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


class FlightSearchView(APIView):
    permission_classes = [AllowAny]

    def _execute_search(self, request, params):
        serializer = FlightSearchRequestSerializer(data=params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        now = timezone.now()
        base_qs = Vuelo.objects.filter(
            estado=EstadoVuelo.PROGRAMADO,
            salida_utc__gt=now,
        ).select_related("ruta__origen", "ruta__destino")

        pasajeros = data.get("pasajeros", 1)
        clase = data.get("clase", "")
        tipo_vuelo = data.get("tipo_vuelo", "")
        precio_max = data.get("precio_max")

        def filtrar_qs(qs, orig_id, orig_str, dest_id, dest_str, f_salida):
            if orig_id:
                qs = qs.filter(ruta__origen_id=orig_id)
            elif orig_str:
                qs = qs.filter(ruta__origen__nombre__icontains=orig_str)

            if dest_id:
                qs = qs.filter(ruta__destino_id=dest_id)
            elif dest_str:
                qs = qs.filter(ruta__destino__nombre__icontains=dest_str)

            if f_salida:
                qs = qs.filter(fecha_salida=f_salida)

            if tipo_vuelo:
                qs = qs.filter(tipo_vuelo=tipo_vuelo)

            if clase == "PRIMERA_CLASE":
                qs = qs.filter(cupos_disponibles_primera__gte=pasajeros)
                if precio_max:
                    qs = qs.filter(costo_persona_primera__lte=precio_max)
            elif clase == "ECONOMICA":
                qs = qs.filter(cupos_disponibles_economica__gte=pasajeros)
                if precio_max:
                    qs = qs.filter(costo_persona_economica__lte=precio_max)
            else:
                qs = qs.filter(
                    Q(cupos_disponibles_economica__gte=pasajeros)
                    | Q(cupos_disponibles_primera__gte=pasajeros)
                )
                if precio_max:
                    qs = qs.filter(
                        Q(costo_persona_economica__lte=precio_max)
                        | Q(costo_persona_primera__lte=precio_max)
                    )
            return qs.order_by("salida_utc")

        vuelos_ida = filtrar_qs(
            base_qs,
            orig_id=data.get("origen_id"),
            orig_str=data.get("origen"),
            dest_id=data.get("destino_id"),
            dest_str=data.get("destino"),
            f_salida=data.get("fecha_salida"),
        )

        vuelos_regreso = []
        tipo_trayecto = data.get("tipo_trayecto", "UNICO")
        if tipo_trayecto == "COMPLETO":
            vuelos_regreso = filtrar_qs(
                base_qs,
                orig_id=data.get("destino_id"),
                orig_str=data.get("destino"),
                dest_id=data.get("origen_id"),
                dest_str=data.get("origen"),
                f_salida=data.get("fecha_regreso"),
            )

        # Historial de búsqueda si autenticado (RF-BSQ-09)
        if request.user.is_authenticated:
            try:
                from apps.sales.models import HistorialBusqueda

                HistorialBusqueda.objects.create(
                    usuario=request.user,
                    origen=str(data.get("origen") or data.get("origen_id") or ""),
                    destino=str(data.get("destino") or data.get("destino_id") or ""),
                    tipo_trayecto=tipo_trayecto,
                    fecha_salida=data.get("fecha_salida"),
                    fecha_regreso=data.get("fecha_regreso"),
                    pasajeros=pasajeros,
                    clase=clase,
                )
            except Exception:
                pass

        return Response(
            {
                "tipo_trayecto": tipo_trayecto,
                "pasajeros": pasajeros,
                "clase": clase,
                "vuelos_ida": VueloListSerializer(vuelos_ida, many=True).data,
                "vuelos_regreso": (
                    VueloListSerializer(vuelos_regreso, many=True).data
                    if tipo_trayecto == "COMPLETO"
                    else []
                ),
            }
        )

    @extend_schema(
        request=FlightSearchRequestSerializer,
        responses={200: FlightSearchResultSerializer},
    )
    def post(self, request):
        return self._execute_search(request, request.data)

    @extend_schema(responses={200: FlightSearchResultSerializer})
    def get(self, request):
        return self._execute_search(request, request.query_params)

