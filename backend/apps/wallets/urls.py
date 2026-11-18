from django.urls import path

from .views import WalletDepositView, WalletDetailView

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("deposit/", WalletDepositView.as_view(), name="wallet-deposit"),
]
