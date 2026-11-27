from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flights.models import Silla
from apps.flights.serializers import SillaSerializer
from apps.users.permissions import HasVerifiedEmail, IsClient

from .idempotency import execute
from .models import Compra, HistorialBusqueda, Reserva
from .serializers import (
    CambiarSillaSerializer,
    CompraDetailSerializer,
    ComprarTiquetesSerializer,
    CrearReservaSerializer,
    HistorialBusquedaSerializer,
    ReservaDetailSerializer,
    TiqueteSerializer,
)
from .services import (
    cambiar_silla_tiquete,
    cancelar_compra,
    cancelar_reserva,
    comprar_tiquetes,
    crear_reserva,
    liberar_reserva_si_vencida,
)

IDEMPOTENCY_HEADER = OpenApiParameter(
    "Idempotency-Key",
    str,
    OpenApiParameter.HEADER,
    required=True,
    description=(
        "Stable per-action key; repeat with exactly the same payload after network failure."
    ),
)


class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses={200: ReservaDetailSerializer(many=True)})
    def get(self, request):
        reservas = (
            Reserva.objects.filter(cliente=request.user)
            .select_related(
                "vuelo__ruta__origen",
                "vuelo__ruta__destino",
                "vuelo_regreso__ruta__origen",
                "vuelo_regreso__ruta__destino",
            )
            .prefetch_related("viajeros_reserva__viajero")
            .order_by("-creada_en")
        )
        for r in reservas:
            liberar_reserva_si_vencida(r)
        reservas = reservas.all()
        return Response(ReservaDetailSerializer(reservas, many=True).data)

    @extend_schema(
        parameters=[IDEMPOTENCY_HEADER],
        request=CrearReservaSerializer,
        responses={201: ReservaDetailSerializer},
    )
    def post(self, request):
        serializer = CrearReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def perform():
            reserva = crear_reserva(
                cliente=request.user,
                **{
                    **{k: v for k, v in serializer.validated_data.items() if k != "viajeros"},
                    "viajeros_data": serializer.validated_data["viajeros"],
                },
            )
            return ReservaDetailSerializer(reserva).data

        return Response(
            execute(
                request.user,
                "reserve",
                request.headers.get("Idempotency-Key"),
                serializer.validated_data,
                perform,
            ),
            status=201,
        )


class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses={200: ReservaDetailSerializer})
    def get(self, request, pk):
        reserva = (
            Reserva.objects.select_related(
                "vuelo__ruta__origen",
                "vuelo__ruta__destino",
                "vuelo_regreso__ruta__origen",
                "vuelo_regreso__ruta__destino",
            )
            .prefetch_related("viajeros_reserva__viajero")
            .filter(pk=pk, cliente=request.user)
            .first()
        )
        if reserva is None:
            from rest_framework.exceptions import NotFound

            raise NotFound()
        liberar_reserva_si_vencida(reserva)
        reserva.refresh_from_db()
        return Response(ReservaDetailSerializer(reserva).data)


class ReservationCancelView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(request=None, responses={200: ReservaDetailSerializer})
    def post(self, request, pk):
        reserva = cancelar_reserva(reserva_id=pk, cliente=request.user)
        return Response(ReservaDetailSerializer(reserva).data, status=status.HTTP_200_OK)


class PurchaseListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses={200: CompraDetailSerializer(many=True)})
    def get(self, request):
        compras = (
            Compra.objects.filter(cliente=request.user)
            .prefetch_related(
                "tiquetes__vuelo__ruta__origen",
                "tiquetes__vuelo__ruta__destino",
                "tiquetes__viajero",
                "tiquetes__silla",
            )
            .order_by("-fecha_compra")
        )
        return Response(CompraDetailSerializer(compras, many=True).data)

    @extend_schema(
        parameters=[IDEMPOTENCY_HEADER],
        request=ComprarTiquetesSerializer,
        responses={201: CompraDetailSerializer},
    )
    def post(self, request):
        serializer = ComprarTiquetesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def perform():
            data = dict(serializer.validated_data)
            data["viajeros_data"] = data.pop("viajeros", None)
            compra = comprar_tiquetes(cliente=request.user, **data)
            return CompraDetailSerializer(compra).data

        return Response(
            execute(
                request.user,
                "purchase",
                request.headers.get("Idempotency-Key"),
                serializer.validated_data,
                perform,
            ),
            status=201,
        )


class PurchaseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses={200: CompraDetailSerializer})
    def get(self, request, pk):
        compra = (
            Compra.objects.prefetch_related(
                "tiquetes__vuelo__ruta__origen",
                "tiquetes__vuelo__ruta__destino",
                "tiquetes__viajero",
                "tiquetes__silla",
            )
            .filter(pk=pk, cliente=request.user)
            .first()
        )
        if compra is None:
            from rest_framework.exceptions import NotFound

            raise NotFound()
        return Response(CompraDetailSerializer(compra).data)


class PurchaseCancelView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(
        request=None,
        responses={
            200: CompraDetailSerializer,
            409: OpenApiResponse(
                description="Hay tiquetes pendientes de resolución por la aerolínea."
            ),
        },
    )
    def post(self, request, pk):
        compra = cancelar_compra(compra_id=pk, cliente=request.user)
        return Response(CompraDetailSerializer(compra).data, status=status.HTTP_200_OK)


class SeatMapView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: SillaSerializer(many=True)})
    def get(self, request, vuelo_id):
        sillas = Silla.objects.filter(vuelo_id=vuelo_id).order_by("numero_silla")
        return Response(SillaSerializer(sillas, many=True).data)


class TicketSeatChangeView(APIView):
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(request=CambiarSillaSerializer, responses={200: TiqueteSerializer})
    def post(self, request, pk):
        serializer = CambiarSillaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tiquete = cambiar_silla_tiquete(
            tiquete_id=pk,
            nueva_silla_id=serializer.validated_data["nueva_silla_id"],
            actor=request.user,
        )
        return Response(TiqueteSerializer(tiquete).data, status=status.HTTP_200_OK)


class SearchHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses={200: HistorialBusquedaSerializer(many=True)})
    def get(self, request):
        historial = HistorialBusqueda.objects.filter(usuario=request.user).order_by("-creado_en")[
            :20
        ]
        return Response(HistorialBusquedaSerializer(historial, many=True).data)
