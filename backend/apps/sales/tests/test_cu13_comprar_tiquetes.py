from decimal import Decimal

import pytest

from apps.flights.models import EstadoSilla
from apps.sales.models import EstadoReserva
from apps.wallets.models import MovimientoBilletera


@pytest.mark.django_db
def test_compra_directa_exitosa(vuelo_nacional, cliente_client, cliente_con_billetera):
    saldo_inicial = cliente_con_billetera.wallet.balance
    tarifa = vuelo_nacional.costo_persona_economica  # 150000.00

    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "tipo_trayecto": "UNICO",
        "viajeros": [
            {
                "documento": "6001",
                "tipo_documento": "CC",
                "nombres": "Viajero",
                "apellidos": "Comprador",
                "fecha_nacimiento": "1992-06-15",
                "genero": "M",
                "telefono": "3001234567",
                "correo": "viajero@example.com",
            }
        ],
    }

    response = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    assert response.status_code == 201
    res = response.json()

    # 1. Localizador de 6 caracteres (DEC-02)
    assert len(res["localizador"]) == 6
    assert res["estado"] == "CONFIRMADA"
    assert Decimal(str(res["valor_pagado"])) == tarifa

    # 2. Débito en billetera (DEC-03, DEC-09)
    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == saldo_inicial - tarifa

    movimiento = MovimientoBilletera.objects.filter(wallet=cliente_con_billetera.wallet).first()
    assert movimiento.tipo == MovimientoBilletera.Tipo.COMPRA
    assert movimiento.valor == tarifa

    # 3. Asignación de silla (DEC-08)
    assert len(res["tiquetes"]) == 1
    tiquete_data = res["tiquetes"][0]
    assert tiquete_data["silla"]["estado"] == EstadoSilla.OCUPADA
    assert Decimal(str(tiquete_data["precio_pagado"])) == tarifa


@pytest.mark.django_db
def test_compra_desde_reserva_exitosa(vuelo_nacional, cliente_client, cliente_con_billetera):
    # 1. Crear reserva previa
    data_reserva = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "7001",
                "nombres": "Reservador",
                "apellidos": "Uno",
                "fecha_nacimiento": "1988-08-08",
                "correo": "reservador@example.com",
            }
        ],
    }
    res_crear = cliente_client.post("/api/v1/sales/reservations/", data_reserva, format="json")
    reserva_id = res_crear.json()["id"]

    vuelo_nacional.refresh_from_db()
    cupos_despues_reserva = vuelo_nacional.cupos_disponibles_economica

    # 2. Convertir reserva en compra
    data_compra = {"reserva_id": reserva_id}
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data_compra, format="json")
    assert res_compra.status_code == 201

    # Verificar que el vuelo no perdió cupos adicionales
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == cupos_despues_reserva

    # Verificar estado de la reserva convertida
    from apps.sales.models import Reserva

    reserva = Reserva.objects.get(pk=reserva_id)
    assert reserva.estado == EstadoReserva.COMPRADA


@pytest.mark.django_db
def test_compra_saldo_insuficiente_rechazada(
    vuelo_internacional, cliente_client, cliente_con_billetera
):
    # El vuelo internacional cuesta 2.500.000 COP por persona en económica
    # La billetera tiene 2.000.000 COP
    data = {
        "vuelo_id": vuelo_internacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "8001",
                "nombres": "Viajero",
                "apellidos": "Internacional",
                "fecha_nacimiento": "1990-01-01",
                "correo": "internacional@example.com",
            }
        ],
    }

    response = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "insufficient_wallet_balance"

    # La billetera conserva su saldo intacto
    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == Decimal("2000000.00")
