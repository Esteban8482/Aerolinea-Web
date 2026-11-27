from django.urls import path

from .views import (
    PaymentMethodDetailView,
    PaymentMethodsView,
    WalletDepositView,
    WalletDetailView,
    WalletMovementsView,
)

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("deposit/", WalletDepositView.as_view(), name="wallet-deposit"),
    path("payment-methods/", PaymentMethodsView.as_view(), name="payment-methods"),
    path(
        "payment-methods/<int:pk>/", PaymentMethodDetailView.as_view(), name="payment-method-detail"
    ),
    path("movements/", WalletMovementsView.as_view(), name="wallet-movements"),
]
