from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from apps.flights.models import BitacoraVuelo, Ciudad, EstadoVuelo, NotificacionAfectacion
from apps.flights.services import programar_vuelo


@pytest.fixture
def vuelo_programado(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=3),
        hora_salida=time(10, 0),
        costo_persona_economica=Decimal("150000.00"),
        costo_persona_primera=Decimal("225000.00"),
        actor=admin_user,
    )


@pytest.mark.django_db
def test_editar_vuelo_fecha_y_hora_exitoso(vuelo_programado, admin_client):
    nueva_fecha = date.today() + timedelta(days=4)
    nueva_hora = "16:00:00"

    data = {
        "fecha_salida": str(nueva_fecha),
        "hora_salida": nueva_hora,
    }

    url = f"/api/v1/flights/{vuelo_programado.pk}/"
    response = admin_client.patch(url, data, format="json")
    assert response.status_code == 200
    resp = response.json()

    assert resp["fecha_salida"] == str(nueva_fecha)
    assert resp["hora_salida"] == nueva_hora
    # Bogotá a Pereira dura 55 min => llegada 16:55
    assert resp["hora_llegada"] == "16:55:00"

    # Verificar que se creó notificación de afectación (DEC-13)
    notif = NotificacionAfectacion.objects.filter(
        vuelo=vuelo_programado, tipo_afectacion=NotificacionAfectacion.Tipo.REPROGRAMACION
    )
    assert notif.exists()

    # Verificar bitácora
    bitacora = BitacoraVuelo.objects.filter(
        vuelo=vuelo_programado, tipo_evento=BitacoraVuelo.Evento.EDICION
    )
    assert bitacora.exists()


@pytest.mark.django_db
def test_editar_vuelo_costo_exitoso(vuelo_programado, admin_client):
    data = {
        "costo_persona_economica": "195000.00",
        "costo_persona_primera": "290000.00",
    }

    url = f"/api/v1/flights/{vuelo_programado.pk}/"
    response = admin_client.patch(url, data, format="json")
    assert response.status_code == 200
    resp = response.json()

    assert resp["costo_persona_economica"] == "195000.00"
    assert resp["costo_persona_primera"] == "290000.00"

    vuelo_programado.refresh_from_db()
    assert vuelo_programado.costo_persona_economica == Decimal("195000.00")


@pytest.mark.django_db
def test_editar_vuelo_fecha_salida_en_el_pasado_rechazada(vuelo_programado, admin_client):
    data = {
        "fecha_salida": "2020-01-01",
        "hora_salida": "10:00:00",
    }

    url = f"/api/v1/flights/{vuelo_programado.pk}/"
    response = admin_client.patch(url, data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "departure_in_past"


@pytest.mark.django_db
def test_editar_vuelo_inmutabilidad_de_codigo_y_ruta(vuelo_programado, admin_client):
    codigo_original = vuelo_programado.codigo_vuelo
    ruta_original_id = vuelo_programado.ruta_id

    data = {
        "codigo_vuelo": "XX9999",
        "origen_id": 999,
        "costo_persona_economica": "170000.00",
    }

    url = f"/api/v1/flights/{vuelo_programado.pk}/"
    response = admin_client.patch(url, data, format="json")
    assert response.status_code == 200

    vuelo_programado.refresh_from_db()
    assert vuelo_programado.codigo_vuelo == codigo_original
    assert vuelo_programado.ruta_id == ruta_original_id
    assert vuelo_programado.costo_persona_economica == Decimal("170000.00")


@pytest.mark.django_db
def test_editar_vuelo_no_programado_rechazado(vuelo_programado, admin_client):
    vuelo_programado.estado = EstadoVuelo.CANCELADO
    vuelo_programado.save()

    data = {"costo_persona_economica": "180000.00"}
    url = f"/api/v1/flights/{vuelo_programado.pk}/"
    response = admin_client.patch(url, data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "flight_not_editable"


@pytest.mark.django_db
def test_editar_vuelo_denegado_para_no_administrador(vuelo_programado, regular_client, anon_client):
    url = f"/api/v1/flights/{vuelo_programado.pk}/"
    data = {"costo_persona_economica": "180000.00"}

    # Cliente regular
    res = regular_client.patch(url, data, format="json")
    assert res.status_code == 403

    # Anónimo
    res_anon = anon_client.patch(url, data, format="json")
    assert res_anon.status_code in (401, 403)
