from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.flights.models import EstadoSilla, Silla, Vuelo
from apps.flights.operations import create_promotion, offer_relocation, resolve_relocation
from apps.flights.services import cancelar_vuelo, editar_vuelo, programar_vuelo
from apps.sales.checkin import authorized_tickets, boarding_pdf, confirm_checkin, request_link
from apps.sales.models import Compra, GuestAccess, JourneyNotification, Reserva, Tiquete
from apps.sales.services import (
    PriceChanged,
    cambiar_silla_tiquete,
    cancelar_compra,
    cancelar_reserva,
    comprar_tiquetes,
    crear_reserva,
    liberar_reserva_si_vencida,
    resolver_precio_vigente,
)
from apps.wallets.models import MovimientoBilletera

pytestmark = pytest.mark.django_db


@pytest.fixture
def passenger():
    return dict(
        documento="00042",
        tipo_documento="CC",
        nombres="Ana",
        apellidos="Prueba",
        fecha_nacimiento=date(1990, 1, 1),
        genero="F",
        telefono="1234567",
        correo="ana@example.invalid",
        nombre_contacto="Contacto",
        telefono_contacto="7654321",
    )


def buy(client, flight, passenger):
    return comprar_tiquetes(
        cliente=client,
        vuelo_id=flight.pk,
        viajeros_data=[passenger],
        accepted_total=flight.costo_persona_economica,
    )


def test_authorization(admin_user, cliente_con_billetera, vuelo_nacional, passenger):
    with pytest.raises(PermissionDenied):
        buy(admin_user, vuelo_nacional, passenger)
    cliente_con_billetera.is_email_verified = False
    with pytest.raises(PermissionDenied):
        buy(cliente_con_billetera, vuelo_nacional, passenger)


def test_price_rollback(cliente_con_billetera, vuelo_nacional, passenger):
    with pytest.raises(PriceChanged):
        comprar_tiquetes(
            cliente_con_billetera,
            vuelo_nacional.pk,
            viajeros_data=[passenger],
            accepted_total=Decimal("1"),
        )
    assert not Compra.objects.exists()
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 125


def test_purchase_api_idempotency(cliente_client, vuelo_nacional, passenger):
    payload = dict(vuelo_id=vuelo_nacional.pk, viajeros=[passenger], accepted_total="150000.00")
    first = cliente_client.post(
        "/api/v1/sales/purchases/", payload, format="json", HTTP_IDEMPOTENCY_KEY="purchase-1"
    )
    assert first.status_code == 201, first.data
    second = cliente_client.post(
        "/api/v1/sales/purchases/", payload, format="json", HTTP_IDEMPOTENCY_KEY="purchase-1"
    )
    assert second.data == first.data
    assert Compra.objects.count() == 1
    payload["accepted_total"] = "2.00"
    assert (
        cliente_client.post(
            "/api/v1/sales/purchases/", payload, format="json", HTTP_IDEMPOTENCY_KEY="purchase-1"
        ).status_code
        == 400
    )


