from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import CanUseWallet

from .models import PaymentMethod, Wallet
from .payment_services import deposit_from_method, manage_method, register_method
from .serializers import (
    DepositarSerializer,
    DepositResultSerializer,
    MovementPageSerializer,
    MovimientoBilleteraSerializer,
    PaymentMethodCreateSerializer,
    PaymentMethodPageSerializer,
    PaymentMethodSerializer,
    PaymentMethodUpdateSerializer,
    WalletSerializer,
)


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated, CanUseWallet]

    @extend_schema(responses={200: WalletSerializer})
    def get(self, request):
        wallet = get_object_or_404(Wallet, user=request.user)
        return Response(WalletSerializer(wallet).data)


class WalletDepositView(APIView):
    permission_classes = [IsAuthenticated, CanUseWallet]

    @extend_schema(
        request=DepositarSerializer,
        responses={200: DepositResultSerializer},
        parameters=[
            OpenApiParameter("Idempotency-Key", str, OpenApiParameter.HEADER, required=True)
        ],
    )
    def post(self, request):
        serializer = DepositarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        wallet, movement = deposit_from_method(
            actor=request.user,
            method_id=data["medio_pago_id"],
            amount=data["monto"],
            key=request.headers.get("Idempotency-Key"),
            reference=data["referencia"],
        )
        result = WalletSerializer(wallet).data
        result["deposit"] = MovimientoBilleteraSerializer(movement).data
        return Response(result)


class PaymentMethodsView(APIView):
    permission_classes = [IsAuthenticated, CanUseWallet]

    @extend_schema(responses={200: PaymentMethodPageSerializer})
    def get(self, request):
        paginator = PageNumberPagination()
        methods = PaymentMethod.objects.filter(user=request.user)
        page = paginator.paginate_queryset(methods, request)
        return paginator.get_paginated_response(PaymentMethodSerializer(page, many=True).data)

    @extend_schema(request=PaymentMethodCreateSerializer, responses={201: PaymentMethodSerializer})
    def post(self, request):
        serializer = PaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method = register_method(actor=request.user, data=request.data)
        return Response(PaymentMethodSerializer(method).data, status=status.HTTP_201_CREATED)


class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated, CanUseWallet]

    @extend_schema(request=PaymentMethodUpdateSerializer, responses={200: PaymentMethodSerializer})
    def patch(self, request, pk):
        serializer = PaymentMethodUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method = manage_method(actor=request.user, method_id=pk, **serializer.validated_data)
        return Response(PaymentMethodSerializer(method).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        manage_method(actor=request.user, method_id=pk, deactivate=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WalletMovementsView(APIView):
    permission_classes = [IsAuthenticated, CanUseWallet]

    @extend_schema(responses={200: MovementPageSerializer})
    def get(self, request):
        wallet = get_object_or_404(Wallet, user=request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(
            wallet.movimientos.select_related("medio_pago").order_by("-creado_en", "-pk"), request
        )
        return paginator.get_paginated_response(MovimientoBilleteraSerializer(page, many=True).data)
