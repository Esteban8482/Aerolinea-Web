from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from apps.flights.models import Silla
from apps.flights.services import programar_vuelo
from apps.sales.cancellations import ResolutionConflict, alternatives, cancel, resolve
from apps.sales.checkin import boarding_pdf
from apps.sales.models import CancellationResolution, JourneyNotification, Tiquete
from apps.sales.services import comprar_tiquetes
from apps.wallets.models import MovimientoBilletera

pytestmark = pytest.mark.django_db


def traveler(number, child=False):
    return dict(
        documento=str(number),
        tipo_documento="CC",
        nombres="Persona",
        apellidos="Prueba",
        fecha_nacimiento=date.today().replace(year=date.today().year - (10 if child else 30)),
        genero="F",
        correo=f"traveler{number}@example.invalid",
        telefono="1234567",
        nombre_contacto="Contacto",
        telefono_contacto="7654321",
    )


@pytest.fixture
def cancelled_group(cliente_con_billetera, vuelo_nacional, admin_user):
    purchase = comprar_tiquetes(
        cliente_con_billetera,
        vuelo_nacional.pk,
        viajeros_data=[traveler(1), traveler(2, True)],
        accepted_total=Decimal("300000"),
    )
    cancel(admin_user, vuelo_nacional.pk, "Cancelación aprobada")
    return CancellationResolution.objects.get(purchase=purchase)


@pytest.fixture
def replacement(vuelo_nacional, admin_user):
    return programar_vuelo(
        origen_id=vuelo_nacional.ruta.origen_id,
        destino_id=vuelo_nacional.ruta.destino_id,
        fecha_salida=date.today() + timedelta(days=6),
        hora_salida=time(10),
        costo_persona_economica="900000",
        costo_persona_primera="1000000",
        actor=admin_user,
    )


def test_cancel_creates_pending_group_without_refunds_and_notifies_only_buyer(cancelled_group):
    r = cancelled_group
    assert r.tickets.filter(estado="PENDIENTE_RESOLUCION").count() == 2
    assert not MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()
    jobs = JourneyNotification.objects.filter(subject="Gestiona la cancelación de tu vuelo")
    assert list(jobs.values_list("recipient", flat=True)) == [r.purchase.cliente.email]
    assert f"/cancelaciones/{r.pk}" in jobs.get().body
    assert r.purchase.tiquetes.filter(estado="ACTIVO").count() == 0


def test_group_relocation_preserves_prices_seat_limit_and_retry(cancelled_group, replacement):
    r = cancelled_group
    original = r.tickets.order_by("pk").first()
    original.numero_cambios_silla = 1
    original.save()
    before = r.purchase.cliente.wallet.balance
    assert [f.pk for f in alternatives(r)] == [replacement.pk]
    result = resolve(r.purchase.cliente, r.pk, "RELOCATE", replacement.pk)
    assert result.status == "RELOCATED"
    new = Tiquete.objects.filter(replacement_of__cancellation_resolution=r)
    assert new.count() == 2
    assert set(new.values_list("precio_pagado", flat=True)) == {Decimal("150000")}
    assert new.get(replacement_of=original).numero_cambios_silla == 1
    assert set(new.values_list("estado_checkin", flat=True)) == {"PENDIENTE"}
    resolve(r.purchase.cliente, r.pk, "RELOCATE", replacement.pk)
    assert new.count() == 2
    assert r.purchase.cliente.wallet.balance == before
    with pytest.raises(ResolutionConflict):
        resolve(r.purchase.cliente, r.pk, "REFUND")


def test_full_group_capacity_conflict_keeps_refund_available(cancelled_group, replacement):
    replacement.cupos_disponibles_economica = 1
    replacement.save()
    assert alternatives(cancelled_group) == []
    with pytest.raises(ResolutionConflict):
        resolve(cancelled_group.purchase.cliente, cancelled_group.pk, "RELOCATE", replacement.pk)
    cancelled_group.refresh_from_db()
    assert cancelled_group.status == "PENDING"
    result = resolve(cancelled_group.purchase.cliente, cancelled_group.pk, "REFUND")
    assert result.status == "REFUNDED"
    resolve(cancelled_group.purchase.cliente, cancelled_group.pk, "REFUND")
    assert MovimientoBilletera.objects.filter(tipo="REEMBOLSO").count() == 2
    assert sum(
        MovimientoBilletera.objects.filter(tipo="REEMBOLSO").values_list("valor", flat=True)
    ) == Decimal("300000")


def test_relocation_group_rollback(cancelled_group, replacement):
    original_create = Tiquete.objects.create
    count = 0

    def fail_second(**kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("injected")
        return original_create(**kwargs)

    with (
        patch.object(Tiquete.objects, "create", side_effect=fail_second),
        pytest.raises(RuntimeError),
    ):
        resolve(cancelled_group.purchase.cliente, cancelled_group.pk, "RELOCATE", replacement.pk)
    assert (
        Tiquete.objects.filter(replacement_of__cancellation_resolution=cancelled_group).count() == 0
    )
    assert not Silla.objects.filter(vuelo=replacement, estado="OCUPADA").exists()
    cancelled_group.refresh_from_db()
    assert cancelled_group.status == "PENDING"


def test_resolution_ownership_and_confirmation(cancelled_group, admin_user):
    client = APIClient()
    client.force_authenticate(cancelled_group.purchase.cliente)
    endpoint = f"/api/v1/sales/cancellations/{cancelled_group.pk}/"
    assert client.get(endpoint).status_code == 200
    assert client.post(endpoint, {"decision": "REFUND", "confirmed": False}).status_code == 400
    assert client.post(endpoint, {"decision": "REFUND", "confirmed": True}).status_code == 200
    client.force_authenticate(admin_user)
    assert client.post(endpoint, {"decision": "REFUND", "confirmed": True}).status_code == 403
    panel = client.get(f"/api/v1/sales/flights/{cancelled_group.flight_id}/cancellation-panel/")
    assert panel.data["summary"]["REFUNDED"] == 2


def test_cancel_invalidates_boarding_and_is_repeat_safe(cancelled_group, admin_user):
    from rest_framework.exceptions import ValidationError

    cancel(admin_user, cancelled_group.flight_id, "Reintento")
    assert CancellationResolution.objects.count() == 1
    with pytest.raises(ValidationError):
        boarding_pdf(cancelled_group.tickets.first())


@pytest.mark.django_db(transaction=True)
def test_concurrent_incompatible_resolutions_have_one_outcome(cancelled_group, replacement):
    barrier = Barrier(2)
    buyer, pk, destination = cancelled_group.purchase.cliente, cancelled_group.pk, replacement.pk

    def attempt(decision):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return resolve(
                buyer, pk, decision, destination if decision == "RELOCATE" else None
            ).status
        except ResolutionConflict:
            return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["RELOCATE", "REFUND"]))
    assert results.count("conflict") == 1
    cancelled_group.refresh_from_db()
    assert cancelled_group.status in ("RELOCATED", "REFUNDED")
    assert not (
        Tiquete.objects.filter(replacement_of__cancellation_resolution=cancelled_group).exists()
        and MovimientoBilletera.objects.filter(tipo="REEMBOLSO").exists()
    )
