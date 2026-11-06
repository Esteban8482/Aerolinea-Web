import pytest

from apps.flights.models import ClaseTiquete, EstadoSilla, Silla
from apps.sales.models import EstadoCheckin, Tiquete


@pytest.mark.django_db
def test_cambiar_silla_exitoso(vuelo_nacional, cliente_client):
    # 1. Comprar tiquete
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "11001",
                "nombres": "Mateo",
                "apellidos": "Silla",
                "fecha_nacimiento": "1990-01-01",
                "correo": "mateo@example.com",
            }
        ],
    }
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    tiquete_data = res_compra.json()["tiquetes"][0]
    tiquete_id = tiquete_data["id"]
    silla_anterior_id = tiquete_data["silla"]["id"]

    # 2. Consultar mapa de sillas y buscar otra libre de clase económica
    res_map = cliente_client.get(f"/api/v1/sales/flights/{vuelo_nacional.pk}/seats/")
    assert res_map.status_code == 200
    sillas = res_map.json()

    nueva_silla_candidata = next(
        s
        for s in sillas
        if s["clase"] == "ECONOMICA"
        and s["estado"] == "DISPONIBLE"
        and s["id"] != silla_anterior_id
    )

    # 3. Confirmar cambio de silla (CU-17)
    res_cambio = cliente_client.post(
        f"/api/v1/sales/tickets/{tiquete_id}/change-seat/",
        {"nueva_silla_id": nueva_silla_candidata["id"]},
        format="json",
    )
    assert res_cambio.status_code == 200
    res_data = res_cambio.json()
    assert res_data["numero_cambios_silla"] == 1
    assert res_data["silla"]["id"] == nueva_silla_candidata["id"]

    # Silla anterior volvió a DISPONIBLE, nueva quedó OCUPADA
    silla_ant = Silla.objects.get(pk=silla_anterior_id)
    silla_nueva = Silla.objects.get(pk=nueva_silla_candidata["id"])
    assert silla_ant.estado == EstadoSilla.DISPONIBLE
    assert silla_nueva.estado == EstadoSilla.OCUPADA


@pytest.mark.django_db
def test_cambiar_silla_segundo_intento_rechazado(vuelo_nacional, cliente_client):
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "11002",
                "nombres": "Mateo",
                "apellidos": "DobleCambio",
                "fecha_nacimiento": "1990-01-01",
                "correo": "doble@example.com",
            }
        ],
    }
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    tiquete_id = res_compra.json()["tiquetes"][0]["id"]
    silla_actual = res_compra.json()["tiquetes"][0]["silla"]["id"]

    sillas_libres = list(
        Silla.objects.filter(
            vuelo=vuelo_nacional, clase=ClaseTiquete.ECONOMICA, estado=EstadoSilla.DISPONIBLE
        ).exclude(id=silla_actual)
    )

    # Primer cambio: exitoso
    res1 = cliente_client.post(
        f"/api/v1/sales/tickets/{tiquete_id}/change-seat/",
        {"nueva_silla_id": sillas_libres[0].pk},
        format="json",
    )
    assert res1.status_code == 200

    # Segundo cambio: rechazado (RN-15: máximo 1 cambio)
    res2 = cliente_client.post(
        f"/api/v1/sales/tickets/{tiquete_id}/change-seat/",
        {"nueva_silla_id": sillas_libres[1].pk},
        format="json",
    )
    assert res2.status_code == 400
    assert res2.json()["code"] == "seat_change_limit_reached"


@pytest.mark.django_db
def test_cambiar_silla_otra_clase_rechazada(vuelo_nacional, cliente_client):
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "11003",
                "nombres": "Mateo",
                "apellidos": "UpgradeIlegal",
                "fecha_nacimiento": "1990-01-01",
                "correo": "upgrade@example.com",
            }
        ],
    }
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    tiquete_id = res_compra.json()["tiquetes"][0]["id"]

    # Buscar una silla de PRIMERA_CLASE
    silla_primera = Silla.objects.filter(
        vuelo=vuelo_nacional, clase=ClaseTiquete.PRIMERA_CLASE
    ).first()

    res = cliente_client.post(
        f"/api/v1/sales/tickets/{tiquete_id}/change-seat/",
        {"nueva_silla_id": silla_primera.pk},
        format="json",
    )
    assert res.status_code == 400
    assert res.json()["code"] == "seat_not_available"


@pytest.mark.django_db
def test_cambiar_silla_checkin_confirmado_rechazado(vuelo_nacional, cliente_client):
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "11004",
                "nombres": "Mateo",
                "apellidos": "Checkin",
                "fecha_nacimiento": "1990-01-01",
                "correo": "checkin@example.com",
            }
        ],
    }
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    tiquete_id = res_compra.json()["tiquetes"][0]["id"]

    tiquete = Tiquete.objects.get(pk=tiquete_id)
    tiquete.estado_checkin = EstadoCheckin.CONFIRMADO
    tiquete.save()

    otra_silla = Silla.objects.filter(
        vuelo=vuelo_nacional, clase=ClaseTiquete.ECONOMICA, estado=EstadoSilla.DISPONIBLE
    ).exclude(id=tiquete.silla_id).first()

    res = cliente_client.post(
        f"/api/v1/sales/tickets/{tiquete_id}/change-seat/",
        {"nueva_silla_id": otra_silla.pk},
        format="json",
    )
    assert res.status_code == 400
    assert res.json()["code"] == "checkin_already_confirmed"
