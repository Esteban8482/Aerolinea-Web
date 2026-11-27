from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest
from django.core import mail
from django.core.management import call_command
from django.db import connection

from apps.flights.models import EstadoSilla, Vuelo
from apps.sales import services as sales_services
from apps.sales.errors import InsufficientSeats
from apps.sales.models import (
    Compra,
    EstadoCompra,
    EstadoReserva,
    EstadoTiquete,
    NotificacionCompra,
    Tiquete,
)
from apps.sales.services import comprar_tiquetes, resolver_precio_vigente
from apps.users.models import User
from apps.wallets.models import MovimientoBilletera, Wallet
from apps.wallets.services import depositar


@pytest.mark.django_db
def test_compra_directa_exitosa(vuelo_nacional, cliente_client, cliente_con_billetera):
    saldo_inicial = cliente_con_billetera.wallet.balance
    tarifa = vuelo_nacional.costo_persona_economica  # 150000.00

    data = {
        "accepted_total": str(vuelo_nacional.costo_persona_economica * 1),
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "tipo_trayecto": "UNICO",
        "viajeros": [
            {
                "nombre_contacto": "Contacto de prueba",
                "telefono_contacto": "3007654321",
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

    response = cliente_client.post(
        "/api/v1/sales/purchases/",
        data,
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
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
        "accepted_total": str(vuelo_nacional.costo_persona_economica * 1),
        "vuelo_id": vuelo_nacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "genero": "M",
                "telefono": "3001234567",
                "nombre_contacto": "Contacto de prueba",
                "telefono_contacto": "3007654321",
                "documento": "7001",
                "nombres": "Reservador",
                "apellidos": "Uno",
                "fecha_nacimiento": "1988-08-08",
                "correo": "reservador@example.com",
            }
        ],
    }
    res_crear = cliente_client.post(
        "/api/v1/sales/reservations/",
        data_reserva,
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    reserva_id = res_crear.json()["id"]

    vuelo_nacional.refresh_from_db()
    cupos_despues_reserva = vuelo_nacional.cupos_disponibles_economica

    # 2. Convertir reserva en compra
    data_compra = {"accepted_total": "150000.00", "reserva_id": reserva_id}
    res_compra = cliente_client.post(
        "/api/v1/sales/purchases/",
        data_compra,
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
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
        "accepted_total": str(vuelo_internacional.costo_persona_economica * 1),
        "vuelo_id": vuelo_internacional.pk,
        "clase": "ECONOMICA",
        "viajeros": [
            {
                "genero": "M",
                "telefono": "3001234567",
                "nombre_contacto": "Contacto de prueba",
                "telefono_contacto": "3007654321",
                "documento": "8001",
                "nombres": "Viajero",
                "apellidos": "Internacional",
                "fecha_nacimiento": "1990-01-01",
                "correo": "internacional@example.com",
            }
        ],
    }

    response = cliente_client.post(
        "/api/v1/sales/purchases/",
        data,
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "insufficient_wallet_balance"

    # La billetera conserva su saldo intacto
    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == Decimal("2000000.00")


# ---------------------------------------------------------------------------
# Cobertura adicional de brechas HU-013
# ---------------------------------------------------------------------------


def _viajero(documento, correo, nacimiento="1990-01-01"):
    return {
        "nombre_contacto": "Contacto de prueba",
        "telefono_contacto": "3007654321",
        "documento": documento,
        "tipo_documento": "CC",
        "nombres": "Viajero",
        "apellidos": f"Doc{documento}",
        "fecha_nacimiento": nacimiento,
        "genero": "M",
        "telefono": "3001234567",
        "correo": correo,
    }


def _crear_cliente_con_saldo(email, username, document_number, saldo):
    cliente = User.objects.create_user(
        email=email,
        password="password-segura-pruebas-2026",
        role=User.Role.CLIENTE,
        username=username,
        first_name="Cliente",
        last_name="Prueba",
        document_number=document_number,
        birth_date="1993-07-21",
        birth_place="Cali",
        billing_address="Avenida 3 # 12-34",
        gender="F",
    )
    cliente.is_email_verified = True
    cliente.save(update_fields=["is_email_verified"])
    wallet, _ = Wallet.objects.get_or_create(user=cliente)
    depositar(wallet.pk, saldo, "Saldo inicial de prueba")
    cliente.refresh_from_db()
    return cliente


@pytest.mark.django_db(transaction=True)
def test_compra_concurrente_por_ultimo_cupo(vuelo_nacional, cliente_con_billetera, catalogo):
    """Dos clientes compiten por el último cupo: exactamente uno confirma la compra
    y el rechazado conserva su saldo intacto, sin compra ni silla asignada."""
    Vuelo.objects.filter(pk=vuelo_nacional.pk).update(cupos_disponibles_economica=1)

    cliente_b = _crear_cliente_con_saldo(
        "cliente.compra.b@example.invalid",
        "cliente_compra_b",
        "5556667778",
        Decimal("2000000.00"),
    )

    def intentar_compra(cliente, documento):
        connection.close()
        try:
            comprar_tiquetes(
                accepted_total=Decimal("150000.00"),
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
        futuro_a = executor.submit(intentar_compra, cliente_con_billetera, "8101")
        futuro_b = executor.submit(intentar_compra, cliente_b, "8102")
        resultados = sorted([futuro_a.result(timeout=15), futuro_b.result(timeout=15)])

    assert resultados == ["ok", "sin_cupos"]

    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 0
    assert Compra.objects.count() == 1
    assert Tiquete.objects.filter(vuelo=vuelo_nacional, estado=EstadoTiquete.ACTIVO).count() == 1

    # El cliente rechazado no fue debitado ni generó movimiento
    compra = Compra.objects.get(estado=EstadoCompra.CONFIRMADA)
    perdedor = cliente_b if compra.cliente_id == cliente_con_billetera.pk else cliente_con_billetera
    perdedor.wallet.refresh_from_db()
    assert perdedor.wallet.balance == Decimal("2000000.00")
    assert (
        MovimientoBilletera.objects.filter(
            wallet=perdedor.wallet, tipo=MovimientoBilletera.Tipo.COMPRA
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_compra_limite_cinco_tiquetes_acumulados_en_mismo_vuelo(
    vuelo_nacional, cliente_client, cliente_con_billetera
):
    """Máximo 5 tiquetes activos por cliente por vuelo, acumulando compras directas."""
    r1 = cliente_client.post(
        "/api/v1/sales/purchases/",
        {
            "accepted_total": str(vuelo_nacional.costo_persona_economica * 3),
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"820{i}", f"a{i}@example.com") for i in range(3)],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    assert r1.status_code == 201
    cliente_con_billetera.wallet.refresh_from_db()
    saldo_tras_primera = cliente_con_billetera.wallet.balance

    # 3 activos + 3 nuevos = 6 > 5
    r2 = cliente_client.post(
        "/api/v1/sales/purchases/",
        {
            "accepted_total": str(vuelo_nacional.costo_persona_economica * 3),
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"821{i}", f"b{i}@example.com") for i in range(3)],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "ticket_limit_exceeded"

    # Rechazo sin efectos: saldo, cupos y tiquetes sin cambios
    cliente_con_billetera.wallet.refresh_from_db()
    assert cliente_con_billetera.wallet.balance == saldo_tras_primera
    assert Compra.objects.count() == 1
    vuelo_nacional.refresh_from_db()
    assert vuelo_nacional.cupos_disponibles_economica == 125 - 3

    # 3 activos + 2 nuevos = 5, exactamente en el límite
    r3 = cliente_client.post(
        "/api/v1/sales/purchases/",
        {
            "accepted_total": str(vuelo_nacional.costo_persona_economica * 2),
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [_viajero(f"822{i}", f"c{i}@example.com") for i in range(2)],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    assert r3.status_code == 201


@pytest.mark.django_db(transaction=True)
def test_correo_codigo_reserva_enviado_a_cada_viajero(vuelo_nacional, cliente_client):
    """Tras confirmar la compra, cada viajero recibe el localizador, su código de
    tiquete y su silla por correo; el reproceso no duplica envíos."""
    response = cliente_client.post(
        "/api/v1/sales/purchases/",
        {
            "accepted_total": str(vuelo_nacional.costo_persona_economica * 2),
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [
                _viajero("8301", "viajero1@example.com"),
                _viajero("8302", "viajero2@example.com", nacimiento="2015-05-10"),
            ],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    assert response.status_code == 201
    localizador = response.json()["localizador"]

    notificaciones = list(NotificacionCompra.objects.select_related("tiquete"))
    assert len(notificaciones) == 2
    assert {n.recipient for n in notificaciones} == {
        "viajero1@example.com",
        "viajero2@example.com",
    }
    assert all(n.sent_at is None for n in notificaciones)

    out = StringIO()
    call_command("process_purchase_emails", stdout=out)
    assert "Enviados: 2; fallidos: 0." in out.getvalue()

    assert len(mail.outbox) == 2
    codigos = {n.tiquete.codigo_tiquete for n in notificaciones}
    for mensaje in mail.outbox:
        assert localizador in mensaje.body
        assert any(codigo in mensaje.body for codigo in codigos)
        assert mensaje.to[0] in {"viajero1@example.com", "viajero2@example.com"}

    for n in notificaciones:
        n.refresh_from_db()
        assert n.sent_at is not None
        assert n.last_error == ""

    # Reproceso idempotente: no reenvía ni duplica correos
    out = StringIO()
    call_command("process_purchase_emails", stdout=out)
    assert "Enviados: 0; fallidos: 0." in out.getvalue()
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_resolver_precio_vigente_retorna_tarifa_base_por_clase(vuelo_nacional):
    """Hoy (sin HU-004) el precio vigente es la tarifa base del vuelo según la clase."""
    assert resolver_precio_vigente(vuelo_nacional, "ECONOMICA") == Decimal("150000.00")
    assert resolver_precio_vigente(vuelo_nacional, "PRIMERA_CLASE") == Decimal("220000.00")


@pytest.mark.django_db
def test_compra_resuelve_precios_via_resolver_precio_vigente(
    vuelo_nacional, cliente_client, monkeypatch
):
    """La compra obtiene el precio exclusivamente desde resolver_precio_vigente:
    al cambiar su resultado (como hará HU-004 con las promociones), el total
    debitado y el precio_pagado de cada tiquete reflejan ese valor."""
    monkeypatch.setattr(
        sales_services,
        "resolver_precio_vigente",
        lambda vuelo, clase, fecha=None: Decimal("111111.00"),
    )

    response = cliente_client.post(
        "/api/v1/sales/purchases/",
        {
            "accepted_total": "222222.00",
            "vuelo_id": vuelo_nacional.pk,
            "clase": "ECONOMICA",
            "viajeros": [
                _viajero("8401", "precio1@example.com"),
                _viajero("8402", "precio2@example.com"),
            ],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=uuid4().hex,
    )
    assert response.status_code == 201
    res = response.json()
    assert Decimal(str(res["valor_pagado"])) == Decimal("222222.00")
    assert all(Decimal(str(t["precio_pagado"])) == Decimal("111111.00") for t in res["tiquetes"])
