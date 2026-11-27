from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flights.models import ClaseTiquete, Promotion
from apps.flights.operations import create_promotion
from apps.flights.serializers import VueloDetalleSerializer
from apps.users.permissions import HasVerifiedEmail, IsAdministrator, IsClient

from .checkin import (
    authorized_tickets,
    boarding_pdf,
    confirm_checkin,
    guest_change_seat,
    request_link,
)
from .models import RelocationOffer, TipoTrayecto
from .serializers import TiqueteSerializer

CHECKIN_TOKEN = OpenApiParameter(
    "X-Checkin-Token",
    str,
    OpenApiParameter.HEADER,
    description="Traveler-scoped magic-link credential. Omit when using the buyer session.",
)


class GuestTicketSerializer(TiqueteSerializer):
    class Meta(TiqueteSerializer.Meta):
        fields = [field for field in TiqueteSerializer.Meta.fields if field != "precio_pagado"]


def access_serializer(request):
    return GuestTicketSerializer if guest_token(request) else TiqueteSerializer


class CheckinInput(serializers.Serializer):
    ticket_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=10
    )


class GuestLinkInput(serializers.Serializer):
    locator = serializers.CharField(min_length=6, max_length=6)
    document_type = serializers.CharField(max_length=20)
    document = serializers.CharField(max_length=30)
    email = serializers.EmailField()


class GuestSeatInput(serializers.Serializer):
    seat_id = serializers.IntegerField(min_value=1)


class PromotionInput(serializers.Serializer):
    clase = serializers.ChoiceField(choices=ClaseTiquete.choices)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class PromotionOutput(serializers.ModelSerializer):
    currency = serializers.CharField(default="COP", read_only=True)

    class Meta:
        model = Promotion
        fields = ["id", "vuelo", "clase", "price", "currency", "starts_at", "ends_at", "active"]


class OfferInput(serializers.Serializer):
    ticket_id = serializers.IntegerField(min_value=1)
    destination_id = serializers.IntegerField(min_value=1)


class DecisionInput(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["ACCEPT", "REFUND"])


class OfferOutput(serializers.ModelSerializer):
    class Meta:
        model = RelocationOffer
        fields = ["id", "ticket", "destination", "accepted_at", "resolved_at", "decision"]


def guest_token(request):
    # A dedicated credential, never accepted as a general user session.
    return request.headers.get("X-Checkin-Token")


@method_decorator(csrf_protect, name="dispatch")
class CheckinView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[CHECKIN_TOKEN], request=CheckinInput, responses=TiqueteSerializer(many=True)
    )
    def post(self, request):
        data = CheckinInput(data=request.data)
        data.is_valid(raise_exception=True)
        tickets = confirm_checkin(
            data.validated_data["ticket_ids"], request.user, guest_token(request)
        )
        return Response(access_serializer(request)(tickets, many=True).data)

    @extend_schema(parameters=[CHECKIN_TOKEN], responses=TiqueteSerializer(many=True))
    def get(self, request):
        tickets = (
            authorized_tickets(request.user, guest_token(request))
            .select_related("compra", "viajero", "silla", "vuelo__ruta")
            .order_by("pk")
        )
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(tickets, request)
        return paginator.get_paginated_response(access_serializer(request)(page, many=True).data)


@method_decorator(csrf_protect, name="dispatch")
class GuestLinkView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=GuestLinkInput, responses={202: None})
    def post(self, request):
        data = GuestLinkInput(data=request.data)
        data.is_valid(raise_exception=True)
        from apps.users.limits import consume_limit, request_origin

        consume_limit(scope="guest_origin", subject=request_origin(request), maximum=20)
        values = data.validated_data
        subject = "|".join(
            [
                values["document_type"].strip().upper(),
                values["document"].strip().upper(),
                values["email"].lower(),
            ]
        )
        consume_limit(scope="guest_traveler", subject=subject, maximum=5, interval=60)
        request_link(**values)
        return Response(
            {"message": "Si los datos corresponden a un tiquete habilitado, recibirás un enlace."},
            status=202,
        )


@method_decorator(csrf_protect, name="dispatch")
class GuestSeatView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[CHECKIN_TOKEN], request=GuestSeatInput, responses=TiqueteSerializer)
    def post(self, request, pk):
        data = GuestSeatInput(data=request.data)
        data.is_valid(raise_exception=True)
        from rest_framework.exceptions import PermissionDenied

        token = guest_token(request)
        if not token:
            raise PermissionDenied()
        ticket = guest_change_seat(pk, data.validated_data["seat_id"], token)
        return Response(GuestTicketSerializer(ticket).data)


