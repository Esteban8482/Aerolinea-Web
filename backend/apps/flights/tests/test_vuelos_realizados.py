from datetime import date, time, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.flights.models import Ciudad, EstadoVuelo, Vuelo
from apps.flights.services import programar_vuelo


@pytest.fixture
def vuelo_pendiente(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=3),
        hora_salida=time(10, 0),
        costo_persona_economica=Decimal("150000.00"),
        actor=admin_user,
    )


@pytest.fixture
def vuelo_aterrizado(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Cartagena")
    vuelo = programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=2),
        hora_salida=time(8, 0),
        costo_persona_economica=Decimal("200000.00"),
        actor=admin_user,
    )
    pasado = timezone.now() - timedelta(hours=2)
    Vuelo.objects.filter(pk=vuelo.pk).update(salida_utc=pasado, llegada_utc=pasado)
    return vuelo


@pytest.mark.django_db
def test_marcar_vuelos_realizados_solo_vencidos_e_idempotente(vuelo_pendiente, vuelo_aterrizado):
    out = StringIO()
    call_command("marcar_vuelos_realizados", stdout=out)
    assert "Vuelos marcados como realizados: 1." in out.getvalue()

    vuelo_aterrizado.refresh_from_db()
    assert vuelo_aterrizado.estado == EstadoVuelo.REALIZADO

    vuelo_pendiente.refresh_from_db()
    assert vuelo_pendiente.estado == EstadoVuelo.PROGRAMADO

    # Segunda corrida: no vuelve a marcar nada (idempotente)
    out = StringIO()
    call_command("marcar_vuelos_realizados", stdout=out)
    assert "Vuelos marcados como realizados: 0." in out.getvalue()
