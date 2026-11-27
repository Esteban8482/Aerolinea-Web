from django.db import migrations

OPTIONS = {
    "gender": [
        ("F", "Femenino"),
        ("M", "Masculino"),
        ("OTRO", "Otro"),
        ("NO_INFORMA", "Prefiero no informar"),
    ],
    "document_type": [
        ("CC", "Cédula de ciudadanía"),
        ("TI", "Tarjeta de identidad"),
        ("CE", "Cédula de extranjería"),
        ("PASAPORTE", "Pasaporte"),
        ("RC", "Registro civil"),
        ("PPT", "Permiso por Protección Temporal"),
        ("OTRO", "Otro documento"),
    ],
    "travel_class": [("ECONOMICA", "Clase económica"), ("PRIMERA_CLASE", "Primera clase")],
    "trip_type": [("UNICO", "Solo ida"), ("COMPLETO", "Ida y regreso")],
    "flight_type": [("NACIONAL", "Nacional"), ("INTERNACIONAL", "Internacional")],
    "payment_method_type": [
        ("TARJETA", "Tarjeta simulada"),
        ("CUENTA_BANCARIA", "Cuenta bancaria simulada"),
    ],
    "relocation_decision": [("ACCEPT", "Aceptar reubicación"), ("REFUND", "Solicitar reembolso")],
    "cancellation_alternative": [("REINTEGRO", "Reintegro"), ("REUBICACION", "Reubicación")],
}


def seed(apps, schema_editor):
    model = apps.get_model("reference", "Option")
    for category, choices in OPTIONS.items():
        for position, (code, label) in enumerate(choices):
            model.objects.using(schema_editor.connection.alias).get_or_create(
                category=category, code=code, defaults={"label": label, "position": position}
            )


class Migration(migrations.Migration):
    dependencies = [("reference", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
