from django.db import migrations

from apps.flights.catalogo import cargar_catalogo


def poblar_catalogo_inicial(apps, schema_editor):
    cargar_catalogo(apps)


def revertir_catalogo(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("flights", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(poblar_catalogo_inicial, reverse_code=revertir_catalogo),
    ]
