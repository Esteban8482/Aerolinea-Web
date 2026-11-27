"""Cumulative HTTP journeys across authentication, funding, flights and sales."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.flights.models import Ciudad, Vuelo
from apps.flights.services import programar_vuelo
from apps.sales.journey_mail import process_journey_emails
from apps.sales.mail import process_purchase_emails
from apps.sales.models import Compra, JourneyNotification, Tiquete
from apps.users.mail import process_verification_emails
from apps.users.models import EmailVerification, User
from apps.users.services import verification_token
from apps.users.tests.test_registration import PASSWORD
from apps.users.tests.test_registration import data as data
from apps.users.tests.test_registration import registration_settings as registration_settings
from apps.wallets.models import MovimientoBilletera, Wallet

pytestmark = pytest.mark.django_db
BASE = "/api/v1/"


def csrf(client):
    client.credentials(HTTP_X_CSRFTOKEN=client.get(BASE + "auth/csrf/").data["csrf_token"])


def traveler(document="000123"):
    return dict(
        documento=document,
        tipo_documento="CC",
        nombres="Synthetic",
        apellidos="Traveler",
        fecha_nacimiento="1990-01-01",
        genero="F",
        telefono="1234567",
        correo="traveler@example.invalid",
        nombre_contacto="Emergency",
        telefono_contacto="7654321",
    )


@pytest.mark.django_db(transaction=True)
def test_registered_customer_funds_reserves_buys_cancels_and_checks_in(
    data, catalogo, admin_user, settings
):
    client = APIClient(enforce_csrf_checks=True)
    csrf(client)
    assert client.post(BASE + "auth/register/", data, format="json").status_code == 201
    user = User.objects.get(email=data["email"].lower())
    assert Wallet.objects.get(user=user).balance == 0
    assert process_verification_emails() == (1, 0)
    assert (
        client.post(
            BASE + "auth/verify-email/",
            {"token": verification_token(EmailVerification.objects.get(user=user))},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.post(
            BASE + "auth/login/", {"email": user.email, "password": PASSWORD}, format="json"
        ).status_code
        == 200
    )
    csrf(client)  # Login rotates CSRF.
    method = client.post(
        BASE + "sales/wallet/payment-methods/",
        {
            "tipo": "CUENTA_BANCARIA",
            "numero": "000123456789",
            "alias": "Funding",
            "titular": "Synthetic Customer",
            "entidad": "Simulated Bank",
        },
        format="json",
    )
    assert method.status_code == 201, method.data
    funding = client.post(
        BASE + "sales/wallet/deposit/",
        {"medio_pago_id": method.data["id"], "monto": "1000000.00"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="funding",
    )
    assert funding.status_code == 200, funding.data
    admin = APIClient()
    admin.force_authenticate(admin_user)
    origin, destination = Ciudad.objects.get(nombre="Bogotá"), Ciudad.objects.get(nombre="Pereira")
    flight = admin.post(
        BASE + "flights/",
        {
            "origen_id": origin.pk,
            "destino_id": destination.pk,
            "fecha_salida": str(date.today() + timedelta(days=3)),
            "hora_salida": "12:00:00",
            "costo_persona_economica": "150000.00",
            "costo_persona_primera": "220000.00",
        },
        format="json",
    )
    assert flight.status_code == 201, flight.data
    flight_id = flight.data["id"]
    assert (
        client.get(BASE + "flights/catalogue/", {"origen_id": origin.pk}).data[0]["id"] == flight_id
    )
    search = client.get(
        BASE + "flights/search/",
        {
            "origen_id": origin.pk,
            "destino_id": destination.pk,
            "fecha_salida": flight.data["fecha_salida"],
        },
    )
    assert search.status_code == 200 and search.data["vuelos_ida"][0]["id"] == flight_id
    reservation = client.post(
        BASE + "sales/reservations/",
        {"vuelo_id": flight_id, "viajeros": [traveler()]},
        format="json",
        HTTP_IDEMPOTENCY_KEY="reserve",
    )
    assert reservation.status_code == 201, reservation.data
    quote = client.post(
        BASE + "sales/quote/", {"reserva_id": reservation.data["id"]}, format="json"
    )
    assert quote.status_code == 200, quote.data
    payload = {"reserva_id": reservation.data["id"], "accepted_total": quote.data["total"]}
    purchase = client.post(
        BASE + "sales/purchases/", payload, format="json", HTTP_IDEMPOTENCY_KEY="convert"
    )
    assert purchase.status_code == 201, purchase.data
    replay = client.post(
        BASE + "sales/purchases/", payload, format="json", HTTP_IDEMPOTENCY_KEY="convert"
    )
    assert replay.data == purchase.data
    assert process_purchase_emails() == (1, 0)
    cancel = client.post(BASE + f"sales/purchases/{purchase.data['id']}/cancel/", {}, format="json")
    assert cancel.status_code == 200, cancel.data
    assert Wallet.objects.get(user=user).balance == Decimal("1000000")
    assert MovimientoBilletera.objects.filter(wallet__user=user).count() == 3
    # New direct purchase, using the same now-released seat inventory and original funds.
    direct = client.post(
        BASE + "sales/purchases/",
        {"vuelo_id": flight_id, "viajeros": [traveler()], "accepted_total": "150000.00"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="direct",
    )
    assert direct.status_code == 201, direct.data
    ticket = Tiquete.objects.get(compra_id=direct.data["id"])
    now = timezone.now()
    # An administrative reschedule opens the current check-in window.
    new_departure = now + timedelta(hours=12)
    from zoneinfo import ZoneInfo

    local = new_departure.astimezone(ZoneInfo("America/Bogota"))
    edit = admin.patch(
        BASE + f"flights/{flight_id}/",
        {
            "fecha_salida": str(local.date()),
            "hora_salida": local.time().isoformat(),
            "motivo": "Synthetic schedule update",
        },
        format="json",
    )
    assert edit.status_code == 200, edit.data
    checkin = client.post(BASE + "sales/check-in/", {"ticket_ids": [ticket.pk]}, format="json")
    assert checkin.status_code == 200, checkin.data
    pdf = client.get(BASE + f"sales/tickets/{ticket.pk}/boarding-pass/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    settings.GUEST_CHECKIN_FRONTEND_URL = "https://example.invalid/check-in"
    guest = APIClient(enforce_csrf_checks=True)
    csrf(guest)
    link = guest.post(
        BASE + "sales/check-in/access/",
        {
            "locator": direct.data["localizador"],
            "document_type": "CC",
            "document": "000123",
            "email": "traveler@example.invalid",
        },
        format="json",
    )
    assert link.status_code == 202
    token = (
        JourneyNotification.objects.get(guest_access__isnull=False)
        .body.split("#token=")[1]
        .split(".")[0]
    )
    guest.credentials(HTTP_X_CHECKIN_TOKEN=token)
    assert guest.get(BASE + "sales/check-in/").data["count"] == 1
    assert guest.get(BASE + f"sales/tickets/{ticket.pk}/boarding-pass/").status_code == 200
    sent, failed = process_journey_emails()
    assert sent >= 2 and failed == 0
    assert any(getattr(message, "attachments", []) for message in mail.outbox)
    csrf(client)
    assert client.post(BASE + "auth/logout/", {}, format="json").status_code == 200
    assert client.get(BASE + "sales/wallet/").status_code == 403
    assert Compra.objects.count() == 2


def test_catalogue_and_price_filter_respect_available_class(catalogo, admin_user):
    origin, destination = Ciudad.objects.get(nombre="Bogotá"), Ciudad.objects.get(nombre="Pereira")
    flight = programar_vuelo(
        origen_id=origin.pk,
        destino_id=destination.pk,
        fecha_salida=date.today() + timedelta(days=3),
        hora_salida=time(12),
        costo_persona_economica=Decimal("1000"),
        costo_persona_primera=Decimal("5000"),
        actor=admin_user,
    )
    Vuelo.objects.filter(pk=flight.pk).update(cupos_disponibles_economica=0)
    client = APIClient()
    # Economy is affordable but full; first class is available but too expensive.
    response = client.get(BASE + "flights/search/", {"origen_id": origin.pk, "precio_max": "2000"})
    assert response.status_code == 200 and response.data["vuelos_ida"] == []
    assert client.get(BASE + "flights/catalogue/cities/").data[0]["id"] == origin.pk
    assert client.get(BASE + "flights/catalogue/").status_code == 400
    Vuelo.objects.filter(pk=flight.pk).update(estado="CANCELADO")
    assert client.get(BASE + "flights/catalogue/", {"origen_id": origin.pk}).data == []
    assert client.get(BASE + "flights/catalogue/cities/").data == []
