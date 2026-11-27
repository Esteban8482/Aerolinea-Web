from decimal import Decimal

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flights.models import Vuelo
from apps.flights.serializers import VueloListSerializer
from apps.users.permissions import HasVerifiedEmail, IsAdministrator, IsClient

from .cancellations import alternatives, resolve
from .models import CancellationResolution, EstadoReserva, EstadoTiquete, Reserva, Tiquete
from .serializers import TiqueteSerializer


class ResolutionOutput(serializers.ModelSerializer):
    locator = serializers.CharField(source="purchase.localizador")
    purchaser_id = serializers.IntegerField(source="purchase.cliente_id")
    flight = VueloListSerializer()
    destination = VueloListSerializer(allow_null=True)
    tickets = TiqueteSerializer(many=True)
    refunded_amount = serializers.SerializerMethodField()

    def get_refunded_amount(self, obj) -> str:
        return str(
            sum(
                (t.refund.valor for t in obj.tickets.select_related("refund") if t.refund_id),
                Decimal("0"),
            )
        )

    class Meta:
        model = CancellationResolution
        fields = [
            "id",
            "purchase_id",
            "purchaser_id",
            "locator",
            "flight",
            "status",
            "destination",
            "created_at",
            "resolved_at",
            "tickets",
            "refunded_amount",
        ]


class ResolutionDetailOutput(ResolutionOutput):
    alternatives = VueloListSerializer(many=True, read_only=True)

    class Meta(ResolutionOutput.Meta):
        fields = [*ResolutionOutput.Meta.fields, "alternatives"]


class ResolutionInput(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["RELOCATE", "REFUND"])
    destination_id = serializers.IntegerField(min_value=1, required=False)
    confirmed = serializers.BooleanField()

    def validate(self, attrs):
        if not attrs["confirmed"]:
            raise serializers.ValidationError("Confirma expresamente tu decisión.")
        if attrs["decision"] == "RELOCATE" and "destination_id" not in attrs:
            raise serializers.ValidationError({"destination_id": "Selecciona una alternativa."})
        return attrs


class ResolutionsView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses=ResolutionOutput(many=True))
    def get(self, request):
        rows = CancellationResolution.objects.filter(purchase__cliente=request.user).order_by("-pk")
        return Response(ResolutionOutput(rows, many=True).data)


class ResolutionView(APIView):
    permission_classes = [IsAuthenticated, IsClient, HasVerifiedEmail]

    @extend_schema(responses=ResolutionDetailOutput)
    def get(self, request, pk):
        row = get_object_or_404(CancellationResolution, pk=pk, purchase__cliente=request.user)
        data = ResolutionOutput(row).data
        data["alternatives"] = VueloListSerializer(alternatives(row), many=True).data
        return Response(data)

    @extend_schema(request=ResolutionInput, responses=ResolutionOutput)
    def post(self, request, pk):
        data = ResolutionInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        values.pop("confirmed")
        return Response(ResolutionOutput(resolve(request.user, pk, **values)).data)


class CancellationPanelOutput(serializers.Serializer):
    passengers = serializers.IntegerField()
    purchases = serializers.IntegerField()
    reservations = serializers.IntegerField()
    summary = serializers.DictField(child=serializers.IntegerField())
    resolutions = ResolutionOutput(many=True)


class CancellationPanelView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]

    @extend_schema(responses=CancellationPanelOutput)
    def get(self, request, pk):
        from django.db.models import Q

        flight = get_object_or_404(Vuelo, pk=pk)
        tickets = Tiquete.objects.filter(vuelo=flight, estado=EstadoTiquete.ACTIVO)
        rows = list(CancellationResolution.objects.filter(flight=flight))
        summary = {
            state: sum(r.tickets.count() for r in rows if r.status == state)
            for state in CancellationResolution.Status.values
        }
        return Response(
            {
                "passengers": sum(summary.values()) if rows else tickets.count(),
                "purchases": len(rows) if rows else tickets.values("compra_id").distinct().count(),
                "reservations": Reserva.objects.filter(
                    Q(vuelo=flight) | Q(vuelo_regreso=flight), estado=EstadoReserva.VIGENTE
                ).count(),
                "summary": summary,
                "resolutions": ResolutionOutput(rows, many=True).data,
            }
        )
