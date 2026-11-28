from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.limits import request_origin
from apps.users.permissions import IsAdministrator

from .errors import DuplicateRoute, FlightNotFound
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
    RutaUpdateSerializer,
    VueloDetalleSerializer,
    VueloListSerializer,
)
from .services import cancelar_vuelo, crear_ruta, editar_vuelo, programar_vuelo


class CitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CiudadSerializer(many=True)})
    def get(self, request):
        todos = request.query_params.get("todos") == "1"
        queryset = Ciudad.objects.all().order_by("nombre")
        if not (
            todos
            and request.user.is_authenticated
            and request.user.role in ("ADMINISTRADOR", "ROOT")
        ):
            queryset = queryset.filter(activa=True)
        return Response(CiudadSerializer(queryset, many=True).data)


class RoutesView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdministrator()]
        return [AllowAny()]

    @extend_schema(responses={200: RutaSerializer(many=True)})
    def get(self, request):
        todos = request.query_params.get("todos") == "1"
        queryset = (
            Ruta.objects.all()
            .select_related("origen", "destino")
            .order_by("origen__nombre", "destino__nombre")
        )
        if not (
            todos
            and request.user.is_authenticated
            and request.user.role in ("ADMINISTRADOR", "ROOT")
        ):
            queryset = queryset.filter(activa=True)
        return Response(RutaSerializer(queryset, many=True).data)

    @extend_schema(request=CrearRutaSerializer, responses={201: RutaSerializer})
    def post(self, request):
        serializer = CrearRutaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        origen_id = serializer.validated_data["origen_id"]
        destino_id = serializer.validated_data["destino_id"]
        tipo_vuelo = serializer.validated_data["tipo_vuelo"]
        duracion_min = serializer.validated_data["duracion_min"]
        activa = serializer.validated_data.get("activa", True)

        try:
            ruta = crear_ruta(
                origen_id=origen_id,
                destino_id=destino_id,
                tipo_vuelo=tipo_vuelo,
                duracion_min=duracion_min,
            )
            if not activa:
                ruta.activa = False
                ruta.save(update_fields=["activa"])
            return Response(RutaSerializer(ruta).data, status=status.HTTP_201_CREATED)
        except DuplicateRoute:
            ruta = Ruta.objects.get(origen_id=origen_id, destino_id=destino_id)
            ruta.tipo_vuelo = tipo_vuelo
            ruta.duracion_min = duracion_min
            ruta.activa = activa
            ruta.save()
            return Response(RutaSerializer(ruta).data, status=status.HTTP_200_OK)


class RouteDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(request=RutaUpdateSerializer, responses={200: RutaSerializer})
    def patch(self, request, pk):
        try:
            ruta = Ruta.objects.select_related("origen", "destino").get(pk=pk)
        except Ruta.DoesNotExist:
            return Response(
                {"code": "route_not_found", "message": "Ruta no encontrada en el catálogo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RutaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(ruta, field, value)
        ruta.save()
        return Response(RutaSerializer(ruta).data, status=status.HTTP_200_OK)


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
        if not (request.user.is_authenticated and request.user.role == "ADMINISTRADOR"):
            queryset = queryset.filter(
                estado=EstadoVuelo.PROGRAMADO,
                salida_utc__gt=timezone.now(),
                ruta__activa=True,
                ruta__origen__activa=True,
                ruta__destino__activa=True,
            ).filter(Q(cupos_disponibles_economica__gt=0) | Q(cupos_disponibles_primera__gt=0))
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
            motivo=serializer.validated_data["motivo"],
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
            ruta__activa=True,
            ruta__origen__activa=True,
            ruta__destino__activa=True,
        ).select_related("ruta__origen", "ruta__destino")

        pasajeros = data.get("pasajeros", 1)
        clase = data.get("clase", "")
        tipo_vuelo = data.get("tipo_vuelo", "")
        precio_min = data.get("precio_min")
        precio_max = data.get("precio_max")
        orden = data.get("orden", "salida_asc")

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

            elif clase == "ECONOMICA":
                qs = qs.filter(cupos_disponibles_economica__gte=pasajeros)

            else:
                qs = qs.filter(
                    Q(cupos_disponibles_economica__gte=pasajeros)
                    | Q(cupos_disponibles_primera__gte=pasajeros)
                )

            from apps.sales.services import resolver_precio_vigente

            from decimal import Decimal

            applicable = []
            for flight in qs:
                candidates = []
                if clase:
                    candidates = [clase]
                else:
                    candidates = [
                        c
                        for c in ("ECONOMICA", "PRIMERA_CLASE")
                        if (
                            flight.cupos_disponibles_primera
                            if c == "PRIMERA_CLASE"
                            else flight.cupos_disponibles_economica
                        ) >= pasajeros
                    ]

                eligible = []
                for candidate in candidates:
                    capacity = (
                        flight.cupos_disponibles_primera
                        if candidate == "PRIMERA_CLASE"
                        else flight.cupos_disponibles_economica
                    )
                    if capacity < pasajeros:
                        continue
                    fare = resolver_precio_vigente(flight, candidate, now)
                    eligible.append((candidate, fare))

                if not eligible:
                    continue
                candidate, fare = min(
                    eligible,
                    key=lambda item: (item[1], item[0]),
                )
                if precio_min is not None and fare < precio_min:
                    continue
                if precio_max is not None and fare > precio_max:
                    continue
                applicable.append((flight, candidate, fare))

            reverse_price = orden == "precio_desc"
            reverse_time = orden == "salida_desc"
            if orden in ("precio_asc", "precio_desc"):
                applicable.sort(
                    key=lambda item: (item[0].salida_utc, item[0].pk)
                )
                applicable.sort(
                    key=lambda item: item[2],
                    reverse=reverse_price,
                )
            else:
                applicable.sort(
                    key=lambda item: (
                        item[0].salida_utc,
                        item[2],
                        item[0].pk,
                    ),
                    reverse=reverse_time,
                )
            return [item[0] for item in applicable]

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
            selected_outbound_id = data.get("selected_outbound_id")
            if selected_outbound_id:
                outbound = Vuelo.objects.filter(pk=selected_outbound_id).first()
                if outbound:
                    vuelos_regreso = [
                        flight
                        for flight in vuelos_regreso
                        if flight.salida_utc > outbound.llegada_utc
                    ]

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
                "vuelos_ida": VueloListSerializer(
                    vuelos_ida,
                    many=True,
                    context={"clase": clase, "pasajeros": pasajeros, "now": now},
                ).data,
                "vuelos_regreso": (
                    VueloListSerializer(
                        vuelos_regreso,
                        many=True,
                        context={"clase": clase, "pasajeros": pasajeros, "now": now},
                    ).data
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


class CatalogueCitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CiudadSerializer(many=True)})
    def get(self, request):
        origins = Vuelo.objects.filter(
            estado=EstadoVuelo.PROGRAMADO, salida_utc__gt=timezone.now()
        ).values("ruta__origen_id")
        cities = Ciudad.objects.filter(activa=True, pk__in=origins).order_by("nombre")
        return Response(CiudadSerializer(cities, many=True).data)


class FlightCatalogueView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("origen_id", int, required=True)],
        responses={200: VueloListSerializer(many=True)},
    )
    def get(self, request):
        try:
            origin = int(request.query_params.get("origen_id", ""))
            if origin < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError({"origen_id": "Indica una ciudad válida."}) from None
        flights = (
            Vuelo.objects.filter(
                ruta__origen_id=origin,
                estado=EstadoVuelo.PROGRAMADO,
                salida_utc__gt=timezone.now(),
                ruta__activa=True,
                ruta__origen__activa=True,
                ruta__destino__activa=True,
            )
            .filter(Q(cupos_disponibles_economica__gt=0) | Q(cupos_disponibles_primera__gt=0))
            .select_related("ruta__origen", "ruta__destino")
            .order_by("salida_utc", "pk")
        )
        return Response(VueloListSerializer(flights, many=True).data)