def test_seat_change_and_constraint(cliente_con_billetera, vuelo_nacional, passenger, admin_user):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    with pytest.raises(PermissionDenied):
        cambiar_silla_tiquete(ticket.pk, ticket.silla_id, admin_user)
    assert (
        cambiar_silla_tiquete(
            ticket.pk, ticket.silla_id, cliente_con_billetera
        ).numero_cambios_silla
        == 0
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Tiquete.objects.create(
            compra=ticket.compra,
            vuelo=ticket.vuelo,
            viajero=ticket.viajero,
            silla=ticket.silla,
            clase=ticket.clase,
            precio_pagado=ticket.precio_pagado,
            codigo_tiquete="DUPLICATE",
        )
    seat = Silla.objects.filter(
        vuelo=vuelo_nacional, clase=ticket.clase, estado=EstadoSilla.DISPONIBLE
    ).first()
    assert (
        cambiar_silla_tiquete(ticket.pk, seat.pk, cliente_con_billetera).numero_cambios_silla == 1
    )
    another = Silla.objects.filter(
        vuelo=vuelo_nacional, clase=ticket.clase, estado=EstadoSilla.DISPONIBLE
    ).first()
    from apps.sales.errors import SeatChangeLimitReached

    with pytest.raises(SeatChangeLimitReached):
        cambiar_silla_tiquete(ticket.pk, another.pk, cliente_con_billetera)


def test_refund_once_and_rollback(cliente_con_billetera, vuelo_nacional, passenger):
    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    with patch("apps.sales.services.reembolsar_a_billetera", side_effect=RuntimeError("injected")):
        with pytest.raises(RuntimeError):
            cancelar_compra(purchase.pk, cliente_con_billetera)
    assert purchase.tiquetes.get().estado == "ACTIVO"
    cancelar_compra(purchase.pk, cliente_con_billetera)
    cancelar_compra(purchase.pk, cliente_con_billetera)
    assert MovimientoBilletera.objects.filter(tipo="REEMBOLSO").get().valor == Decimal("150000")


def test_reservation_cancel_and_expiry(cliente_con_billetera, vuelo_nacional, passenger):
    reservation = crear_reserva(cliente_con_billetera, vuelo_nacional.pk, "ECONOMICA", [passenger])
    cancelar_reserva(reservation.pk, cliente_con_billetera)
    cancelar_reserva(reservation.pk, cliente_con_billetera)
    assert not MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()
    reservation = crear_reserva(cliente_con_billetera, vuelo_nacional.pk, "ECONOMICA", [passenger])
    Reserva.objects.filter(pk=reservation.pk).update(
        limite_vigencia=timezone.now() - timedelta(seconds=1)
    )
    assert liberar_reserva_si_vencida(reservation)
    assert not liberar_reserva_si_vencida(reservation)
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 125


def test_flight_cancel(cliente_con_billetera, vuelo_nacional, passenger, admin_user):
    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    reservation = crear_reserva(
        cliente_con_billetera, vuelo_nacional.pk, "ECONOMICA", [{**passenger, "documento": "43"}]
    )
    cancelar_vuelo(vuelo_nacional.pk, "Cancelación de prueba", actor=admin_user)
    reservation.refresh_from_db()
    vuelo_nacional.refresh_from_db()
    assert reservation.estado == "CANCELADA"
    assert vuelo_nacional.estado == "CANCELADO"
    assert vuelo_nacional.cupos_disponibles_economica == 125
    assert purchase.tiquetes.get().refund_id


def test_promotions_new_only(cliente_con_billetera, vuelo_nacional, passenger, admin_user):
    reservation = crear_reserva(cliente_con_billetera, vuelo_nacional.pk, "ECONOMICA", [passenger])
    start = timezone.now() + timedelta(minutes=1)
    end = start + timedelta(hours=1)
    create_promotion(admin_user, vuelo_nacional.pk, "ECONOMICA", Decimal("100000"), start, end)
    with patch("django.utils.timezone.now", return_value=start):
        assert resolver_precio_vigente(vuelo_nacional, "ECONOMICA") == Decimal("100000")
        assert resolver_precio_vigente(
            vuelo_nacional, "ECONOMICA", reservation_created_at=reservation.creada_en
        ) == Decimal("150000")
        with pytest.raises(ValidationError):
            create_promotion(
                admin_user, vuelo_nacional.pk, "ECONOMICA", Decimal("90000"), start, end
            )
    assert resolver_precio_vigente(vuelo_nacional, "ECONOMICA", end) == Decimal("150000")


def test_checkin_group_and_pdf(cliente_con_billetera, vuelo_nacional, passenger):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    with pytest.raises(ValidationError):
        confirm_checkin([ticket.pk], cliente_con_billetera)
    with patch(
        "django.utils.timezone.now", return_value=vuelo_nacional.salida_utc - timedelta(hours=24)
    ):
        with pytest.raises(NotFound):
            confirm_checkin([ticket.pk, ticket.pk + 999], cliente_con_billetera)
        ticket.refresh_from_db()
        assert not ticket.checkin_confirmado
        confirm_checkin([ticket.pk], cliente_con_billetera)
        confirm_checkin([ticket.pk], cliente_con_billetera)
        ticket.refresh_from_db()
        assert boarding_pdf(ticket).startswith(b"%PDF-")
        assert JourneyNotification.objects.filter(boarding_pass=True).count() == 1
    with patch("django.utils.timezone.now", return_value=vuelo_nacional.salida_utc):
        with pytest.raises(ValidationError):
            confirm_checkin([ticket.pk], cliente_con_billetera)


def test_magic_link(cliente_con_billetera, vuelo_nacional, passenger, settings):
    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    settings.GUEST_CHECKIN_FRONTEND_URL = "https://example.invalid/check-in"
    request_link(purchase.localizador, "CC", passenger["documento"], passenger["correo"])
    job = JourneyNotification.objects.get(subject="Acceso seguro al check-in")
    token = job.body.split("#token=")[1].split(".")[0]
    assert authorized_tickets(token=token).count() == 1
    assert not GuestAccess.objects.filter(token_digest=token).exists()
    with patch("django.utils.timezone.now", return_value=vuelo_nacional.salida_utc):
        assert not authorized_tickets(token=token).exists()


def test_reschedule(cliente_con_billetera, vuelo_nacional, passenger, admin_user):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    Tiquete.objects.filter(pk=ticket.pk).update(
        estado_checkin="CONFIRMADO", fecha_checkin=timezone.now()
    )
    reservation = crear_reserva(
        cliente_con_billetera, vuelo_nacional.pk, "ECONOMICA", [{**passenger, "documento": "99"}]
    )
    maximum = reservation.creada_en + timedelta(hours=24)
    editar_vuelo(
        vuelo_nacional.pk,
        fecha_salida=vuelo_nacional.fecha_salida + timedelta(days=2),
        actor=admin_user,
        motivo="Reprogramación",
    )
    ticket.refresh_from_db()
    reservation.refresh_from_db()
    assert not ticket.checkin_confirmado
    assert reservation.limite_vigencia <= maximum
    assert ticket.precio_pagado == Decimal("150000")


def test_relocation(cliente_con_billetera, vuelo_nacional, passenger, admin_user):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    destination = programar_vuelo(
        vuelo_nacional.ruta.origen_id,
        vuelo_nacional.ruta.destino_id,
        vuelo_nacional.fecha_salida + timedelta(days=1),
        time(10),
        Decimal("900000"),
        Decimal("1000000"),
        actor=admin_user,
    )
    offer = offer_relocation(admin_user, ticket.pk, destination.pk)
    result = resolve_relocation(cliente_con_billetera, offer.pk, "ACCEPT")
    assert result.accepted_at
    ticket.refresh_from_db()
    assert ticket.replacement.precio_pagado == ticket.precio_pagado
    assert not MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()
    assert MovimientoBilletera.objects.filter(tipo="COMPRA").count() == 1


@pytest.mark.parametrize("hours", [1, 3])
@pytest.mark.parametrize("offset,allowed", [(-1, True), (0, False), (1, False)])
def test_cancellation_boundaries(
    cliente_con_billetera, vuelo_nacional, passenger, hours, offset, allowed
):
    from apps.sales.errors import CancellationWindowClosed

    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    if hours == 3:
        Vuelo.objects.filter(pk=vuelo_nacional.pk).update(tipo_vuelo="INTERNACIONAL")
    now = vuelo_nacional.salida_utc - timedelta(hours=hours) + timedelta(seconds=offset)
    with patch("django.utils.timezone.now", return_value=now):
        if allowed:
            cancelar_compra(purchase.pk, cliente_con_billetera)
        else:
            with pytest.raises(CancellationWindowClosed):
                cancelar_compra(purchase.pk, cliente_con_billetera)
    assert MovimientoBilletera.objects.filter(tipo="REEMBOLSO").count() == int(allowed)


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "Infinity", "150000", "200000"])
def test_invalid_promotions(admin_user, vuelo_nacional, price):
    start = timezone.now() + timedelta(minutes=1)
    with pytest.raises(ValidationError):
        create_promotion(
            admin_user, vuelo_nacional.pk, "ECONOMICA", price, start, start + timedelta(hours=1)
        )
    assert not vuelo_nacional.promotions.exists()


