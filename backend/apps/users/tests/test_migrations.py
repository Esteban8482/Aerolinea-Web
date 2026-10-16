from uuid import uuid4

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_upgrade_preserves_initial_accounts_and_adds_zero_wallets():
    # Esquema efímero dentro de la base de pytest; no altera el volumen de desarrollo.
    schema = connection.ops.quote_name("migration_audit_" + uuid4().hex)
    with connection.cursor() as cursor:
        cursor.execute("SHOW search_path")
        original_search_path = cursor.fetchone()[0]
        cursor.execute(f"CREATE SCHEMA {schema}")
        cursor.execute(f"SET search_path TO {schema}")
    try:
        executor = MigrationExecutor(connection)
        before = [("users", "0001_initial")]
        executor.migrate(before)
        User = executor.loader.project_state(before).apps.get_model("users", "User")
        root = User.objects.create(username="previous-root-id", role="ROOT", email="", password="!")
        email = "long-address-from-initial-implementation@example.invalid"
        account = User.objects.create(
            username=email, email=email, role="ADMINISTRADOR", first_name="Existing", password="!"
        )
        executor = MigrationExecutor(connection)
        after = executor.loader.graph.leaf_nodes()
        executor.migrate(after)
        state = executor.loader.project_state(after)
        User = state.apps.get_model("users", "User")
        Wallet = state.apps.get_model("wallets", "Wallet")
        migrated_root = User.objects.get(pk=root.pk)
        migrated_account = User.objects.get(pk=account.pk)
        assert migrated_root.root_id == "previous-root-id"
        assert migrated_root.email is None
        assert migrated_root.password == "!"
        assert migrated_account.email == email
        assert migrated_account.first_name == "Existing"
        assert migrated_account.username == ""
        assert migrated_account.password == "!"
        assert Wallet.objects.count() == 2
        assert not Wallet.objects.exclude(balance=0).exists()
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('search_path', %s, false)", [original_search_path])
            cursor.execute(f"DROP SCHEMA {schema} CASCADE")
