from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection

from apps.flights.models import Vuelo
from apps.sales.errors import InsufficientSeats
from apps.sales.models import Carrito, Compra, ItemCarrito
from apps.sales.services import agregar_item_carrito, checkout_carrito
from apps.users.models import User
from apps.wallets.models import MovimientoBilletera, Wallet
from apps.wallets.services import depositar


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


def _item_payload(vuelo, viajeros, clase="ECONOMICA"):
    return {
        "vuelo_id": vuelo.pk,
        "clase": clase,
        "tipo_trayecto": "UNICO",
        "viajeros": viajeros,
    }


def _crear_cliente_con_saldo(email, username, document_number, saldo):
    cliente = User.objects.create_user(
        email=email,
        password="password-segura-pruebas-2026",
        role=User.Role.CLIENTE,
        username=username,
        first_name="Cliente",
        last_name="Carrito",
        document_number=document_number,
        birth_date="1993-07-21",
        birth_place="Cali",
        billing_address="Avenida 3 # 12-34",
        gender="F",
    )
    wallet, _ = Wallet.objects.get_or_create(user=cliente)
    depositar(wallet.pk, saldo, "Saldo inicial de prueba")
    cliente.refresh_from_db()
    return cliente


@pytest.mark.django_db
def test_agregar_y_listar_carrito_con_liquidacion(vuelo_nacional, cliente_client):
    r1 = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(vuelo_nacional, [_viajero("9101", "i1@example.com")]),
        format="json",
    )
    assert r1.status_code == 201

    r2 = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(
            vuelo_nacional,
            [
                _viajero("9102", "i2@example.com"),
                _viajero("9103", "i3@example.com"),
            ],
        ),
        format="json",
    )
    assert r2.status_code == 201

    response = cliente_client.get("/api/v1/sales/cart/")
    assert response.status_code == 200
    carrito = response.json()

    assert len(carrito["items"]) == 2
    subtotales = sorted(item["subtotal"] for item in carrito["items"])
    assert subtotales == ["150000.00", "300000.00"]
    assert carrito["total"] == "450000.00"

    item = carrito["items"][0]
    assert item["vuelo"]["codigo_vuelo"] == vuelo_nacional.codigo_vuelo
    assert item["clase"] == "ECONOMICA"
    assert item["num_pasajeros"] == len(item["viajeros"])
    assert item["precio_unitario"] == "150000.00"

    # Agregar al carrito no descuenta cupos del vuelo
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 125


@pytest.mark.django_db
def test_quitar_item_carrito(vuelo_nacional, cliente_client):
    r = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(vuelo_nacional, [_viajero("9201", "q1@example.com")]),
        format="json",
    )
    item_id = r.json()["items"][0]["id"]

    response = cliente_client.delete(f"/api/v1/sales/cart/items/{item_id}/")
    assert response.status_code == 204

    carrito = cliente_client.get("/api/v1/sales/cart/").json()
    assert carrito["items"] == []
    assert carrito["total"] == "0.00"

    # Quitar de nuevo: el item ya no existe
    response = cliente_client.delete(f"/api/v1/sales/cart/items/{item_id}/")
    assert response.status_code == 404
    assert response.json()["code"] == "cart_item_not_found"


@pytest.mark.django_db
def test_agregar_item_valida_cupos_tentativos(vuelo_nacional, cliente_client):
    Vuelo.objects.filter(pk=vuelo_nacional.pk).update(cupos_disponibles_economica=2)

    r1 = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(
            vuelo_nacional,
            [
                _viajero("9301", "t1@example.com"),
                _viajero("9302", "t2@example.com"),
            ],
        ),
        format="json",
    )
    assert r1.status_code == 201

    # El carrito ya acumula 2 de 2 cupos tentativos en económica
    r2 = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(vuelo_nacional, [_viajero("9303", "t3@example.com")]),
        format="json",
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "insufficient_seats"


@pytest.mark.django_db
def test_agregar_item_limite_cinco_contando_reservas(vuelo_nacional, cliente_client):
    # Reserva vigente de 3 tiquetes en el mismo vuelo
    reserva = cliente_client.post(
        "/api/v1/sales/reservations/",
        {
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"940{i}", f"r{i}@example.com") for i in range(3)],
        },
        format="json",
    )
    assert reserva.status_code == 201

    # 3 en reserva + 3 en carrito = 6 > 5
    r1 = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(
            vuelo_nacional,
            [_viajero(f"941{i}", f"c{i}@example.com") for i in range(3)],
        ),
        format="json",
    )
    assert r1.status_code == 400
    assert r1.json()["code"] == "ticket_limit_exceeded"

    # 3 en reserva + 2 en carrito = 5, exactamente en el límite
    r2 = cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(
            vuelo_nacional,
            [_viajero(f"942{i}", f"d{i}@example.com") for i in range(2)],
        ),
        format="json",
    )
    assert r2.status_code == 201