def test_another_customer_cannot_access_ticket(cliente_con_billetera, vuelo_nacional, passenger):
    from apps.users.models import User

    other = User.objects.create_user(
        email="other@example.invalid",
        username="other",
        first_name="Other",
        last_name="Client",
        document_number="999",
        birth_date=date(1990, 1, 1),
        birth_place="Pereira",
        billing_address="Test",
        gender="M",
        password="Another-safe-password-2026",
        role="CLIENTE",
        is_email_verified=True,
    )
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    with pytest.raises(NotFound):
        cambiar_silla_tiquete(ticket.pk, ticket.silla_id, other)
    with pytest.raises(NotFound):
        confirm_checkin([ticket.pk], other)
    assert not authorized_tickets(other).filter(pk=ticket.pk).exists()


def test_guest_csrf_and_email_throttle(cliente_con_billetera, vuelo_nacional, passenger, settings):
    from rest_framework.test import APIClient

    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    settings.GUEST_CHECKIN_FRONTEND_URL = "https://example.invalid/check-in"
    client = APIClient(enforce_csrf_checks=True)
    payload = dict(
        locator=purchase.localizador,
        document_type="CC",
        document=passenger["documento"],
        email=passenger["correo"],
    )
    assert client.post("/api/v1/sales/check-in/access/", payload, format="json").status_code == 403
    csrf = client.get("/api/v1/auth/csrf/").data["csrf_token"]
    first = client.post(
        "/api/v1/sales/check-in/access/", payload, format="json", HTTP_X_CSRFTOKEN=csrf
    )
    assert first.status_code == 202, first.data
    again = client.post(
        "/api/v1/sales/check-in/access/", payload, format="json", HTTP_X_CSRFTOKEN=csrf
    )
    assert again.status_code == 429
    assert "Retry-After" in again
    assert GuestAccess.objects.count() == 1


