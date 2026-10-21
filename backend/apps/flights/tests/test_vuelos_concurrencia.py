from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.db import connection

from apps.flights.errors import FlightCodeExhausted
from apps.flights.models import Ciudad, SecuenciaCodigoVuelo
from apps.flights.services import generar_codigo_vuelo, programar_vuelo


@pytest.mark.django_db(transaction=True)
def test_ca01_generacion_concurrente_de_codigos_de_vuelo(catalogo, admin_user):
    """CA-01: Dos administradores crean vuelos simultáneamente.

    Deben obtener códigos válidos, distintos y consecutivos sin colisiones.
    """
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    fecha_salida = date.today() + timedelta(days=20)
    hora_salida = time(10, 0)

    def crear_un_vuelo():
        connection.close()
        return programar_vuelo(
            origen_id=origen.pk,
            destino_id=destino.pk,
            fecha_salida=fecha_salida,
            hora_salida=hora_salida,
            costo_persona_economica=Decimal("150000.00"),
            actor=admin_user,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(crear_un_vuelo)
        future2 = executor.submit(crear_un_vuelo)
        vuelo1 = future1.result(timeout=10)
        vuelo2 = future2.result(timeout=10)

    assert vuelo1.codigo_vuelo != vuelo2.codigo_vuelo
    assert vuelo1.codigo_vuelo.startswith("XX")
    assert vuelo2.codigo_vuelo.startswith("XX")

    consecutivos = sorted([int(vuelo1.codigo_vuelo[2:]), int(vuelo2.codigo_vuelo[2:])])
    assert consecutivos[1] == consecutivos[0] + 1


@pytest.mark.django_db(transaction=True)
def test_agotamiento_controlado_de_codigos_de_vuelo(catalogo):
    """DEC-01: Agotar 9999 números produce un error controlado."""
    secuencia, _ = SecuenciaCodigoVuelo.objects.get_or_create(prefijo="XX")
    secuencia.ultimo_consecutivo = 9999
    secuencia.save()

    with pytest.raises(FlightCodeExhausted):
        generar_codigo_vuelo()
