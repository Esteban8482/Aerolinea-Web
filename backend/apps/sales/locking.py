"""Shared transaction boundary for inventory-changing workflows.

The transaction-scoped PostgreSQL lock serializes cross-flight operations, including
round trips and administrative changes. Wallet-only operations never acquire this
lock. This deliberately favors correctness over parallel inventory throughput.
"""

from functools import wraps

from django.db import connection, transaction


def inventory_transaction(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with transaction.atomic():
            if connection.vendor != "postgresql":
                raise RuntimeError("Inventory workflows require PostgreSQL.")
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [7140301])
            return function(*args, **kwargs)

    return wrapped