def test_flight_cancellation_rolls_back_every_buyer(
    cliente_con_billetera, vuelo_nacional, passenger, admin_user
):
    purchase = comprar_tiquetes(
        cliente_con_billetera,
        vuelo_nacional.pk,
        viajeros_data=[passenger, {**passenger, "documento": "43"}],
        accepted_total=Decimal("300000"),
    )
    from apps.sales import services

    refund = services.reembolsar_a_billetera
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected")
        return refund(*args, **kwargs)

    with (
        patch("apps.sales.services.reembolsar_a_billetera", side_effect=fail_second),
        pytest.raises(RuntimeError),
    ):
        cancelar_vuelo(vuelo_nacional.pk, "Prueba de rollback", actor=admin_user)
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.estado == "PROGRAMADO"
    assert purchase.tiquetes.filter(estado="ACTIVO").count() == 2
    assert not MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()


def test_quote_and_discount_accepted_total(
    cliente_con_billetera, cliente_client, vuelo_nacional, passenger, admin_user
):
    start = timezone.now() + timedelta(minutes=1)
    create_promotion(
        admin_user, vuelo_nacional.pk, "ECONOMICA", "100000", start, start + timedelta(hours=2)
    )
    with patch("django.utils.timezone.now", return_value=start):
        quote = cliente_client.post(
            "/api/v1/sales/quote/",
            {"vuelo_id": vuelo_nacional.pk, "passenger_count": 1},
            format="json",
        )
        assert quote.status_code == 200, quote.data
        assert Decimal(quote.data["total"]) == Decimal("100000")
        purchase = comprar_tiquetes(
            cliente_con_billetera,
            vuelo_nacional.pk,
            viajeros_data=[passenger],
            accepted_total=quote.data["total"],
        )
        assert purchase.tiquetes.get().precio_pagado == Decimal("100000")


@pytest.mark.django_db(transaction=True)
def test_pdf_mail_failure_preserves_checkin_and_retries(
    cliente_con_billetera, vuelo_nacional, passenger
):
    from django.core import mail

    from apps.sales.journey_mail import process_journey_emails

    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    with patch(
        "django.utils.timezone.now", return_value=vuelo_nacional.salida_utc - timedelta(hours=1)
    ):
        confirm_checkin([ticket.pk], cliente_con_billetera)
        with patch("apps.sales.journey_mail.boarding_pdf", side_effect=RuntimeError("injected")):
            assert process_journey_emails() == (0, 1)
        ticket.refresh_from_db()
        assert ticket.checkin_confirmado
        job = JourneyNotification.objects.get(boarding_pass=True)
        assert job.sent_at is None and job.attempts == 1
        JourneyNotification.objects.filter(pk=job.pk).update(next_attempt_at=timezone.now())
        assert process_journey_emails() == (1, 0)
        assert len(mail.outbox[-1].attachments) == 1
        assert process_journey_emails() == (0, 0)


