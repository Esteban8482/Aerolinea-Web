from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from apps.flights.models import Ciudad
from apps.flights.services import programar_vuelo
from apps.sales.models import HistorialBusqueda


@pytest.fixture
def vuelos_de_prueba(catalogo, admin_user):
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")

    hoy = date.today()
    fecha_ida = hoy + timedelta(days=5)
    fecha_regreso = hoy + timedelta(days=10)

    # Vuelo ida Bogotá -> Pereira
    vuelo_ida = programar_vuelo(
        origen_id=bogota.pk,
        destino_id=pereira.pk,
        fecha_salida=fecha_ida,
        hora_salida=time(9, 0),
        costo_persona_economica=Decimal("150000.00"),
        costo_persona_primera=Decimal("220000.00"),
        actor=admin_user,
    )

    # Vuelo regreso Pereira -> Bogotá
    vuelo_regreso = programar_vuelo(
        origen_id=pereira.pk,
        destino_id=bogota.pk,
        fecha_salida=fecha_regreso,
        hora_salida=time(18, 0),
        costo_persona_economica=Decimal("160000.00"),
        costo_persona_primera=Decimal("240000.00"),
        actor=admin_user,
    )

    return vuelo_ida, vuelo_regreso


@pytest.mark.django_db
def test_buscar_vuelo_trayecto_unico_exitoso(vuelos_de_prueba, anon_client):
    vuelo_ida, _ = vuelos_de_prueba
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": bogota.pk,
        "destino_id": pereira.pk,
        "tipo_trayecto": "UNICO",
        "pasajeros": 2,
        "clase": "ECONOMICA",
    }

    response = anon_client.post("/api/v1/flights/search/", data, format="json")
    assert response.status_code == 200
    res = response.json()

    assert res["tipo_trayecto"] == "UNICO"
    assert len(res["vuelos_ida"]) >= 1
    assert res["vuelos_ida"][0]["codigo_vuelo"] == vuelo_ida.codigo_vuelo
    assert len(res["vuelos_regreso"]) == 0


@pytest.mark.django_db
def test_buscar_vuelo_trayecto_completo_ida_y_regreso(vuelos_de_prueba, anon_client):
    vuelo_ida, vuelo_regreso = vuelos_de_prueba
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": bogota.pk,
        "destino_id": pereira.pk,
        "tipo_trayecto": "COMPLETO",
        "fecha_salida": str(vuelo_ida.fecha_salida),
        "fecha_regreso": str(vuelo_regreso.fecha_salida),
        "pasajeros": 1,
    }

    response = anon_client.post("/api/v1/flights/search/", data, format="json")
    assert response.status_code == 200
    res = response.json()

    assert res["tipo_trayecto"] == "COMPLETO"
    assert len(res["vuelos_ida"]) >= 1
    assert res["vuelos_ida"][0]["codigo_vuelo"] == vuelo_ida.codigo_vuelo
    assert len(res["vuelos_regreso"]) >= 1
    assert res["vuelos_regreso"][0]["codigo_vuelo"] == vuelo_regreso.codigo_vuelo


@pytest.mark.django_db
def test_buscar_vuelos_fecha_regreso_anterior_a_salida_rechazada(vuelos_de_prueba, anon_client):
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")

    hoy = date.today()
    data = {
        "origen_id": bogota.pk,
        "destino_id": pereira.pk,
        "tipo_trayecto": "COMPLETO",
        "fecha_salida": str(hoy + timedelta(days=10)),
        "fecha_regreso": str(hoy + timedelta(days=5)),
    }

    response = anon_client.post("/api/v1/flights/search/", data, format="json")
    assert response.status_code == 400
    assert "fecha_regreso" in response.json()["details"]


@pytest.mark.django_db
def test_buscar_vuelos_origen_igual_destino_rechazado(vuelos_de_prueba, anon_client):
    bogota = Ciudad.objects.get(nombre="Bogotá")

    data = {
        "origen_id": bogota.pk,
        "destino_id": bogota.pk,
    }

    response = anon_client.post("/api/v1/flights/search/", data, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_buscar_vuelos_excluye_cancelados_y_cupos_insuficientes(vuelos_de_prueba, anon_client):
    vuelo_ida, _ = vuelos_de_prueba
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")

    # Si se agotan los cupos de primera clase:
    vuelo_ida.cupos_disponibles_primera = 0
    vuelo_ida.save()

    data = {
        "origen_id": bogota.pk,
        "destino_id": pereira.pk,
        "clase": "PRIMERA_CLASE",
        "pasajeros": 1,
    }

    res = anon_client.post("/api/v1/flights/search/", data, format="json")
    assert res.status_code == 200
    assert len(res.json()["vuelos_ida"]) == 0


@pytest.mark.django_db
def test_buscar_vuelos_registra_historial_para_usuario_autenticado(
    vuelos_de_prueba, regular_client, client_user
):
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": bogota.pk,
        "destino_id": pereira.pk,
        "tipo_trayecto": "UNICO",
        "pasajeros": 2,
    }

    res = regular_client.post("/api/v1/flights/search/", data, format="json")
    assert res.status_code == 200

    historial = HistorialBusqueda.objects.filter(usuario=client_user)
    assert historial.exists()
    assert historial.first().pasajeros == 2


@pytest.mark.django_db
def test_buscar_vuelos_precio_min_max_y_rango_invalido(vuelos_de_prueba, anon_client):
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")
    base = {
        "origen_id": bogota.pk,
        "destino_id": pereira.pk,
        "clase": "ECONOMICA",
        "precio_min": "100000.00",
        "precio_max": "200000.00",
    }
    response = anon_client.post("/api/v1/flights/search/", base, format="json")
    assert response.status_code == 200
    assert response.json()["vuelos_ida"]
    assert all(
        Decimal(flight["precio_por_persona"]) >= Decimal("100000")
        and Decimal(flight["precio_por_persona"]) <= Decimal("200000")
        for flight in response.json()["vuelos_ida"]
    )

    invalid = anon_client.post(
        "/api/v1/flights/search/",
        {**base, "precio_min": "200000", "precio_max": "100000"},
        format="json",
    )
    assert invalid.status_code == 400
    assert "precio_min" in invalid.json()["details"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "orden",
    ["precio_asc", "precio_desc", "salida_asc", "salida_desc"],
)
def test_buscar_vuelos_admite_todos_los_ordenes(vuelos_de_prueba, anon_client, orden):
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")
    response = anon_client.post(
        "/api/v1/flights/search/",
        {
            "origen_id": bogota.pk,
            "destino_id": pereira.pk,
            "orden": orden,
        },
        format="json",
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_buscar_sin_clase_identifica_tarifa_elegible_y_clase(vuelos_de_prueba, anon_client):
    bogota = Ciudad.objects.get(nombre="Bogotá")
    pereira = Ciudad.objects.get(nombre="Pereira")
    response = anon_client.post(
        "/api/v1/flights/search/",
        {
            "origen_id": bogota.pk,
            "destino_id": pereira.pk,
            "pasajeros": 1,
        },
        format="json",
    )
    assert response.status_code == 200
    flight = response.json()["vuelos_ida"][0]
    assert flight["clase_aplicable"] == "ECONOMICA"
    assert Decimal(flight["precio_por_persona"]) == Decimal("150000.00")
