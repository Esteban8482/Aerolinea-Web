from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from apps.flights.models import BitacoraVuelo, Ciudad, EstadoVuelo, NotificacionAfectacion
from apps.flights.services import programar_vuelo


@pytest.fixture
def vuelo_para_cancelar(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Cali")
    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=5),
        hora_salida=time(12, 0),
        costo_persona_economica=Decimal("160000.00"),
        actor=admin_user,
    )


@pytest.mark.django_db
def test_cancelar_vuelo_programado_exitoso(vuelo_para_cancelar, admin_client):
    url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    data = {
        "motivo": "Mantenimiento preventivo no programado de la aeronave.",
        "alternativa": "REINTEGRO",
    }

    response = admin_client.post(url, data, format="json")
    assert response.status_code == 200
    resp = response.json()

    assert resp["estado"] == "CANCELADO"
    assert resp["motivo_cancelacion"] == data["motivo"]
    assert resp["cancelado_en"] is not None
    assert resp["cupos_disponibles_primera"] == 0
    assert resp["cupos_disponibles_economica"] == 0

    vuelo_para_cancelar.refresh_from_db()
    assert vuelo_para_cancelar.estado == EstadoVuelo.CANCELADO

    # Verificar que noticias asociadas quedaron inactivas (CU-03)
    assert not vuelo_para_cancelar.noticias.filter(vigente=True).exists()

    # Verificar notificación de afectación (DEC-13)
    notif = NotificacionAfectacion.objects.filter(
        vuelo=vuelo_para_cancelar, tipo_afectacion=NotificacionAfectacion.Tipo.CANCELACION
    )
    assert notif.exists()
    assert notif.first().motivo == data["motivo"]

    # Verificar bitácora de auditoría
    bitacora = BitacoraVuelo.objects.filter(
        vuelo=vuelo_para_cancelar, tipo_evento=BitacoraVuelo.Evento.CANCELACION
    )
    assert bitacora.exists()


@pytest.mark.django_db
def test_cancelar_vuelo_sin_motivo_rechazado(vuelo_para_cancelar, admin_client):
    url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    data = {"motivo": "   "}

    response = admin_client.post(url, data, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_cancelar_vuelo_ya_cancelado_rechazado(vuelo_para_cancelar, admin_client):
    vuelo_para_cancelar.estado = EstadoVuelo.CANCELADO
    vuelo_para_cancelar.save()

    url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    data = {"motivo": "Intento de cancelar vuelo cancelado."}

    response = admin_client.post(url, data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "flight_not_cancellable"


@pytest.mark.django_db
def test_cancelar_vuelo_denegado_para_no_administrador(
    vuelo_para_cancelar, regular_client, anon_client
):
    url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    data = {"motivo": "Intento no autorizado."}

    # Cliente regular
    res = regular_client.post(url, data, format="json")
    assert res.status_code == 403

    # Anónimo
    res_anon = anon_client.post(url, data, format="json")
    assert res_anon.status_code in (401, 403)



@pytest.mark.django_db
def test_cancelar_vuelo_en_estado_realizado_rechazado(vuelo_para_cancelar, admin_client):
    vuelo_para_cancelar.estado = EstadoVuelo.REALIZADO
    vuelo_para_cancelar.save()

    url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    data = {"motivo": "Intento de cancelar vuelo ya realizado."}

    response = admin_client.post(url, data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "flight_not_cancellable"


@pytest.mark.django_db
def test_cancelar_vuelo_inexistente_retorna_404(catalogo, admin_client):
    url = "/api/v1/flights/999999/cancel/"
    data = {"motivo": "Vuelo que no existe."}

    response = admin_client.post(url, data, format="json")
    assert response.status_code == 404
    assert response.json()["code"] == "flight_not_found"


@pytest.mark.django_db
def test_cancelar_vuelo_con_alternativa_reubicacion(vuelo_para_cancelar, admin_client):
    url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    data = {
        "motivo": "Cancelación por mal clima, reubicando pasajeros.",
        "alternativa": "REUBICACION",
    }

    response = admin_client.post(url, data, format="json")
    assert response.status_code == 200
    resp = response.json()
    assert resp["estado"] == "CANCELADO"

    notif = NotificacionAfectacion.objects.get(
        vuelo=vuelo_para_cancelar, tipo_afectacion=NotificacionAfectacion.Tipo.CANCELACION
    )
    assert notif.datos_adicionales.get("alternativa") == "REUBICACION"

    bitacora = BitacoraVuelo.objects.get(
        vuelo=vuelo_para_cancelar, tipo_evento=BitacoraVuelo.Evento.CANCELACION
    )
    assert bitacora.detalles.get("alternativa") == "REUBICACION"


@pytest.mark.django_db
def test_vuelo_cancelado_no_puede_ser_editado(vuelo_para_cancelar, admin_client):
    # Primero cancelamos el vuelo vía API
    cancel_url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/cancel/"
    res_cancel = admin_client.post(cancel_url, {"motivo": "Cancelado antes de editar."}, format="json")
    assert res_cancel.status_code == 200

    # Ahora intentamos editarlo vía PATCH
    edit_url = f"/api/v1/flights/{vuelo_para_cancelar.pk}/"
    res_edit = admin_client.patch(edit_url, {"costo_persona_economica": "200000.00"}, format="json")
    assert res_edit.status_code == 400
    assert res_edit.json()["code"] == "flight_not_editable"


@pytest.mark.django_db
def test_vuelo_cancelado_excluido_de_busqueda_programados_pero_consultable_en_detalle(
    vuelo_para_cancelar, admin_client, anon_client
):
    vuelo_id = vuelo_para_cancelar.pk
    # Cancelar el vuelo
    res_cancel = admin_client.post(
        f"/api/v1/flights/{vuelo_id}/cancel/",
        {"motivo": "Cancelado para exclusión de búsqueda."},
        format="json",
    )
    assert res_cancel.status_code == 200

    # Filtrar vuelos programados: no debe aparecer
    res_list = anon_client.get("/api/v1/flights/?estado=PROGRAMADO")
    assert res_list.status_code == 200
    vuelos_programados = res_list.json()
    assert all(v["id"] != vuelo_id for v in vuelos_programados)

    # Detalle directo: sí es consultable y refleja estado CANCELADO
    res_detail = anon_client.get(f"/api/v1/flights/{vuelo_id}/")
    assert res_detail.status_code == 200
    detalle = res_detail.json()
    assert detalle["id"] == vuelo_id
    assert detalle["estado"] == "CANCELADO"
    assert detalle["motivo_cancelacion"] == "Cancelado para exclusión de búsqueda."
    assert detalle["cupos_disponibles_economica"] == 0
    assert detalle["cupos_disponibles_primera"] == 0
