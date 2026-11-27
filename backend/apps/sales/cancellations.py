"""Purchaser-directed, atomic resolution of an airline cancellation (DEC-29)."""

from collections import Counter
from decimal import Decimal
from urllib.parse import urlsplit

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.flights.errors import FlightNotCancellable, FlightNotFound
from apps.flights.models import BitacoraVuelo, EstadoSilla, EstadoVuelo, Silla, Vuelo

from .events import audit, notify
from .locking import inventory_transaction
from .models import (
    CancellationResolution,
    EstadoCheckin,
    EstadoReserva,
    EstadoTiquete,
    JourneyNotification,
    Reserva,
    Tiquete,
)
from .rules import administrator_required, capacity_field, client_required
from .services import (
    _change_capacity,
    _refund_ticket,
    _release,
    contar_tiquetes_activos_cliente_en_vuelo,
)


class ResolutionConflict(APIException):
    status_code = 409
    default_code = "cancellation_resolution_conflict"
    default_detail = "La operación cambió. Consulta las alternativas y confirma nuevamente."


def management_link(resolution):
    base = settings.CANCELLATION_FRONTEND_URL
    parsed = urlsplit(base)
    if (
        not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.scheme not in ("http", "https")
        or (not settings.DEBUG and parsed.scheme != "https")
    ):
        raise ValidationError("La URL de gestión de cancelaciones no está configurada.")
    return f"{base.rstrip('/')}/{resolution.pk}"


@inventory_transaction
def cancel(actor, flight_id, reason, origin=""):
    administrator_required(actor)
    if not reason or len(reason.strip()) < 3:
        raise ValidationError({"motivo": "Indica el motivo de cancelación."})
    flight = Vuelo.objects.select_for_update().filter(pk=flight_id).first()
    if flight is None:
        raise FlightNotFound()
    if flight.estado == EstadoVuelo.CANCELADO:
        return flight
    if flight.estado != EstadoVuelo.PROGRAMADO or flight.salida_utc <= timezone.now():
        raise FlightNotCancellable()
    now = timezone.now()
    for reservation in Reserva.objects.filter(estado=EstadoReserva.VIGENTE).filter(
        Q(vuelo=flight) | Q(vuelo_regreso=flight)
    ):
        _release(reservation, EstadoReserva.CANCELADA)
        notify(
            [reservation.cliente.email],
            "Reserva cancelada",
            f"Reserva {reservation.pk}: vuelo {flight.codigo_vuelo} cancelado. "
            "Se liberó el itinerario sin cargo.",
        )
    tickets = list(
        Tiquete.objects.filter(vuelo=flight, estado=EstadoTiquete.ACTIVO).select_related(
            "compra__cliente", "viajero"
        )
    )
    groups = {}
    for ticket in tickets:
        if ticket.compra_id not in groups:
            resolution = CancellationResolution.objects.create(
                purchase=ticket.compra, flight=flight
            )
            groups[ticket.compra_id] = resolution
            notify(
                [ticket.compra.cliente.email],
                "Gestiona la cancelación de tu vuelo",
                f"Tu vuelo {flight.codigo_vuelo} ha sido cancelado. Lamentamos los inconvenientes. "
                f"Selecciona reubicación sin cargo o reembolso: {management_link(resolution)}. "
                "Inicia sesión con la cuenta compradora para continuar.",
            )
            ticket.compra.disrupted = True
            ticket.compra.save(update_fields=["disrupted"])
        ticket.cancellation_resolution = groups[ticket.compra_id]
        ticket.estado = EstadoTiquete.PENDIENTE_RESOLUCION
        ticket.estado_checkin = EstadoCheckin.PENDIENTE
        ticket.fecha_checkin = None
        ticket.save(
            update_fields=["cancellation_resolution", "estado", "estado_checkin", "fecha_checkin"]
        )
        JourneyNotification.objects.filter(
            ticket=ticket, boarding_pass=True, sent_at__isnull=True
        ).update(cancelled_at=now)
    Silla.objects.filter(vuelo=flight).update(estado=EstadoSilla.DISPONIBLE)
    flight.refresh_from_db()
    flight.estado = EstadoVuelo.CANCELADO
    flight.motivo_cancelacion = reason.strip()
    flight.cancelado_en = now
    flight.cancelado_por = actor
    flight.cupos_disponibles_economica = flight.cupos_disponibles_primera = 0
    flight.save()
    flight.noticias.update(vigente=False)
    flight.promotions.update(active=False, disabled_reason="flight_cancelled")
    BitacoraVuelo.objects.create(
        vuelo=flight,
        actor=actor,
        tipo_evento=BitacoraVuelo.Evento.CANCELACION,
        ip_origen=origin,
        detalles={"motivo": reason, "resolucion": "COMPRADOR", "pasajeros": len(tickets)},
    )
    return flight


