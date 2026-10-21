import pytest
from rest_framework.test import APIClient

from apps.flights.catalogo import cargar_catalogo
from apps.users.models import User

PASSWORD = "admin-password-pruebas-2026"


@pytest.fixture
def catalogo(db):
    cargar_catalogo()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin.vuelos@example.invalid",
        password=PASSWORD,
        role=User.Role.ADMINISTRADOR,
        first_name="Admin",
        last_name="Vuelos",
    )


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        email="cliente.vuelos@example.invalid",
        password=PASSWORD,
        role=User.Role.CLIENTE,
        username="cliente_vuelos",
        first_name="Cliente",
        last_name="Comprador",
        document_number="1234567890",
        birth_date="1990-05-15",
        birth_place="Pereira",
        billing_address="Carrera 1 # 2-3",
        gender="M",
    )


@pytest.fixture
def root_user(db):
    return User.objects.create_root(
        root_id="root-vuelos",
        password=PASSWORD,
        email="root.vuelos@example.invalid",
    )


def obtener_csrf(api_client):
    res = api_client.get("/api/v1/auth/csrf/")
    token = res.json()["csrf_token"]
    api_client.credentials(HTTP_X_CSRFTOKEN=token)
    return token


@pytest.fixture
def admin_client(admin_user):
    client = APIClient(enforce_csrf_checks=True)
    obtener_csrf(client)
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def regular_client(client_user):
    client = APIClient(enforce_csrf_checks=True)
    obtener_csrf(client)
    client.force_authenticate(user=client_user)
    return client


@pytest.fixture
def anon_client():
    client = APIClient(enforce_csrf_checks=True)
    obtener_csrf(client)
    return client
