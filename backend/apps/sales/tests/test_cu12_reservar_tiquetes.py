from datetime import timedelta

import pytest
from django.utils import timezone

from apps.sales.models import Reserva


@pytest.mark.django_db
def test_crear_reserva_nacional_exitosa(vuelo_nacional, cliente_client, cliente_con_billetera):
    cupos_iniciales = vuelo_nacional.cupos_disponibles_economica

    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "tipo_trayecto": "UNICO",
        "viajeros": [
            {
                "documento": "1001",
                "tipo_documento": "CC",
                "nombres": "Juan",
                "apellidos": "Pérez",
                "fecha_nacimiento": "1990-01-01",
                "genero": "M",
                "telefono": "3001234567",
                "correo": "juan@example.com",
            },
            {
                "documento": "1002",
                "tipo_documento": "TI",
                "nombres": "Pedro",
                "apellidos": "Pérez",
                "fecha_nacimiento": "2015-05-10",
                "genero": "M",
                "telefono": "3001234567",
                "correo": "pedro@example.com",
            },
        ],
    }

    response = cliente_client.post("/api/v1/sales/reservations/", data, format="json")
    assert response.status_code == 201
    res = response.json()

    assert res["estado"] == "VIGENTE"
    assert len(res["viajeros"]) == 2

    # Verificar descuento de cupos en el vuelo (DEC-08)
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_iniciales - 2

    # Verificar vigencia máxima de 24 horas (DEC-07)
    reserva = Reserva.objects.get(pk=res["id"])
    assert reserva.limite_vigencia <= timezone.now() + timedelta(hours=24, minutes=1)


@pytest.mark.django_db
def test_crear_reserva_sin_adulto_rechazada(vuelo_nacional, cliente_client):
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "2001",
                "tipo_documento": "TI",
                "nombres": "Menor",
                "apellidos": "Uno",
                "fecha_nacimiento": "2016-01-01",
                "genero": "M",
                "telefono": "3001234567",
                "correo": "menor@example.com",
            }
        ],
    }

    response = cliente_client.post("/api/v1/sales/reservations/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "adult_passenger_required"


@pytest.mark.django_db
def test_crear_reserva_viajero_duplicado_rechazada(vuelo_nacional, cliente_client):
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "3001",
                "nombres": "Adulto",
                "apellidos": "Uno",
                "fecha_nacimiento": "1990-01-01",
                "correo": "adulto@example.com",
            },
            {
                "documento": "3001",
                "nombres": "Adulto",
                "apellidos": "Repetido",
                "fecha_nacimiento": "1990-01-01",
                "correo": "adulto@example.com",
            },
        ],
    }

    response = cliente_client.post("/api/v1/sales/reservations/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "duplicate_passenger_in_flight"


@pytest.mark.django_db
def test_crear_reserva_limite_tiquetes_cliente_excedido(vuelo_nacional, cliente_client):
    # Intentar reservar 6 pasajeros (máximo 5)
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": f"400{i}",
                "nombres": f"V{i}",
                "apellidos": "T",
                "fecha_nacimiento": "1990-01-01",
                "correo": f"v{i}@ex.com",
            }
            for i in range(6)
        ],
    }

    response = cliente_client.post("/api/v1/sales/reservations/", data, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_cancelar_reserva_voluntaria_devuelve_cupos(vuelo_nacional, cliente_client):
    cupos_base = vuelo_nacional.cupos_disponibles_economica

    # 1. Crear reserva
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "5001",
                "nombres": "Adulto",
                "apellidos": "Cancelar",
                "fecha_nacimiento": "1985-05-05",
                "correo": "cancelar@example.com",
            }
        ],
    }
    creacion = cliente_client.post("/api/v1/sales/reservations/", data, format="json")
    reserva_id = creacion.json()["id"]

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_base - 1

    # 2. Cancelar reserva
    cancel_res = cliente_client.post(f"/api/v1/sales/reservations/{reserva_id}/cancel/")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["estado"] == "CANCELADA"

    # Cupo devuelto
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_base
