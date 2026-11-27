"""Shared authorization, traveler and inventory rules (DEC-07/08/09/10)."""

from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.flights.models import ClaseTiquete, EstadoVuelo
from apps.users.models import User

from .errors import (
    AdultPassengerRequired,
    DuplicatePassengerInFlight,
    FlightNotAvailableForSale,
    TicketLimitExceeded,
)
from .models import EstadoReserva, EstadoTiquete, ReservaViajero, TipoTrayecto, Tiquete, Viajero


def client_required(actor, *, require_verified=True):
    if (
        not actor
        or not actor.is_authenticated
        or not actor.is_active
        or actor.role != User.Role.CLIENTE
    ):
        raise PermissionDenied()
    if require_verified and not actor.is_email_verified:
        raise PermissionDenied("Verifica tu correo electrónico.", code="email_not_verified")


def administrator_required(actor):
    if (
        not actor
        or not actor.is_authenticated
        or not actor.is_active
        or actor.role != User.Role.ADMINISTRADOR
    ):
        raise PermissionDenied()


def owned(queryset, actor, **lookup):
    obj = queryset.filter(**lookup).first()
    if obj is None or obj.cliente_id != actor.pk:
        raise NotFound()
    return obj


def money(value):
    try:
        result = Decimal(str(value))
        if (
            not result.is_finite()
            or result <= 0
            or result >= Decimal("1000000000000")
            or result != result.quantize(Decimal(".01"))
        ):
            raise ValueError
    except (ValueError, ArithmeticError):
        raise ValidationError(
            {"amount": "Indica un valor positivo con máximo dos decimales."}
        ) from None
    return result


def identity(data):
    return str(data.get("tipo_documento", "CC")).strip().upper(), str(
        data["documento"]
    ).strip().upper()


def itinerary(flights, trip, now):
    if trip not in TipoTrayecto.values or (trip == TipoTrayecto.COMPLETO) != (len(flights) == 2):
        raise ValidationError(
            {"tipo_trayecto": "El trayecto debe corresponder a los vuelos indicados."}
        )
    if len({f.pk for f in flights}) != len(flights):
        raise ValidationError({"vuelo_regreso_id": "Ida y regreso deben ser vuelos distintos."})
    for flight in flights:
        if (
            flight.estado != EstadoVuelo.PROGRAMADO
            or flight.salida_utc <= now
            or not flight.ruta.activa
            or not flight.ruta.origen.activa
            or not flight.ruta.destino.activa
        ):
            raise FlightNotAvailableForSale()
    if len(flights) == 2:
        a, b = flights
        if (
            a.ruta.origen_id != b.ruta.destino_id
            or a.ruta.destino_id != b.ruta.origen_id
            or b.salida_utc <= a.llegada_utc
        ):
            raise ValidationError(
                {
                    "vuelo_regreso_id": "El regreso debe invertir la ruta y salir "
                    "después de la llegada."
                }
            )


def travelers(data, flights, actor, now, exclude_reservation=None):
    if not 1 <= len(data) <= 5:
        raise TicketLimitExceeded()
    identities = [identity(item) for item in data]
    if len(set(identities)) != len(identities):
        raise DuplicatePassengerInFlight()
    for item in data:
        from apps.reference.catalogue import validate_option

        validate_option("document_type", identity(item)[0], "tipo_documento")
        validate_option("gender", item.get("genero"), "genero")
        required = [
            "documento",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "genero",
            "telefono",
            "correo",
            "nombre_contacto",
            "telefono_contacto",
        ]
        if any(not item.get(field) for field in required):
            raise ValidationError(
                {"viajeros": "Completa identidad, contacto y contacto de emergencia."}
            )
        birth = item["fecha_nacimiento"]
        if isinstance(birth, str):
            birth = date.fromisoformat(birth)
        if birth > timezone.localdate(now):
            raise ValidationError(
                {"fecha_nacimiento": "La fecha de nacimiento no puede estar en el futuro."}
            )
    for flight in flights:
        if not any(
            Viajero(fecha_nacimiento=item["fecha_nacimiento"]).es_mayor_de_edad(flight.fecha_salida)
            for item in data
        ):
            raise AdultPassengerRequired()
        reservations = ReservaViajero.objects.filter(
            reserva__estado=EstadoReserva.VIGENTE, reserva__limite_vigencia__gt=now
        ).filter(Q(reserva__vuelo=flight) | Q(reserva__vuelo_regreso=flight))
        if exclude_reservation:
            reservations = reservations.exclude(reserva_id=exclude_reservation)
        tickets = Tiquete.objects.filter(vuelo=flight, estado=EstadoTiquete.ACTIVO)
        if (
            reservations.filter(reserva__cliente=actor).count()
            + tickets.filter(compra__cliente=actor).count()
            + len(data)
            > 5
        ):
            raise TicketLimitExceeded()
        for kind, number in identities:
            if (
                reservations.filter(
                    viajero__tipo_documento__iexact=kind, viajero__documento__iexact=number
                ).exists()
                or tickets.filter(
                    viajero__tipo_documento__iexact=kind, viajero__documento__iexact=number
                ).exists()
            ):
                raise DuplicatePassengerInFlight()


def capacity_field(clase):
    if clase not in ClaseTiquete.values:
        raise ValidationError({"clase": "Clase inválida."})
    return (
        "cupos_disponibles_primera"
        if clase == ClaseTiquete.PRIMERA_CLASE
        else "cupos_disponibles_economica"
    )