def eligible(resolution, destination):
    tickets = list(resolution.tickets.select_related("viajero"))
    if (
        destination.pk == resolution.flight_id
        or destination.ruta_id != resolution.flight.ruta_id
        or destination.estado != EstadoVuelo.PROGRAMADO
        or destination.salida_utc <= timezone.now()
        or not destination.ruta.activa
        or not destination.ruta.origen.activa
        or not destination.ruta.destino.activa
    ):
        raise ResolutionConflict()
    counts = Counter(t.clase for t in tickets)
    for clase, count in counts.items():
        if (
            getattr(destination, capacity_field(clase)) < count
            or Silla.objects.filter(
                vuelo=destination, clase=clase, estado=EstadoSilla.DISPONIBLE
            ).count()
            < count
        ):
            raise ResolutionConflict("No quedan sillas para todo el grupo en su clase original.")
    if not any(t.viajero.es_mayor_de_edad(destination.fecha_salida) for t in tickets):
        raise ResolutionConflict("El grupo debe conservar un adulto acompañante.")
    if (
        contar_tiquetes_activos_cliente_en_vuelo(resolution.purchase.cliente, destination)
        + len(tickets)
        > 5
    ):
        raise ResolutionConflict("Se excede el límite de cinco viajeros del comprador en el vuelo.")
    for t in tickets:
        identity = {
            "viajero__tipo_documento__iexact": t.viajero.tipo_documento,
            "viajero__documento__iexact": t.viajero.documento,
        }
        if Tiquete.objects.filter(
            vuelo=destination, estado=EstadoTiquete.ACTIVO, **identity
        ).exists():
            raise ResolutionConflict("Un viajero ya tiene tiquete en la alternativa.")
        if (
            Reserva.objects.filter(
                estado=EstadoReserva.VIGENTE,
                limite_vigencia__gt=timezone.now(),
                **{f"viajeros_reserva__{k}": v for k, v in identity.items()},
            )
            .filter(Q(vuelo=destination) | Q(vuelo_regreso=destination))
            .exists()
        ):
            raise ResolutionConflict("Un viajero ya tiene reserva en la alternativa.")
    for other in (
        resolution.purchase.tiquetes.filter(estado=EstadoTiquete.ACTIVO)
        .exclude(vuelo_id=resolution.flight_id)
        .select_related("vuelo__ruta")
    ):
        leg = other.vuelo
        if (
            leg.ruta.origen_id == destination.ruta.destino_id
            and leg.salida_utc <= destination.llegada_utc
        ) or (
            leg.ruta.destino_id == destination.ruta.origen_id
            and leg.llegada_utc >= destination.salida_utc
        ):
            raise ResolutionConflict(
                "La alternativa es incompatible con la otra etapa del itinerario."
            )
    return tickets


def alternatives(resolution):
    if resolution.status != CancellationResolution.Status.PENDING:
        return []
    result = []
    for flight in (
        Vuelo.objects.filter(
            ruta=resolution.flight.ruta,
            estado=EstadoVuelo.PROGRAMADO,
            salida_utc__gt=timezone.now(),
        )
        .exclude(pk=resolution.flight_id)
        .select_related("ruta__origen", "ruta__destino")
        .order_by("salida_utc")
    ):
        try:
            eligible(resolution, flight)
        except ResolutionConflict:
            continue
        result.append(flight)
    return result


@inventory_transaction
def resolve(actor, pk, decision, destination_id=None):
    client_required(actor)
    resolution = (
        CancellationResolution.objects.select_related("purchase__cliente", "flight__ruta")
        .filter(pk=pk, purchase__cliente=actor)
        .first()
    )
    if resolution is None:
        raise NotFound()
    desired = {"RELOCATE": "RELOCATED", "REFUND": "REFUNDED"}.get(decision)
    if not desired:
        raise ValidationError("Selecciona reubicación o reembolso.")
    if resolution.status != "PENDING":
        if resolution.status != desired or (
            desired == "RELOCATED" and resolution.destination_id != destination_id
        ):
            raise ResolutionConflict("La cancelación ya fue resuelta de otra manera.")
        return resolution
    tickets = list(resolution.tickets.select_related("compra", "viajero", "vuelo"))
    if any(t.estado != EstadoTiquete.PENDIENTE_RESOLUCION for t in tickets):
        raise ResolutionConflict()
    if desired == "REFUNDED":
        for ticket in tickets:
            _refund_ticket(ticket)
    else:
        destination = (
            Vuelo.objects.select_related("ruta__origen", "ruta__destino")
            .filter(pk=destination_id)
            .first()
        )
        if destination is None:
            raise ResolutionConflict("Selecciona una alternativa disponible.")
        tickets = eligible(resolution, destination)
        for ticket in tickets:
            seat = (
                Silla.objects.select_for_update()
                .filter(vuelo=destination, clase=ticket.clase, estado=EstadoSilla.DISPONIBLE)
                .order_by("numero_silla")
                .first()
            )
            if seat is None:
                raise ResolutionConflict()
            seat.estado = EstadoSilla.OCUPADA
            seat.save(update_fields=["estado"])
            _change_capacity(destination, ticket.clase, -1)
            ticket.estado = EstadoTiquete.CANCELADO
            ticket.save(update_fields=["estado"])
            replacement = Tiquete.objects.create(
                compra=ticket.compra,
                vuelo=destination,
                viajero=ticket.viajero,
                silla=seat,
                clase=ticket.clase,
                precio_pagado=ticket.precio_pagado,
                replacement_of=ticket,
                numero_cambios_silla=ticket.numero_cambios_silla,
                codigo_tiquete=f"R{ticket.pk}-{destination.pk}",
            )
            notify(
                [ticket.viajero.correo],
                "Tiquete reubicado",
                f"Tiquete {replacement.codigo_tiquete}: vuelo {destination.codigo_vuelo}, "
                f"salida {destination.salida_utc.isoformat()}, silla {seat.numero_silla}. "
                "Realiza nuevamente el check-in cuando corresponda.",
            )
        resolution.destination = destination
    resolution.status = desired
    resolution.resolved_at = timezone.now()
    resolution.save(update_fields=["status", "resolved_at", "destination"])
    outcome = "reubicación sin cargo" if desired == "RELOCATED" else "reembolso"
    notify(
        [actor.email],
        "Cancelación resuelta",
        f"Compra {resolution.purchase.localizador}: {outcome} confirmado. "
        f"Importe original del grupo: {sum((t.precio_pagado for t in tickets), Decimal('0'))} COP.",
    )
    audit(actor, "cancellation_resolved", resolution, decision=decision, destination=destination_id)
    return resolution
