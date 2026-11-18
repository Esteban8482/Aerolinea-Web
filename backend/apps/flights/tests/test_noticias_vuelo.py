from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.flights.models import Ciudad, EstadoVuelo, NoticiaVuelo, Vuelo
from apps.flights.services import programar_vuelo


@pytest.fixture
def vuelo_antiguo(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=4),
        hora_salida=time(9, 0),
        costo_persona_economica=Decimal("150000.00"),
        actor=admin_user,
    )


@pytest.fixture
def vuelo_reciente(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Cartagena")
    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=6),
        hora_salida=time(15, 0),
        costo_persona_economica=Decimal("210000.00"),
        actor=admin_user,
    )


@pytest.mark.django_db
def test_news_lista_noticias_vigentes_ordenadas_por_reciente(vuelo_antiguo, vuelo_reciente):
    client = APIClient()
    response = client.get("/api/v1/flights/news/")
    assert response.status_code == 200
    noticias = response.json()
    assert len(noticias) == 2

    # Más reciente primero, con los datos del vuelo para renderizar tarjetas
    assert noticias[0]["vuelo"]["codigo_vuelo"] == vuelo_reciente.codigo_vuelo
    assert noticias[1]["vuelo"]["codigo_vuelo"] == vuelo_antiguo.codigo_vuelo

    tarjeta = noticias[0]
    assert tarjeta["titulo"]
    assert tarjeta["vuelo"]["origen"] == "Bogotá"
    assert tarjeta["vuelo"]["destino"] == "Cartagena"
    assert tarjeta["vuelo"]["fecha_salida"] == str(vuelo_reciente.fecha_salida)
    assert tarjeta["vuelo"]["costo_persona_economica"] == "210000.00"


@pytest.mark.django_db
def test_news_excluye_vuelos_no_programados_y_noticias_no_vigentes(
    vuelo_antiguo, vuelo_reciente
):
    Vuelo.objects.filter(pk=vuelo_reciente.pk).update(estado=EstadoVuelo.CANCELADO)
    NoticiaVuelo.objects.filter(vuelo=vuelo_antiguo).update(vigente=False)

    client = APIClient()
    response = client.get("/api/v1/flights/news/")
    assert response.status_code == 200
    assert response.json() == []

    # Un vuelo realizado tampoco aparece en las noticias del Home
    Vuelo.objects.filter(pk=vuelo_reciente.pk).update(estado=EstadoVuelo.REALIZADO)
    NoticiaVuelo.objects.filter(vuelo=vuelo_reciente).update(vigente=True)
    response = client.get("/api/v1/flights/news/")
    assert response.json() == []
