from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import aauthenticate, authenticate
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction

from apps.users.management.commands import create_root as create_root_command
from apps.users.models import User
from apps.users.services import provision_root
from apps.wallets.models import Wallet

PASSWORD = "prueba-larga-con-varias-palabras-2026"


@pytest.fixture
def profile():
    return {
        "username": "viajero",
        "first_name": "Persona",
        "last_name": "De Prueba",
        "document_number": "00123456",
        "birth_date": date(1995, 6, 15),
        "birth_place": "Pereira",
        "billing_address": "Dirección ficticia de pruebas",
        "gender": "dato de prueba",
    }


@pytest.mark.django_db
def test_root_uses_explicit_id_without_profile_or_email():
    root, created = provision_root(root_id="root-01", password=PASSWORD)
    assert created
    assert authenticate(root_id="root-01", password=PASSWORD) == root
    assert authenticate(email="root-01", password=PASSWORD) is None
    assert root.email is None
    assert root.username == ""
    assert not root.is_staff and not root.is_superuser
    assert root.wallet.balance == Decimal("0.00")
    assert root.password.startswith("argon2$argon2id$")
    assert root.password != PASSWORD
    assert str(root) == f"ROOT:{root.pk}"


@pytest.mark.django_db
def test_client_email_and_profile_username_are_independent(profile):
    user = User.objects.create_user(email="Traveler@Example.com", password=PASSWORD, **profile)
    assert user.email == "traveler@example.com"
    assert user.username == "viajero"
    assert authenticate(email="TRAVELER@example.COM", password=PASSWORD) == user
    assert authenticate(email="viajero", password=PASSWORD) is None
    user.email = "Nuevo@Example.com"
    user.save(update_fields=["email"])
    user.refresh_from_db()
    assert user.email == "nuevo@example.com"
    assert user.username == "viajero"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "username",
        "first_name",
        "last_name",
        "document_number",
        "birth_date",
        "birth_place",
        "billing_address",
        "gender",
    ],
)
def test_client_requires_ers_profile_fields(profile, field):
    profile.pop(field)
    with pytest.raises(ValidationError) as error:
        User(email="test@example.com", role=User.Role.CLIENTE, **profile).full_clean(
            exclude=["password"]
        )
    assert field in error.value.message_dict
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_document_can_be_shared_by_different_accounts(profile):
    User.objects.create_user(email="one@example.com", password=PASSWORD, **profile)
    User.objects.create_user(email="two@example.com", password=PASSWORD, **profile)
    assert User.objects.filter(document_number="00123456").count() == 2


@pytest.mark.django_db
def test_administrator_can_complete_profile_later():
    user = User.objects.create_user(
        email="admin@example.com", password=PASSWORD, role="ADMINISTRADOR"
    )
    assert user.username == ""
    assert not user.is_staff and not user.is_superuser
    with pytest.raises(ValidationError):
        User(role="ADMINISTRADOR").full_clean(exclude=["password"])


@pytest.mark.django_db
def test_optional_root_email_is_preserved_and_unique_across_roles():
    root, _ = provision_root(root_id="root-01", password=PASSWORD, email="Root@Example.com")
    assert root.email == "root@example.com"
    with pytest.raises(ValidationError):
        User.objects.create_user(email="ROOT@example.COM", password=PASSWORD, role="ADMINISTRADOR")
    assert authenticate(email="root@example.com", password=PASSWORD) is None


@pytest.mark.django_db
def test_root_id_cannot_shadow_another_accounts_email():
    user = User.objects.create_user(
        email="shared@example.com", password=PASSWORD, role="ADMINISTRADOR"
    )
    root, _ = provision_root(root_id="shared@example.com", password=PASSWORD)
    assert authenticate(email="shared@example.com", password=PASSWORD) == user
    assert authenticate(root_id="shared@example.com", password=PASSWORD) == root
    assert (
        authenticate(email="shared@example.com", root_id="shared@example.com", password=PASSWORD)
        is None
    )
    assert authenticate(root_id="missing", password=PASSWORD) is None
    root.is_active = False
    root.save(update_fields=["is_active"])
    assert authenticate(root_id="shared@example.com", password=PASSWORD) is None


