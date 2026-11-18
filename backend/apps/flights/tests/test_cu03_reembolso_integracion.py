from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from apps.flights.models import Ciudad, EstadoVuelo
from apps.flights.services import cancelar_vuelo, programar_vuelo
from apps.sales.models import EstadoCompra, EstadoTiquete, Tiquete
from apps.sales.services import comprar_tiquetes
from apps.users.models import User
from apps.wallets.models import MovimientoBilletera, Wallet
from apps.wallets.services import depositar


@pytest.fixture
def cliente_comprador(db):
    user = User.objects.create_user(
        email="comprador.cu03@example.invalid",
        password="password-segura-2026",
        role=User.Role.CLIENTE,
        username="comprador_cu03",
        first_name="Carlos",
        last_name="Comprador",
        document_number="55512345",
        birth_date="1985-05-05",
        birth_place="Bogotá",
        billing_address="Calle 1 # 2-3",
        gender="M",
    )
    user.is_email_verified = True
    user.save()
    wallet, _ = Wallet.objects.get_or_create(user=user)
    depositar(wallet.pk, Decimal("1000000.00"), "Saldo inicial")
    return user


@pytest.mark.django_db
def test_cancelacion_administrativa_vuelo_reembolsa_automaticamente_compras(
    catalogo, admin_user, cliente_comprador
):
    """CU-03 + CU-13 + DEC-09: Al cancelar un vuelo administrativo, todos los tiquetes vendidos

    son reembolsados a la billetera del comprador de forma íntegra e inmediata.
    """
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    # 1. Programar vuelo
    vuelo = programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=6),
        hora_salida=time(14, 0),
        costo_persona_economica=Decimal("180000.00"),
        actor=admin_user,
    )

    # 2. Cliente compra 2 tiquetes
    compra = comprar_tiquetes(
        cliente=cliente_comprador,
        vuelo_id=vuelo.pk,
        clase="ECONOMICA",
        viajeros_data=[
            {
                "documento": "12001",
                "nombres": "Viajero",
                "apellidos": "Uno",
                "fecha_nacimiento": "1990-01-01",
                "correo": "v1@ex.com",
            },
            {
                "documento": "12002",
                "nombres": "Viajero",
                "apellidos": "Dos",
                "fecha_nacimiento": "1995-02-02",
                "correo": "v2@ex.com",
            },
        ],
    )
    assert compra.estado == EstadoCompra.CONFIRMADA
    assert compra.valor_pagado == Decimal("360000.00")

    cliente_comprador.wallet.refresh_from_db()
    saldo_tras_compra = cliente_comprador.wallet.balance
    assert saldo_tras_compra == Decimal("640000.00")

    # 3. Administrador cancela el vuelo (CU-03)
    cancelar_vuelo(
        vuelo_id=vuelo.pk,
        motivo="Falla de motor no programada",
        alternativa="REINTEGRO",
        actor=admin_user,
    )

    # 4. Verificar que el vuelo quedó CANCELADO
    vuelo.refresh_from_db()
    assert vuelo.estado == EstadoVuelo.CANCELADO

    # 5. Verificar que los tiquetes del vuelo quedaron cancelados
    tiquetes = Tiquete.objects.filter(vuelo=vuelo)
    assert all(t.estado == EstadoTiquete.CANCELADO for t in tiquetes)

    # 6. Verificar que la billetera del comprador recibió el reintegro completo (360.000 COP)
    cliente_comprador.wallet.refresh_from_db()
    assert cliente_comprador.wallet.balance == Decimal("1000000.00")

    # Movimiento tipo REEMBOLSO registrado
    mov = MovimientoBilletera.objects.filter(
        wallet=cliente_comprador.wallet, tipo=MovimientoBilletera.Tipo.REEMBOLSO
    ).first()
    assert mov is not None
    assert mov.valor == Decimal("360000.00")