@pytest.mark.django_db(transaction=True)
def test_two_tickets_compete_for_one_seat(cliente_con_billetera, vuelo_nacional, passenger):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connections

    from apps.sales.errors import SeatNotAvailable

    purchase = comprar_tiquetes(
        cliente_con_billetera,
        vuelo_nacional.pk,
        viajeros_data=[passenger, {**passenger, "documento": "43"}],
        accepted_total="300000",
    )
    ids = list(purchase.tiquetes.values_list("pk", flat=True))
    target = Silla.objects.filter(
        vuelo=vuelo_nacional, clase="ECONOMICA", estado="DISPONIBLE"
    ).first()
    barrier = Barrier(2)

    def change(ticket_id):
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            cambiar_silla_tiquete(ticket_id, target.pk, cliente_con_billetera)
            return "ok"
        except SeatNotAvailable:
            return "unavailable"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(change, i) for i in ids]
        assert sorted(f.result(timeout=15) for f in futures) == ["ok", "unavailable"]
    assert Tiquete.objects.filter(silla=target, estado="ACTIVO").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_cancel_refunds_only_once(cliente_con_billetera, vuelo_nacional, passenger):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connections

    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    barrier = Barrier(2)

    def cancel():
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            return cancelar_compra(purchase.pk, cliente_con_billetera).estado
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(cancel) for _ in range(2)]
        assert [f.result(timeout=15) for f in futures] == ["CANCELADA", "CANCELADA"]
    assert MovimientoBilletera.objects.filter(tipo="REEMBOLSO").count() == 1
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 125


def test_promotion_api_and_news_visibility(admin_user, vuelo_nacional):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(admin_user)
    start = timezone.now() + timedelta(minutes=1)
    end = start + timedelta(hours=1)
    result = client.post(
        f"/api/v1/sales/flights/{vuelo_nacional.pk}/promotions/",
        dict(
            clase="ECONOMICA",
            price="90000.00",
            starts_at=start.isoformat(),
            ends_at=end.isoformat(),
        ),
        format="json",
    )
    assert result.status_code == 201, result.data
    promotion_type = f"PROMOTION_{result.data['id']}"
    assert promotion_type not in [
        n["tipo"] for n in client.get("/api/v1/sales/flight-news/").data["results"]
    ]
    with patch("django.utils.timezone.now", return_value=start):
        assert promotion_type in [
            n["tipo"] for n in client.get("/api/v1/sales/flight-news/").data["results"]
        ]
    with patch("django.utils.timezone.now", return_value=end):
        assert promotion_type not in [
            n["tipo"] for n in client.get("/api/v1/sales/flight-news/").data["results"]
        ]


