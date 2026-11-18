from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from apps.flights.models import Vuelo
from apps.sales.errors import InsufficientSeats
from apps.sales.models import EstadoReserva, Reserva
from apps.sales.services import crear_reserva


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


# ---------------------------------------------------------------------------
# Cobertura adicional de brechas HU-012
# ---------------------------------------------------------------------------


def _viajero(documento, correo, nacimiento="1990-01-01"):
    return {
        "documento": documento,
        "tipo_documento": "CC",
        "nombres": "Viajero",
        "apellidos": f"Doc{documento}",
        "fecha_nacimiento": nacimiento,
        "genero": "M",
        "telefono": "3001234567",
        "correo": correo,
    }


@pytest.mark.django_db
def test_crear_reserva_viajero_ya_reservado_en_mismo_vuelo_rechazada(
    vuelo_nacional, cliente_client
):
    """Una misma persona no puede figurar dos veces como viajera en el mismo vuelo,
    aunque sea en reservas distintas."""
    r1 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero("7101", "uno@example.com")],
        },
        format="json",
    )
    assert r1.status_code == 201

    r2 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [
                _viajero("7101", "repetido@example.com"),
                _viajero("7102", "dos@example.com"),
            ],
        },
        format="json",
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "duplicate_passenger_in_flight"


@pytest.mark.django_db
def test_crear_reserva_limite_cinco_tiquetes_acumulados_en_mismo_vuelo(
    vuelo_nacional, cliente_client
):
    """Máximo 5 tiquetes por cliente por vuelo, acumulando reservas vigentes."""
    r1 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"720{i}", f"a{i}@example.com") for i in range(3)],
        },
        format="json",
    )
    assert r1.status_code == 201

    # 3 vigentes + 3 nuevos = 6 > 5
    r2 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"721{i}", f"b{i}@example.com") for i in range(3)],
        },
        format="json",
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "ticket_limit_exceeded"

    # 3 vigentes + 2 nuevos = 5, exactamente en el límite
    r3 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"722{i}", f"c{i}@example.com") for i in range(2)],
        },
        format="json",
    )
    assert r3.status_code == 201


@pytest.mark.django_db
def test_ventana_reserva_nacional_cierra_una_hora_antes(vuelo_nacional, cliente_client):
    """Vuelo nacional: no se puede reservar a menos de 1 hora de la salida (DEC-07)."""
    vuelo_nacional.salida_utc = timezone.now() + timedelta(minutes=30)
    vuelo_nacional.save()

    response = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero("7301", "nacional@example.com")],
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "reservation_window_closed"


@pytest.mark.django_db
def test_ventana_reserva_internacional_cierra_tres_horas_antes(vuelo_internacional, cliente_client):
    """Vuelo internacional: no se puede reservar a menos de 3 horas de la salida (DEC-07)."""
    vuelo_internacional.salida_utc = timezone.now() + timedelta(hours=2)
    vuelo_internacional.save()

    response = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_internacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero("7401", "internacional@example.com")],
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "reservation_window_closed"


@pytest.mark.django_db
def test_limite_vigencia_reserva_segun_tipo_de_vuelo(
    vuelo_nacional, vuelo_internacional, cliente_client
):
    """La vigencia es min(now + 24 h, salida - margen): 1 h nacional, 3 h internacional."""
    ahora = timezone.now()

    vuelo_nacional.salida_utc = ahora + timedelta(hours=20)
    vuelo_nacional.save()
    r_nac = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero("7501", "lim-nac@example.com")],
        },
        format="json",
    )
    assert r_nac.status_code == 201
    reserva_nac = Reserva.objects.get(pk=r_nac.json()["id"])
    esperado_nac = vuelo_nacional.salida_utc - timedelta(hours=1)
    assert abs((reserva_nac.limite_vigencia - esperado_nac).total_seconds()) < 2

    vuelo_internacional.salida_utc = ahora + timedelta(hours=20)
    vuelo_internacional.save()
    r_int = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_internacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero("7502", "lim-int@example.com")],
        },
        format="json",
    )
    assert r_int.status_code == 201
    reserva_int = Reserva.objects.get(pk=r_int.json()["id"])
    esperado_int = vuelo_internacional.salida_utc - timedelta(hours=3)
    assert abs((reserva_int.limite_vigencia - esperado_int).total_seconds()) < 2


