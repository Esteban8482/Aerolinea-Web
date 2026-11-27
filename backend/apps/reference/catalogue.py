"""Stable form codes; operational states remain owned by their domain models."""

import unicodedata

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


def normalized(value):
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(c)
        ).split()
    )


def seed_options(model=None):
    if model is None:
        from .models import Option

        model = Option
    for category, choices in OPTIONS.items():
        for position, (code, label) in enumerate(choices):
            model.objects.get_or_create(
                category=category, code=code, defaults={"label": label, "position": position}
            )


def validate_option(category, code, field):
    from rest_framework.exceptions import ValidationError

    from .models import Option

    if not Option.objects.filter(category=category, code=code, active=True).exists():
        raise ValidationError({field: "Selecciona una opción vigente del catálogo."})
    return code