class BoardingPassView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[CHECKIN_TOKEN], responses={(200, "application/pdf"): bytes})
    def get(self, request, pk):
        from rest_framework.exceptions import NotFound

        ticket = (
            authorized_tickets(request.user, guest_token(request))
            .select_related(
                "vuelo__ruta__origen", "vuelo__ruta__destino", "viajero", "compra", "silla"
            )
            .filter(pk=pk)
            .first()
        )
        if ticket is None:
            raise NotFound()
        response = HttpResponse(boarding_pdf(ticket), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="boarding-pass-{ticket.pk}.pdf"'
        response["Cache-Control"] = "private, no-store"
        return response


class PromotionsView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(request=PromotionInput, responses={201: PromotionOutput})
    def post(self, request, pk):
        data = PromotionInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            PromotionOutput(create_promotion(request.user, pk, **data.validated_data)).data,
            status=201,
        )


class RelocationOffersView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(
        operation_id="create_relocation_offer", request=OfferInput, responses={410: None}
    )
    def post(self, request):
        return Response(
            {
                "code": "workflow_retired",
                "message": "Cancela el vuelo; el comprador seleccionará la resolución.",
            },
            status=410,
        )


class RelocationDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(
        operation_id="resolve_relocation_offer", request=DecisionInput, responses={410: None}
    )
    def post(self, request, pk):
        return Response(
            {
                "code": "workflow_retired",
                "message": "Consulta la gestión de cancelaciones de tu cuenta.",
            },
            status=410,
        )

    @extend_schema(responses=OfferOutput)
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404

        offer = get_object_or_404(RelocationOffer, pk=pk, ticket__compra__cliente=request.user)
        return Response(OfferOutput(offer).data)


class QuoteInput(serializers.Serializer):
    vuelo_id = serializers.IntegerField(min_value=1, required=False)
    vuelo_regreso_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reserva_id = serializers.IntegerField(min_value=1, required=False)
    clase = serializers.ChoiceField(choices=ClaseTiquete.choices, default="ECONOMICA")
    tipo_trayecto = serializers.ChoiceField(choices=TipoTrayecto.choices, default="UNICO")
    passenger_count = serializers.IntegerField(min_value=1, max_value=5, default=1)

    def validate(self, attrs):
        if not attrs.get("vuelo_id") and not attrs.get("reserva_id"):
            raise serializers.ValidationError("Indica vuelo_id o reserva_id.")
        return attrs


class QuoteOutput(serializers.Serializer):
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
    prices = serializers.ListField(child=serializers.DecimalField(max_digits=12, decimal_places=2))
    quoted_at = serializers.DateTimeField()


class QuoteView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(request=QuoteInput, responses=QuoteOutput)
    def post(self, request):
        from .services import quote_purchase

        data = QuoteInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        count = values.pop("passenger_count")
        return Response(quote_purchase(request.user, viajeros_data=[{}] * count, **values))


class CompleteFlightView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(request=None, responses=VueloDetalleSerializer)
    def post(self, request, pk):
        from apps.flights.operations import complete_flight
        from apps.flights.serializers import VueloDetalleSerializer

        return Response(VueloDetalleSerializer(complete_flight(request.user, pk)).data)


class NewsOutput(serializers.Serializer):
    id = serializers.IntegerField()
    vuelo = serializers.IntegerField(source="vuelo_id")
    titulo = serializers.CharField()
    contenido = serializers.CharField()
    tipo = serializers.CharField()
    creada_en = serializers.DateTimeField()


class FlightNewsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=NewsOutput(many=True))
    def get(self, request):
        from django.utils import timezone
        from rest_framework.pagination import PageNumberPagination

        from apps.flights.models import NoticiaVuelo

        now = timezone.now()
        active_promotions = Promotion.objects.filter(
            active=True, starts_at__lte=now, ends_at__gt=now
        ).values_list("pk", flat=True)
        types = ["VUELO_PROGRAMADO", *[f"PROMOTION_{pk}" for pk in active_promotions]]
        news = NoticiaVuelo.objects.filter(
            vigente=True, vuelo__estado="PROGRAMADO", vuelo__salida_utc__gt=now, tipo__in=types
        ).order_by("-creada_en", "-pk")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(news, request)
        return paginator.get_paginated_response(NewsOutput(page, many=True).data)