@pytest.mark.django_db
def test_command_liberar_reservas_vencidas_devuelve_cupos_e_idempotente(
    vuelo_nacional, cliente_client
):
    cupos_base = vuelo_nacional.cupos_disponibles_economica

    # Reserva que quedará vencida (2 cupos)
    r1 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [
                _viajero("7601", "vencida1@example.com"),
                _viajero("7602", "vencida2@example.com", nacimiento="2015-05-10"),
            ],
        },
        format="json",
    )
    assert r1.status_code == 201
    reserva_vencida_id = r1.json()["id"]

    # Reserva que sigue vigente (1 cupo)
    r2 = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero("7603", "vigente@example.com")],
        },
        format="json",
    )
    assert r2.status_code == 201
    reserva_vigente_id = r2.json()["id"]

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_base - 3

    # Forzar el vencimiento de la primera reserva
    Reserva.objects.filter(pk=reserva_vencida_id).update(
        limite_vigencia=timezone.now() - timedelta(minutes=1)
    )

    out = StringIO()
    call_command("liberar_reservas_vencidas", stdout=out)
    assert "Reservas liberadas: 1" in out.getvalue()

    reserva_vencida = Reserva.objects.get(pk=reserva_vencida_id)
    assert reserva_vencida.estado == EstadoReserva.VENCIDA
    reserva_vigente = Reserva.objects.get(pk=reserva_vigente_id)
    assert reserva_vigente.estado == EstadoReserva.VIGENTE

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_base - 1

    # Segunda ejecución: no libera nada ni altera los cupos (idempotente)
    out = StringIO()
    call_command("liberar_reservas_vencidas", stdout=out)
    assert "Reservas liberadas: 0" in out.getvalue()

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_base - 1
    reserva_vencida.refresh_from_db()
    assert reserva_vencida.estado == EstadoReserva.VENCIDA


@pytest.mark.django_db(transaction=True)
def test_reservas_concurrentes_por_ultimo_cupo(vuelo_nacional, cliente_con_billetera, catalogo):
    """Dos clientes compiten por el último cupo: solo uno confirma la reserva
    y el contador nunca queda negativo (select_for_update + transacción)."""
    from apps.users.models import User

    Vuelo.objects.filter(pk=vuelo_nacional.pk).update(cupos_disponibles_economica=1)

    cliente_b = User.objects.create_user(
        email="cliente.concurrente@example.invalid",
        password="password-segura-pruebas-2026",
        role=User.Role.CLIENTE,
        username="cliente_concurrente",
        first_name="Cliente",
        last_name="Concurrente",
        document_number="5556667778",
        birth_date="1993-07-21",
        birth_place="Cali",
        billing_address="Avenida 3 # 12-34",
        gender="F",
    )

    def intentar_reserva(cliente, documento):
        connection.close()
        try:
            crear_reserva(
                cliente=cliente,
                vuelo_id=vuelo_nacional.pk,
                clase="ECONOMICA",
                viajeros_data=[_viajero(documento, f"{documento}@example.com")],
            )
            return "ok"
        except InsufficientSeats:
            return "sin_cupos"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_a = executor.submit(intentar_reserva, cliente_con_billetera, "7701")
        futuro_b = executor.submit(intentar_reserva, cliente_b, "7702")
        resultados = sorted([futuro_a.result(timeout=15), futuro_b.result(timeout=15)])

    assert resultados == ["ok", "sin_cupos"]

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 0
    assert Reserva.objects.filter(vuelo=vuelo_nacional, estado=EstadoReserva.VIGENTE).count() == 1
