from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections, connections
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.reference.models import Country, Locality, Subdivision
from apps.users.models import User
from apps.wallets.models import MovimientoBilletera, PaymentMethod, Wallet
from apps.wallets.payment_services import (
    MAX_BALANCE,
    deposit_from_method,
    manage_method,
    register_method,
)
from apps.wallets.services import debitar_para_compra

URL = "/api/v1/sales/wallet/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    user = User.objects.create_user(
        email="funding@example.invalid",
        role="CLIENTE",
        is_email_verified=True,
        username="funding",
        first_name="Synthetic",
        last_name="Owner",
        document_number="000123",
        birth_date="1990-01-01",
        birth_place="Test",
        billing_address="Test",
        gender="F",
    )
    Wallet.objects.create(user=user)
    return user


@pytest.fixture
def card_data():
    country = Country.objects.create(
        id=170, code="CO", name="Colombia", search_text="colombia"
    )
    subdivision = Subdivision.objects.create(
        id=1, country=country, code="RAS", name="Risaralda", search_text="risaralda"
    )
    city = Locality.objects.create(
        id=1,
        country=country,
        subdivision=subdivision,
        name="Pereira",
        search_text="pereira",
    )
    return dict(
        tipo="TARJETA",
        numero="4111 1111 1111 1111",
        mes_vencimiento=12,
        anio_vencimiento=timezone.now().year + 1,
        titular="Synthetic Owner",
        cardholder_first_name="Synthetic",
        cardholder_last_name="Owner",
        billing_country_id=country.pk,
        billing_subdivision_id=subdivision.pk,
        billing_city_id=city.pk,
        billing_address="Calle sintética 123",
        postal_code="660001",
    )


@pytest.fixture
def method(owner, card_data):
    return register_method(actor=owner, data=card_data)


@pytest.fixture
def client(owner):
    client = APIClient()
    client.force_authenticate(owner)
    return client


def fund(owner, method, key="deposit-1", amount="1000.00"):
    return deposit_from_method(actor=owner, method_id=method.pk, amount=amount, key=key)


def test_private_storage_and_masked_api(owner, client, card_data):
    response = client.post(URL + "payment-methods/", card_data, format="json")
    assert response.status_code == 201, response.data
    method = PaymentMethod.objects.get()
    assert method.ultimos_cuatro == "1111"
    assert len(method.fingerprint) == 64
    assert "4111111111111111" not in str(method.__dict__)
    assert "numero" not in response.data and "fingerprint" not in response.data
    assert response.data["numero_enmascarado"] == "**** 1111"
    assert client.get(URL + "payment-methods/").data["count"] == 1
    duplicate = client.post(URL + "payment-methods/", card_data, format="json")
    assert duplicate.status_code == 400
    assert PaymentMethod.objects.count() == 1


@pytest.mark.parametrize(
    "number",
    [
        "411111111111111",
        "41111111111111111",
        "4111A11111111111",
        "4242424242424242",
    ],
)
def test_card_rejects_invalid_lengths_characters_and_non_synthetic_pan(client, card_data, number):
    response = client.post(
        URL + "payment-methods/",
        {**card_data, "numero": number},
        format="json",
    )
    assert response.status_code == 400
    assert not PaymentMethod.objects.exists()


def test_mastercard_fixture_and_billing_location_are_accepted(owner, client, card_data):
    payload = {
        **card_data,
        "numero": "5555 5555 5555 4444",
        "cardholder_first_name": "Mariana",
        "cardholder_last_name": "Ríos",
        "titular": "Mariana Ríos",
    }
    response = client.post(URL + "payment-methods/", payload, format="json")
    assert response.status_code == 201, response.data
    assert response.data["marca"] == "MASTERCARD"
    assert response.data["numero_enmascarado"] == "**** 4444"
    method = PaymentMethod.objects.get()
    assert method.billing_city_id == card_data["billing_city_id"]
    assert method.postal_code == "660001"
    assert "5555555555554444" not in str(method.__dict__)


def test_card_billing_location_must_be_consistent(client, card_data):
    other_country = Country.objects.create(
        id=724, code="ES", name="España", search_text="españa"
    )
    response = client.post(
        URL + "payment-methods/",
        {**card_data, "billing_country_id": other_country.pk},
        format="json",
    )
    assert response.status_code == 400
    assert "billing_city_id" in response.data["details"]
    assert not PaymentMethod.objects.exists()


def test_bank_deposit_and_history(owner, client):
    result = client.post(
        URL + "payment-methods/",
        dict(
            tipo="CUENTA_BANCARIA",
            alias="Bank",
            titular="Test",
            entidad="Simulated bank",
            numero="0000123456789",
        ),
        format="json",
    )
    assert result.status_code == 201
    payload = {"medio_pago_id": result.data["id"], "monto": "2500.00"}
    response = client.post(URL + "deposit/", payload, format="json", HTTP_IDEMPOTENCY_KEY="bank")
    assert response.status_code == 200, response.data
    assert response.data["balance"] == "2500.00" and response.data["currency"] == "COP"
    movement = MovimientoBilletera.objects.get()
    assert movement.medio_pago_id == result.data["id"]
    assert movement.tipo == "DEPOSITO" and movement.saldo_resultante == Decimal("2500")
    assert client.get(URL + "movements/").data["count"] == 1
    assert client.get(URL).data["balance"] == "2500.00"