@pytest.mark.django_db
def test_checkout_exitoso_con_debito_unico_del_total(
    vuelo_nacional, cliente_client, cliente_con_billetera
):
    cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(vuelo_nacional, [_viajero("9501", "co1@example.com")]),
        format="json",
    )
    cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(
            vuelo_nacional,
            [
                _viajero("9502", "co2@example.com"),
                _viajero("9503", "co3@example.com"),
            ],
        ),
        format="json",
    )

    response = cliente_client.post("/api/v1/sales/cart/checkout/")
    assert response.status_code == 201
    compras = response.json()
    assert len(compras) == 2

    # Un solo movimiento de débito por el total del carrito
    movimientos = MovimientoBilletera.objects.filter(
        wallet=cliente_con_billetera.wallet, tipo=MovimientoBilletera.Tipo.COMPRA
    )
    assert movimientos.count() == 1
    assert movimientos.first().valor == Decimal("450000.00")

    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == Decimal("1550000.00")

    # Cupos descontados en el checkout y carrito vacío
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 125 - 3
    carrito = cliente_client.get("/api/v1/sales/cart/").json()
    assert carrito["items"] == []

    assert {c["localizador"] for c in compras}
    assert all(c["estado"] == "CONFIRMADA" for c in compras)


@pytest.mark.django_db
def test_checkout_saldo_insuficiente_no_afecta_carrito_ni_cupos(
    vuelo_internacional, cliente_client, cliente_con_billetera
):
    # 2.500.000 COP > saldo disponible de 2.000.000 COP
    cliente_client.post(
        "/api/v1/sales/cart/items/",
        _item_payload(vuelo_internacional, [_viajero("9601", "si1@example.com")]),
        format="json",
    )
    cupos_antes = vuelo_internacional.cupos_disponibles_economica

    response = cliente_client.post("/api/v1/sales/cart/checkout/")
    assert response.status_code == 400
    assert response.json()["code"] == "insufficient_wallet_balance"

    # Carrito intacto
    carrito = cliente_client.get("/api/v1/sales/cart/").json()
    assert len(carrito["items"]) == 1
    assert carrito["total"] == "2500000.00"

    # Cupos y billetera sin cambios
    vuelo_internacional.refresh_from_db()
    assert vuelo_internacional.cupos_disponibles_economica == cupos_antes
    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == Decimal("2000000.00")
    assert (
        MovimientoBilletera.objects.filter(
            wallet=cliente_con_billetera.wallet, tipo=MovimientoBilletera.Tipo.COMPRA
        ).count()
        == 0
    )
    assert Compra.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_checkout_concurrente_por_ultimo_cupo(vuelo_nacional, cliente_con_billetera, catalogo):
    """Dos clientes hacen checkout simultáneo por el último cupo: exactamente uno
    confirma y el rechazado conserva carrito, saldo y cupos intactos."""
    Vuelo.objects.filter(pk=vuelo_nacional.pk).update(cupos_disponibles_economica=1)

    cliente_b = _crear_cliente_con_saldo(
        "cliente.carrito.b@example.invalid",
        "cliente_carrito_b",
        "5556667778",
        Decimal("2000000.00"),
    )

    agregar_item_carrito(
        cliente=cliente_con_billetera,
        vuelo_id=vuelo_nacional.pk,
        clase="ECONOMICA",
        viajeros_data=[_viajero("9701", "cc1@example.com")],
    )
    agregar_item_carrito(
        cliente=cliente_b,
        vuelo_id=vuelo_nacional.pk,
        clase="ECONOMICA",
        viajeros_data=[_viajero("9702", "cc2@example.com")],
    )

    def intentar_checkout(cliente):
        connection.close()
        try:
            checkout_carrito(cliente)
            return "ok"
        except InsufficientSeats:
            return "sin_cupos"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_a = executor.submit(intentar_checkout, cliente_con_billetera)
        futuro_b = executor.submit(intentar_checkout, cliente_b)
        resultados = sorted([futuro_a.result(timeout=15), futuro_b.result(timeout=15)])

    assert resultados == ["ok", "sin_cupos"]

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 0
    assert Compra.objects.count() == 1

    ganador = Compra.objects.get().cliente
    perdedor = cliente_b if ganador.pk == cliente_con_billetera.pk else cliente_con_billetera

    # El carrito del perdedor queda intacto y su billetera sin débito
    carrito_perdedor = Carrito.objects.get(cliente=perdedor)
    assert ItemCarrito.objects.filter(carrito=carrito_perdedor).count() == 1
    perdedor.wallet.refresh_from_db()
    assert perdedor.wallet.balance == Decimal("2000000.00")

    # El carrito del ganador quedó vacío
    carrito_ganador = Carrito.objects.get(cliente=ganador)
    assert ItemCarrito.objects.filter(carrito=carrito_ganador).count() == 0
