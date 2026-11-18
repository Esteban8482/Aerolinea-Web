from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.flights.catalogo import cargar_catalogo
from apps.flights.models import Ciudad
from apps.flights.services import programar_vuelo
from apps.users.models import User
from apps.wallets.models import Wallet
from apps.wallets.services import depositar

PASSWORD = "password-segura-pruebas-2026"


@pytest.fixture
def catalogo(db):
    cargar_catalogo()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin.sales@example.invalid",
        password=PASSWORD,
        role=User.Role.ADMINISTRADOR,
        first_name="Admin",
        last_name="Sales",
    )


@pytest.fixture
def cliente_con_billetera(db):
    user = User.objects.create_user(
        email="cliente.sales@example.invalid",
        password=PASSWORD,
        role=User.Role.CLIENTE,
        username="cliente_sales",
        first_name="Carlos",
        last_name="Viajero",
        document_number="9876543210",
        birth_date="1988-03-20",
        birth_place="Bogotá",
        billing_address="Calle 50 # 10-20",
        gender="M",
    )
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    wallet, _ = Wallet.objects.get_or_create(user=user)
    # Depositar 2.000.000 COP para pruebas de compra
    depositar(wallet.pk, Decimal("2000000.00"), "Saldo inicial de prueba")
    user.refresh_from_db()
    return user


@pytest.fixture
def cliente_client(cliente_con_billetera):
    client = APIClient()
    client.force_authenticate(user=cliente_con_billetera)
    return client


@pytest.fixture
def vuelo_nacional(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=5),
        hora_salida=time(10, 0),
        costo_persona_economica=Decimal("150000.00"),
        costo_persona_primera=Decimal("220000.00"),
        actor=admin_user,
    )


@pytest.fixture
def vuelo_internacional(catalogo, admin_user):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Madrid")

    return programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=8),
        hora_salida=time(21, 0),
        costo_persona_economica=Decimal("2500000.00"),
        costo_persona_primera=Decimal("4000000.00"),
        actor=admin_user,
    )