@pytest.mark.parametrize(
    "change",
    [
        dict(cvv="123"),
        dict(numero="not-a-number"),
        dict(numero="1234"),
        dict(mes_vencimiento=13),
        dict(anio_vencimiento=2000),
        dict(tipo="CUENTA_BANCARIA"),
        dict(titular=""),
        dict(is_active=True),
    ],
)
def test_invalid_instrument_is_atomic(client, card_data, change):
    response = client.post(URL + "payment-methods/", {**card_data, **change}, format="json")
    assert response.status_code == 400
    assert not PaymentMethod.objects.exists()


@pytest.mark.parametrize(
    "amount", ["0", "-1", "NaN", "Infinity", "1000.001", "999.99", "1000000000000"]
)
def test_invalid_deposits_leave_balance_and_history_unchanged(client, method, amount):
    response = client.post(
        URL + "deposit/",
        {"medio_pago_id": method.pk, "monto": amount},
        format="json",
        HTTP_IDEMPOTENCY_KEY="invalid",
    )
    assert response.status_code == 400
    assert not MovimientoBilletera.objects.exists()
    assert Wallet.objects.get().balance == 0


def test_deposit_requires_method_key_and_valid_ownership(owner, client, method):
    assert client.post(URL + "deposit/", {"monto": "1000.00"}, format="json").status_code == 400
    assert (
        client.post(
            URL + "deposit/", {"monto": "1000.00", "medio_pago_id": method.pk}, format="json"
        ).status_code
        == 400
    )
    other = User.objects.create(
        email="other@example.invalid", role="CLIENTE", is_email_verified=True
    )
    Wallet.objects.create(user=other)
    client.force_authenticate(other)
    assert (
        client.post(
            URL + "deposit/",
            {"monto": "1000.00", "medio_pago_id": method.pk},
            format="json",
            HTTP_IDEMPOTENCY_KEY="foreign",
        ).status_code
        == 404
    )
    assert client.delete(URL + f"payment-methods/{method.pk}/").status_code == 404
    assert (
        client.patch(
            URL + f"payment-methods/{method.pk}/", {"alias": "hijacked"}, format="json"
        ).status_code
        == 404
    )
    assert client.get(URL + "payment-methods/").data["count"] == 0
    assert not MovimientoBilletera.objects.exists()


def test_request_replay_and_changed_payload(owner, method):
    _, first = fund(owner, method)
    _, repeated = fund(owner, method, amount="1000")
    assert repeated.pk == first.pk
    with pytest.raises(ValidationError):
        fund(owner, method, amount="2000")
    assert Wallet.objects.get().balance == 1000 and MovimientoBilletera.objects.count() == 1
    fund(owner, method, key="second")
    assert Wallet.objects.get().balance == 2000


def test_management_preserves_history_and_replay(owner, client, method):
    _, movement = fund(owner, method)
    assert (
        client.patch(
            URL + f"payment-methods/{method.pk}/", {"alias": "Renamed"}, format="json"
        ).status_code
        == 200
    )
    for _ in range(2):
        assert client.delete(URL + f"payment-methods/{method.pk}/").status_code == 204
    movement.refresh_from_db()
    assert movement.medio_pago_id == method.pk and not movement.medio_pago.activo
    assert fund(owner, method)[1].pk == movement.pk
    with pytest.raises(ValidationError):
        fund(owner, method, key="new")


def test_expired_card_and_balance_overflow_rejected(owner, method):
    PaymentMethod.objects.filter(pk=method.pk).update(anio_vencimiento=2000)
    with pytest.raises(ValidationError):
        fund(owner, method)
    PaymentMethod.objects.filter(pk=method.pk).update(anio_vencimiento=9999)
    Wallet.objects.filter(user=owner).update(balance=MAX_BALANCE)
    with pytest.raises(ValidationError):
        fund(owner, method)
    assert not MovimientoBilletera.objects.exists()


def test_failed_movement_creation_rolls_back_balance(owner, method):
    with patch(
        "apps.wallets.services.MovimientoBilletera.objects.create", side_effect=IntegrityError
    ):
        with pytest.raises(IntegrityError):
            fund(owner, method)
    assert Wallet.objects.get().balance == 0
    assert not MovimientoBilletera.objects.exists()


def test_unverified_or_inactive_cannot_fund_or_manage(owner, method):
    owner.is_email_verified = False
    for callback in [
        lambda: fund(owner, method),
        lambda: manage_method(actor=owner, method_id=method.pk, deactivate=True),
    ]:
        with pytest.raises(PermissionDenied):
            callback()


def test_session_mutations_require_csrf(owner):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner)
    assert client.post(URL + "deposit/", {}, format="json").status_code == 403
    assert client.post(URL + "payment-methods/", {}, format="json").status_code == 403


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_deposits_are_serialized(owner, method, same_key):
    barrier = Barrier(2)

    def run(i):
        close_old_connections()
        try:
            barrier.wait(timeout=15)
            return fund(owner, method, key="same" if same_key else str(i))[1].pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(run, range(2)))
    expected = 1 if same_key else 2
    assert len(set(ids)) == expected
    assert Wallet.objects.get().balance == expected * 1000
    assert MovimientoBilletera.objects.count() == expected


@pytest.mark.django_db(transaction=True)
def test_deposit_and_purchase_debit_do_not_lose_updates(owner, method):
    fund(owner, method, key="initial", amount="3000")
    barrier = Barrier(2)

    def run(deposit):
        close_old_connections()
        try:
            barrier.wait(timeout=15)
            if deposit:
                fund(owner, method, key="concurrent", amount="1000")
            else:
                debitar_para_compra(owner.wallet.pk, Decimal("2000"), "test debit")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, [True, False]))
    assert Wallet.objects.get().balance == 2000
    assert MovimientoBilletera.objects.count() == 3