@pytest.mark.django_db
def test_database_rejects_noncanonical_or_duplicate_emails():
    User.objects.create_user(email="admin@example.com", password=PASSWORD, role="ADMINISTRADOR")
    for email in ("ADMIN@example.com", "admin@example.com", " admin@example.com ", ""):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email=email, role="ADMINISTRADOR", password="!")])


@pytest.mark.django_db
def test_business_role_does_not_implicitly_grant_or_forbid_technical_permissions():
    root, _ = provision_root(root_id="root-01", password=PASSWORD)
    assert not root.is_staff and not root.is_superuser
    root.is_staff = True
    root.save(update_fields=["is_staff"])
    root.refresh_from_db()
    assert root.role == User.Role.ROOT
    assert not root.is_superuser


def test_generic_user_creation_cannot_assign_root_role():
    with pytest.raises(ValueError, match="solo admite"):
        User.objects.create_user(email="root@example.com", password=PASSWORD, role=User.Role.ROOT)


@pytest.mark.django_db
def test_create_root_command_is_interactive_and_idempotent(monkeypatch, capsys):
    monkeypatch.setattr(create_root_command, "getpass", lambda prompt: PASSWORD)
    call_command("create_root", root_id="root-01")
    monkeypatch.setattr(
        create_root_command, "getpass", lambda prompt: pytest.fail("No debe pedir clave")
    )
    call_command("create_root", root_id="another-id")
    assert User.objects.count() == Wallet.objects.count() == 1
    output = capsys.readouterr().out
    assert "Ya existe" in output
    assert PASSWORD not in output


@pytest.mark.django_db
def test_root_and_wallet_creation_roll_back_together():
    with patch("apps.users.services.Wallet.objects.create", side_effect=IntegrityError("injected")):
        with pytest.raises(IntegrityError):
            provision_root(root_id="root-01", password=PASSWORD)
    assert User.objects.count() == Wallet.objects.count() == 0


@pytest.mark.django_db
def test_wallet_rejects_duplicates_and_negative_balance():
    root, _ = provision_root(root_id="root-01", password=PASSWORD)
    with pytest.raises(IntegrityError), transaction.atomic():
        Wallet.objects.create(user=root)
    with pytest.raises(IntegrityError), transaction.atomic():
        Wallet.objects.filter(user=root).update(balance=Decimal("-0.01"))
    assert Wallet.objects.get(user=root).balance == Decimal("0.00")


@pytest.mark.django_db(transaction=True)
def test_concurrent_root_bootstrap_creates_one_account_and_wallet(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connections

    barrier = Barrier(2)
    original_clean = User.full_clean

    def synchronized_clean(self, *args, **kwargs):
        original_clean(self, *args, **kwargs)
        barrier.wait(timeout=10)

    def run_bootstrap():
        close_old_connections()
        try:
            root, created = provision_root(root_id="concurrent-root", password=PASSWORD)
            return root.pk, created
        finally:
            connections.close_all()

    monkeypatch.setattr(User, "full_clean", synchronized_clean)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_bootstrap) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert len({pk for pk, _ in results}) == 1
    assert sum(created for _, created in results) == 1
    assert User.objects.count() == Wallet.objects.count() == 1


@pytest.mark.django_db
def test_async_authentication_respects_the_same_identity_rules():
    root, _ = provision_root(root_id="async-root", password=PASSWORD, email="root@example.com")
    user = User.objects.create_user(
        email="async@example.com", password=PASSWORD, role="ADMINISTRADOR"
    )
    assert async_to_sync(aauthenticate)(root_id="async-root", password=PASSWORD) == root
    assert async_to_sync(aauthenticate)(email="root@example.com", password=PASSWORD) is None
    assert async_to_sync(aauthenticate)(email="ASYNC@example.COM", password=PASSWORD) == user
    assert async_to_sync(User.objects.aget_by_natural_key)("ASYNC@example.COM") == user
    with pytest.raises(User.DoesNotExist):
        async_to_sync(User.objects.aget_by_natural_key)("root@example.com")
