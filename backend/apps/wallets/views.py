from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Wallet
from .serializers import DepositarSerializer, WalletSerializer
from .services import depositar


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: WalletSerializer})
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response(WalletSerializer(wallet).data)


class WalletDepositView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DepositarSerializer, responses={200: WalletSerializer})
    def post(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = DepositarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        depositar(
            wallet_id=wallet.pk,
            monto=serializer.validated_data["monto"],
            referencia=serializer.validated_data.get("referencia", "Depósito"),
        )
        wallet.refresh_from_db()
        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)
