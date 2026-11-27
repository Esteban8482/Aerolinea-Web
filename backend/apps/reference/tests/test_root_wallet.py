from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.users.models import User
from apps.wallets.models import Wallet
from apps.wallets.services import debitar_para_compra, depositar, reembolsar_a_billetera

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", ["ROOT", "ADMINISTRADOR"])
def test_non_client_cannot_access_any_wallet_endpoint_or_financial_service(role):
    root = User.objects.create_root(root_id="catalogue-root", password="test-password-long-2026")
    if role == "ADMINISTRADOR":
        root.role = role
        root.root_id = None
        root.email = "admin-wallet-test@example.invalid"
    root.is_email_verified = True
    root.is_staff = root.is_superuser = True
    root.save()
    wallet = Wallet.objects.create(user=root)
    client = APIClient()
    client.force_authenticate(root)
    base = "/api/v1/sales/wallet/"
    for method, path in [
        ("get", ""),
        ("get", "movements/"),
        ("get", "payment-methods/"),
        ("post", "deposit/"),
        ("post", "payment-methods/"),
        ("delete", "payment-methods/1/"),
    ]:
        assert getattr(client, method)(base + path).status_code == 403
    for service in (depositar, debitar_para_compra, reembolsar_a_billetera):
        with pytest.raises(PermissionDenied):
            service(wallet.pk, Decimal("1000"))
    wallet.refresh_from_db()
    assert wallet.balance == 0
