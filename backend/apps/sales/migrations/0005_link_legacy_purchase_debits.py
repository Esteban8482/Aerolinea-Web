from django.db import migrations


def link_unambiguous_debits(apps, schema_editor):
    Purchase = apps.get_model("sales", "Compra")
    Movement = apps.get_model("wallets", "MovimientoBilletera")
    for purchase in Purchase.objects.filter(debit__isnull=True).iterator():
        matches = list(
            Movement.objects.filter(
                tipo="COMPRA",
                wallet__user_id=purchase.cliente_id,
                valor=purchase.valor_pagado,
                referencia=f"Compra tiquetes localizador {purchase.localizador}",
            ).values_list("pk", flat=True)[:2]
        )
        if len(matches) == 1:
            Purchase.objects.filter(pk=purchase.pk).update(debit_id=matches[0])
    # Ambiguous/missing historical entries remain NULL and fail closed on refunds.
    # Never create money or fabricate payment history to repair an old purchase.


class Migration(migrations.Migration):
    dependencies = [("sales", "0004_tiquete_unique_active_ticket_seat")]
    operations = [migrations.RunPython(link_unambiguous_debits, migrations.RunPython.noop)]