def test_buyer_checkin_and_pdf_http(
    cliente_client, cliente_con_billetera, vuelo_nacional, passenger
):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    # Public mutations retain CSRF protection even when the test user is force-authenticated.
    csrf = cliente_client.get("/api/v1/auth/csrf/").data["csrf_token"]
    with patch(
        "django.utils.timezone.now", return_value=vuelo_nacional.salida_utc - timedelta(hours=1)
    ):
        response = cliente_client.post(
            "/api/v1/sales/check-in/",
            {"ticket_ids": [ticket.pk]},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        assert response.status_code == 200, response.data
        download = cliente_client.get(f"/api/v1/sales/tickets/{ticket.pk}/boarding-pass/")
        assert download.status_code == 200
        assert download.content.startswith(b"%PDF-")
        assert download["Cache-Control"] == "private, no-store"
        assert cliente_client.get("/api/v1/sales/tickets/999999/boarding-pass/").status_code == 404


def test_relocation_no_capacity_refunds(
    cliente_con_billetera, vuelo_nacional, passenger, admin_user
):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    destination = programar_vuelo(
        vuelo_nacional.ruta.origen_id,
        vuelo_nacional.ruta.destino_id,
        vuelo_nacional.fecha_salida + timedelta(days=1),
        time(10),
        Decimal("900000"),
        Decimal("1000000"),
        actor=admin_user,
    )
    offer = offer_relocation(admin_user, ticket.pk, destination.pk)
    Vuelo.objects.filter(pk=destination.pk).update(cupos_disponibles_economica=0)
    result = resolve_relocation(cliente_con_billetera, offer.pk, "ACCEPT")
    assert result.decision == "REFUND"
    ticket.refresh_from_db()
    assert ticket.refund_id
    assert not Tiquete.objects.filter(replacement_of=ticket).exists()


def test_magic_link_renewal_revokes_old_access(
    cliente_con_billetera, vuelo_nacional, passenger, settings
):
    settings.GUEST_CHECKIN_FRONTEND_URL = "https://example.invalid/check-in"
    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    request_link(purchase.localizador, "CC", passenger["documento"], passenger["correo"])
    old = JourneyNotification.objects.get(guest_access__isnull=False)
    token = old.body.split("#token=")[1].split(".")[0]
    request_link(purchase.localizador, "CC", passenger["documento"], passenger["correo"])
    with pytest.raises(PermissionDenied):
        authorized_tickets(token=token)
    old.refresh_from_db()
    assert old.cancelled_at
    assert GuestAccess.objects.filter(revoked_at__isnull=True).count() == 1


def test_performed_transition_is_explicit(admin_user, vuelo_nacional):
    from apps.flights.operations import complete_flight

    with pytest.raises(ValidationError):
        complete_flight(admin_user, vuelo_nacional.pk)
    with patch("django.utils.timezone.now", return_value=vuelo_nacional.salida_utc):
        assert complete_flight(admin_user, vuelo_nacional.pk).estado == "REALIZADO"
        assert complete_flight(admin_user, vuelo_nacional.pk).estado == "REALIZADO"


def test_dst_gap_and_overlap_rejected():
    from apps.flights.services import calcular_llegada

    for day, clock in [(date(2026, 3, 8), time(2, 30)), (date(2026, 11, 1), time(1, 30))]:
        with pytest.raises(ValidationError):
            calcular_llegada(day, clock, 60, "America/New_York", "America/Bogota")


def test_unlinked_debit_never_creates_refund(cliente_con_billetera, vuelo_nacional, passenger):
    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    Compra.objects.filter(pk=purchase.pk).update(debit=None)
    with pytest.raises(ValidationError):
        cancelar_compra(purchase.pk, cliente_con_billetera)
    assert purchase.tiquetes.get().estado == "ACTIVO"
    assert not MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()


def test_migration_links_only_unambiguous_payment(cliente_con_billetera, vuelo_nacional, passenger):
    from importlib import import_module

    from django.apps import apps

    purchase = buy(cliente_con_billetera, vuelo_nacional, passenger)
    debit = purchase.debit
    Compra.objects.filter(pk=purchase.pk).update(debit=None)
    migrate = import_module(
        "apps.sales.migrations.0005_link_legacy_purchase_debits"
    ).link_unambiguous_debits
    migrate(apps, None)
    purchase.refresh_from_db()
    assert purchase.debit_id == debit.pk
    Compra.objects.filter(pk=purchase.pk).update(debit=None)
    MovimientoBilletera.objects.create(
        wallet=debit.wallet,
        tipo="COMPRA",
        valor=debit.valor,
        saldo_resultante=debit.saldo_resultante,
        referencia=debit.referencia,
    )
    migrate(apps, None)
    purchase.refresh_from_db()
    assert purchase.debit_id is None


def test_round_trip_reschedule_flags_incompatible_paid_itinerary(
    cliente_con_billetera, vuelo_nacional, passenger, admin_user
):
    inbound = programar_vuelo(
        vuelo_nacional.ruta.destino_id,
        vuelo_nacional.ruta.origen_id,
        vuelo_nacional.fecha_salida + timedelta(days=1),
        time(10),
        Decimal("150000"),
        Decimal("220000"),
        actor=admin_user,
    )
    purchase = comprar_tiquetes(
        cliente_con_billetera,
        vuelo_nacional.pk,
        viajeros_data=[passenger],
        vuelo_regreso_id=inbound.pk,
        tipo_trayecto="COMPLETO",
        accepted_total="300000",
    )
    editar_vuelo(
        vuelo_nacional.pk,
        fecha_salida=inbound.fecha_salida + timedelta(days=1),
        actor=admin_user,
        motivo="Cambio de operación",
    )
    purchase.refresh_from_db()
    assert purchase.disrupted
    assert JourneyNotification.objects.filter(
        subject="Revisión de itinerario requerida", recipient=cliente_con_billetera.email
    ).exists()
    assert not MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()


def test_guest_cannot_confirm_another_traveler_in_same_locator(
    cliente_con_billetera, vuelo_nacional, passenger, settings
):
    settings.GUEST_CHECKIN_FRONTEND_URL = "https://example.invalid/check-in"
    purchase = comprar_tiquetes(
        cliente_con_billetera,
        vuelo_nacional.pk,
        viajeros_data=[
            passenger,
            {**passenger, "documento": "43", "correo": "other-traveler@example.invalid"},
        ],
        accepted_total="300000",
    )
    request_link(purchase.localizador, "CC", passenger["documento"], passenger["correo"])
    token = (
        JourneyNotification.objects.get(guest_access__isnull=False)
        .body.split("#token=")[1]
        .split(".")[0]
    )
    with (
        patch(
            "django.utils.timezone.now", return_value=vuelo_nacional.salida_utc - timedelta(hours=1)
        ),
        pytest.raises(NotFound),
    ):
        confirm_checkin(list(purchase.tiquetes.values_list("pk", flat=True)), token=token)
    assert not purchase.tiquetes.filter(estado_checkin="CONFIRMADO").exists()


def test_required_operation_key(cliente_client, vuelo_nacional, passenger):
    response = cliente_client.post(
        "/api/v1/sales/purchases/",
        dict(vuelo_id=vuelo_nacional.pk, viajeros=[passenger], accepted_total="150000"),
        format="json",
    )
    assert response.status_code == 400
    assert not Compra.objects.exists()


def test_base_fare_change_disables_invalid_discount(admin_user, vuelo_nacional):
    start = timezone.now() + timedelta(minutes=1)
    promotion = create_promotion(
        admin_user, vuelo_nacional.pk, "ECONOMICA", "140000", start, start + timedelta(hours=1)
    )
    editar_vuelo(
        vuelo_nacional.pk,
        costo_persona_economica="130000",
        actor=admin_user,
        motivo="Nueva tarifa base",
    )
    promotion.refresh_from_db()
    assert not promotion.active and promotion.disabled_reason == "flight_edited"
    assert not vuelo_nacional.noticias.filter(
        tipo=f"PROMOTION_{promotion.pk}", vigente=True
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_purchase_key(cliente_con_billetera, vuelo_nacional, passenger):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connections

    from apps.sales.idempotency import execute
    from apps.sales.models import OperationRequest

    barrier = Barrier(2)

    def attempt():
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            return execute(
                cliente_con_billetera,
                "purchase",
                "same-operation",
                {"flight": vuelo_nacional.pk},
                lambda: {"id": buy(cliente_con_billetera, vuelo_nacional, passenger).pk},
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        results = [f.result(timeout=15) for f in futures]
    assert results[0] == results[1]
    assert Compra.objects.count() == 1
    assert OperationRequest.objects.count() == 1
    assert MovimientoBilletera.objects.filter(tipo="COMPRA").count() == 1


@pytest.mark.parametrize("command", ["seed_dev_data", "cargar_datos_demostracion"])
def test_demo_commands_disabled_outside_debug(command, settings):
    from django.core.management import CommandError, call_command

    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command(command)
    assert not Compra.objects.exists()


def test_documented_password_minimum_without_invented_digit_rule():
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError

    with pytest.raises(DjangoValidationError):
        validate_password("shortphrase")
    validate_password("quiet telescope amber orbit")


def test_immediately_active_promotion_is_allowed(admin_user, vuelo_nacional):
    now = timezone.now()
    promotion = create_promotion(
        admin_user,
        vuelo_nacional.pk,
        "ECONOMICA",
        "100000",
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    assert resolver_precio_vigente(vuelo_nacional, "ECONOMICA") == promotion.price


def test_existing_ticket_access_survives_email_reverification(
    cliente_con_billetera, vuelo_nacional, passenger
):
    ticket = buy(cliente_con_billetera, vuelo_nacional, passenger).tiquetes.get()
    cliente_con_billetera.is_email_verified = False
    cliente_con_billetera.save(update_fields=["is_email_verified"])
    assert authorized_tickets(cliente_con_billetera).filter(pk=ticket.pk).exists()
    assert cambiar_silla_tiquete(ticket.pk, ticket.silla_id, cliente_con_billetera).pk == ticket.pk
    with patch(
        "django.utils.timezone.now", return_value=vuelo_nacional.salida_utc - timedelta(hours=1)
    ):
        assert confirm_checkin([ticket.pk], cliente_con_billetera)[0].checkin_confirmado
    with pytest.raises(PermissionDenied):
        crear_reserva(
            cliente_con_billetera,
            vuelo_nacional.pk,
            "ECONOMICA",
            [{**passenger, "documento": "444"}],
        )
