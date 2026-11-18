from datetime import timedelta

import pytest
from django.utils import timezone

from apps.flights.models import EstadoSilla
from apps.sales.models import EstadoCompra
from apps.wallets.models import MovimientoBilletera


@pytest.mark.django_db
def test_cancelar_compra_voluntaria_reembolso_exitoso(
    vuelo_nacional, cliente_client, cliente_con_billetera
):
    saldo_inicial = cliente_con_billetera.wallet.balance
    tarifa = vuelo_nacional.costo_persona_economica

    # 1. Realizar compra
    data_compra = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "9001",
                "nombres": "Ana",
                "apellidos": "Reembolso",
                "fecha_nacimiento": "1994-04-10",
                "correo": "ana@example.com",
            }
        ],
    }
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data_compra, format="json")
    compra_id = res_compra.json()["id"]
    silla_id = res_compra.json()["tiquetes"][0]["silla"]["id"]

    # 2. Cancelar compra
    res_cancel = cliente_client.post(f"/api/v1/sales/purchases/{compra_id}/cancel/")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["estado"] == EstadoCompra.CANCELADA

    # 3. Saldo reembolsado a la billetera (DEC-09)
    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == saldo_inicial

    mov_reembolso = MovimientoBilletera.objects.filter(
        wallet=cliente_con_billetera.wallet, tipo=MovimientoBilletera.Tipo.REEMBOLSO
    ).first()
    assert mov_reembolso is not None
    assert mov_reembolso.valor == tarifa

    # 4. Silla liberada
    from apps.flights.models import Silla
    silla = Silla.objects.get(pk=silla_id)
    assert silla.estado == EstadoSilla.DISPONIBLE


@pytest.mark.django_db
def test_cancelar_compra_fuera_de_plazo_rechazada(vuelo_nacional, cliente_client):
    # 1. Comprar tiquete
    data = {
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "documento": "9002",
                "nombres": "Pedro",
                "apellidos": "Tarde",
                "fecha_nacimiento": "1991-01-01",
                "correo": "pedro@example.com",
            }
        ],
    }
    res_compra = cliente_client.post("/api/v1/sales/purchases/", data, format="json")
    compra_id = res_compra.json()["id"]

    # Modificar salida del vuelo a 30 minutos desde ahora (menos del margen de 1 hora)
    vuelo_nacional.salida_utc = timezone.now() + timedelta(minutes=30)
    vuelo_nacional.save()

    # 2. Intentar cancelar
    res_cancel = cliente_client.post(f"/api/v1/sales/purchases/{compra_id}/cancel/")
    assert res_cancel.status_code == 400
    assert res_cancel.json()["code"] == "cancellation_window_closed"

