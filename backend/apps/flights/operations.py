from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.sales.events import audit, notify
from apps.sales.locking import inventory_transaction
from apps.sales.models import (
    Compra,
    EstadoCheckin,
    EstadoReserva,
    EstadoTiquete,
    JourneyNotification,
    RelocationOffer,
    Reserva,
    Tiquete,
)
from apps.sales.rules import administrator_required, capacity_field, client_required, money
from apps.sales.services import (
    _change_capacity,
    _refund_ticket,
    _release,
    calcular_limite_vigencia_reserva,
)

from .errors import FlightNotFound
from .models import EstadoSilla, EstadoVuelo, NoticiaVuelo, Promotion, Silla, Vuelo


def propagate_edit(flight, changes, actor):
    now = timezone.now()
    reservations = list(
        Reserva.objects.filter(estado=EstadoReserva.VIGENTE)
        .filter(Q(vuelo=flight) | Q(vuelo_regreso=flight))
        .select_related("vuelo", "vuelo_regreso", "cliente")
    )
    tickets = list(
        Tiquete.objects.filter(vuelo=flight, estado=EstadoTiquete.ACTIVO).select_related(
            "compra__cliente", "viajero"
        )
    )
    recipients = [t.viajero.correo for t in tickets] + [t.compra.cliente.email for t in tickets]
    for reservation in reservations:
        recipients += [
            reservation.cliente.email,
            *reservation.viajeros_reserva.values_list("viajero__correo", flat=True),
        ]
        legs = [reservation.vuelo] + (
            [reservation.vuelo_regreso] if reservation.vuelo_regreso else []
        )
        expired_before = reservation.limite_vigencia <= now
        reservation.limite_vigencia = min(
            reservation.creada_en + timedelta(hours=24),
            *[calcular_limite_vigencia_reserva(f, now)[0] for f in legs],
        )
        reservation.save(update_fields=["limite_vigencia"])
        if expired_before or reservation.limite_vigencia <= now:
            _release(reservation, EstadoReserva.VENCIDA)
        elif len(legs) > 1 and legs[1].salida_utc <= legs[0].llegada_utc:
            # Release the entire unpaid itinerary and explicitly notify; never silently move a leg.
            _release(reservation, EstadoReserva.CANCELADA)
            notify(
                [reservation.cliente.email],
                "Itinerario incompatible",
                f"La reprogramación hizo incompatible la reserva {reservation.pk}; "
                f"fue cancelada sin cargo.",
            )
    if "salida_nueva" in changes:
        for ticket in tickets:
            JourneyNotification.objects.filter(
                ticket=ticket, boarding_pass=True, sent_at__isnull=True
            ).update(cancelled_at=now)
            if ticket.estado_checkin == EstadoCheckin.CONFIRMADO:
                audit(
                    actor,
                    "checkin_invalidated",
                    ticket,
                    previous_checkin=ticket.fecha_checkin.isoformat()
                    if ticket.fecha_checkin
                    else None,
                )
                ticket.estado_checkin = EstadoCheckin.PENDIENTE
                ticket.fecha_checkin = None
                ticket.save(update_fields=["estado_checkin", "fecha_checkin"])
        for purchase_id in {t.compra_id for t in tickets}:
            ordered_tickets = (
                Tiquete.objects.filter(compra_id=purchase_id, estado=EstadoTiquete.ACTIVO)
                .select_related("vuelo")
                .order_by("creado_en", "pk")
            )
            legs = list({t.vuelo_id: t.vuelo for t in ordered_tickets}.values())
            if len(legs) > 1 and any(
                a.llegada_utc >= b.salida_utc for a, b in zip(legs, legs[1:], strict=False)
            ):
                purchase = Compra.objects.get(pk=purchase_id)
                purchase.disrupted = True
                purchase.save(update_fields=["disrupted"])
                notify(
                    [purchase.cliente.email],
                    "Revisión de itinerario requerida",
                    f"Compra {purchase.localizador}: horarios incompatibles. Solicita "
                    f"reubicación o reembolso; no se modificó otro vuelo.",
                )
                audit(actor, "itinerary_affected", purchase, flight=flight.pk)
    for promotion in flight.promotions.filter(active=True):
        base = (
            flight.costo_persona_primera
            if promotion.clase == "PRIMERA_CLASE"
            else flight.costo_persona_economica
        )
        if promotion.price >= base or promotion.ends_at > flight.salida_utc:
            promotion.active = False
            promotion.disabled_reason = "flight_edited"
            promotion.save(update_fields=["active", "disabled_reason"])
            flight.noticias.filter(tipo=f"PROMOTION_{promotion.pk}").update(vigente=False)
    notify(
        recipients,
        "Vuelo actualizado",
        f"El vuelo {flight.codigo_vuelo} cambió: {changes}. Revisa tus "
        f"horarios y realiza nuevamente el check-in si estaba confirmado.",
    )


@inventory_transaction
def create_promotion(actor, flight_id, clase, price, starts_at, ends_at):
    administrator_required(actor)
    flight = Vuelo.objects.select_for_update().filter(pk=flight_id).first()
    if flight is None:
        raise NotFound()
    now = timezone.now()
    price = money(price)
    if timezone.is_naive(starts_at) or timezone.is_naive(ends_at):
        raise ValidationError("Indica vigencia con zona horaria explícita.")
    base = (
        flight.costo_persona_primera if clase == "PRIMERA_CLASE" else flight.costo_persona_economica
    )
    if (
        flight.estado != EstadoVuelo.PROGRAMADO
        or flight.salida_utc <= now
        or getattr(flight, capacity_field(clase)) <= 0
    ):
        raise ValidationError("El vuelo no tiene disponibilidad para promoción.")
    if price >= base or ends_at <= now or ends_at <= starts_at or ends_at > flight.salida_utc:
        raise ValidationError(
            "Revisa el descuento y su vigencia: fin futuro, posterior al inicio "
            "y no después de la salida."
        )
    if flight.promotions.filter(
        clase=clase, active=True, starts_at__lt=ends_at, ends_at__gt=starts_at
    ).exists():
        raise ValidationError("Existe una promoción superpuesta para esta clase.")
    promotion = Promotion.objects.create(
        vuelo=flight,
        clase=clase,
        price=price,
        starts_at=starts_at,
        ends_at=ends_at,
        created_by=actor,
    )
    NoticiaVuelo.objects.create(
        vuelo=flight,
        titulo=f"Promoción {flight.codigo_vuelo}",
        contenido=f"{clase}: {price}; {starts_at.isoformat()} a {ends_at.isoformat()}",
        tipo=f"PROMOTION_{promotion.pk}",
    )
    audit(actor, "promotion_created", promotion, flight=flight.pk)
    return promotion


@inventory_transaction
def offer_relocation(actor, ticket_id, destination_id):
    administrator_required(actor)
    ticket = (
        Tiquete.objects.select_related("vuelo", "compra__cliente")
        .filter(pk=ticket_id, estado=EstadoTiquete.ACTIVO)
        .first()
    )
    destination = Vuelo.objects.filter(pk=destination_id).first()
    if ticket is None or destination is None:
        raise NotFound()
    _eligible_destination(ticket, destination)
    if ticket.relocation_offers.filter(resolved_at__isnull=True).exists():
        raise ValidationError("Ya existe una propuesta pendiente para este tiquete.")
    offer = RelocationOffer.objects.create(ticket=ticket, destination=destination, created_by=actor)
    notify(
        [ticket.compra.cliente.email],
        "Propuesta de reubicación",
        f"Propuesta {offer.pk}: tiquete {ticket.codigo_tiquete} al vuelo "
        f"{destination.codigo_vuelo}. Acepta o solicita reembolso desde tu cuenta. "
        "No hay cobro adicional.",
    )
    audit(actor, "relocation_offered", offer)
    return offer


def _eligible_destination(ticket, destination):
    if (
        destination.pk == ticket.vuelo_id
        or destination.ruta_id != ticket.vuelo.ruta_id
        or destination.estado != EstadoVuelo.PROGRAMADO
        or destination.salida_utc <= timezone.now()
        or getattr(destination, capacity_field(ticket.clase)) <= 0
        or not Silla.objects.filter(
            vuelo=destination, clase=ticket.clase, estado=EstadoSilla.DISPONIBLE
        ).exists()
    ):
        raise ValidationError("No hay disponibilidad compatible en el vuelo de destino.")
    other = Tiquete.objects.filter(
        vuelo=destination,
        estado=EstadoTiquete.ACTIVO,
        viajero__tipo_documento__iexact=ticket.viajero.tipo_documento,
        viajero__documento__iexact=ticket.viajero.documento,
    )
    retained = Reserva.objects.filter(
        estado=EstadoReserva.VIGENTE,
        limite_vigencia__gt=timezone.now(),
        viajeros_reserva__viajero__tipo_documento__iexact=ticket.viajero.tipo_documento,
        viajeros_reserva__viajero__documento__iexact=ticket.viajero.documento,
    ).filter(Q(vuelo=destination) | Q(vuelo_regreso=destination))
    destination_passengers = Tiquete.objects.filter(
        compra=ticket.compra, vuelo=destination, estado=EstadoTiquete.ACTIVO
    ).select_related("viajero")
    if not ticket.viajero.es_mayor_de_edad(destination.fecha_salida) and not any(
        t.viajero.es_mayor_de_edad(destination.fecha_salida) for t in destination_passengers
    ):
        raise ValidationError(
            "La reubicación debe mantener un adulto en el vuelo; reubica primero al adulto."
        )
    if other.exists() or retained.exists():
        raise ValidationError("El viajero ya participa en el vuelo de destino.")
    from apps.sales.services import contar_tiquetes_activos_cliente_en_vuelo

    if contar_tiquetes_activos_cliente_en_vuelo(ticket.compra.cliente, destination) >= 5:
        raise ValidationError("El comprador alcanzó el límite de tiquetes en el destino.")
    for other_ticket in (
        ticket.compra.tiquetes.filter(estado=EstadoTiquete.ACTIVO)
        .exclude(vuelo_id=ticket.vuelo_id)
        .select_related("vuelo")
    ):
        leg = other_ticket.vuelo
        if (
            leg.ruta.origen_id == destination.ruta.destino_id
            and leg.salida_utc <= destination.llegada_utc
        ):
            raise ValidationError("El nuevo vuelo hace incompatible el regreso.")
        if (
            leg.ruta.destino_id == destination.ruta.origen_id
            and leg.llegada_utc >= destination.salida_utc
        ):
            raise ValidationError("El nuevo vuelo hace incompatible la ida.")


@inventory_transaction
def resolve_relocation(actor, offer_id, decision):
    client_required(actor)
    offer = (
        RelocationOffer.objects.select_related(
            "ticket__compra", "ticket__vuelo", "ticket__viajero", "destination__ruta"
        )
        .filter(pk=offer_id, ticket__compra__cliente=actor)
        .first()
    )
    if offer is None:
        raise NotFound()
    if decision not in ("ACCEPT", "REFUND"):
        raise ValidationError("Selecciona ACCEPT o REFUND.")
    if offer.resolved_at:
        if offer.decision != decision:
            raise ValidationError("La propuesta ya fue resuelta.")
        return offer
    ticket = offer.ticket
    if ticket.estado != EstadoTiquete.ACTIVO or ticket.vuelo.estado != EstadoVuelo.PROGRAMADO:
        raise ValidationError("El tiquete ya no admite resolución de reubicación.")
    # Buyer explicitly chooses the outcome. Re-check capacity at acceptance time.
    if decision == "ACCEPT":
        try:
            _eligible_destination(ticket, offer.destination)
        except ValidationError:
            decision = "REFUND"
    if decision == "REFUND":
        _refund_ticket(ticket)
    else:
        _relocate(ticket, offer.destination)
        offer.accepted_at = timezone.now()
    offer.decision = decision
    offer.resolved_at = timezone.now()
    offer.save(update_fields=["decision", "resolved_at", "accepted_at"])
    audit(actor, "relocation_resolved", offer, decision=decision)
    notify(
        [actor.email, ticket.viajero.correo],
        "Propuesta resuelta",
        f"Propuesta {offer.pk}: {decision}.",
    )
    return offer


def _relocate(ticket, destination):
    seat = (
        Silla.objects.select_for_update()
        .filter(vuelo=destination, clase=ticket.clase, estado=EstadoSilla.DISPONIBLE)
        .order_by("pk")
        .first()
    )
    if seat is None:
        _refund_ticket(ticket)
        return
    ticket.estado = EstadoTiquete.CANCELADO
    ticket.save(update_fields=["estado"])
    Silla.objects.filter(pk=ticket.silla_id).update(estado=EstadoSilla.DISPONIBLE)
    _change_capacity(Vuelo.objects.get(pk=ticket.vuelo_id), ticket.clase, 1)
    _change_capacity(destination, ticket.clase, -1)
    seat.estado = EstadoSilla.OCUPADA
    seat.save(update_fields=["estado"])
    replacement = Tiquete.objects.create(
        compra=ticket.compra,
        vuelo=destination,
        viajero=ticket.viajero,
        silla=seat,
        clase=ticket.clase,
        precio_pagado=ticket.precio_pagado,
        codigo_tiquete=f"R{ticket.pk}-{destination.pk}",
        replacement_of=ticket,
        numero_cambios_silla=ticket.numero_cambios_silla,
    )
    JourneyNotification.objects.create(
        recipient=ticket.viajero.correo,
        subject="Tiquete reubicado",
        body=(
            f"Nuevo tiquete {replacement.codigo_tiquete}; vuelo "
            f"{destination.codigo_vuelo}; localizador {ticket.compra.localizador}."
        ),
    )


def cancel_flight(flight_id, reason, alternative, actor, origin):
    # Preserve the internal call signature for existing integrations; purchaser selects outcome.
    from apps.sales.cancellations import cancel

    return cancel(actor, flight_id, reason, origin)


@inventory_transaction
def complete_flight(actor, flight_id):
    """Explicit operational confirmation; time passing never marks a flight performed."""
    administrator_required(actor)
    flight = Vuelo.objects.select_for_update().filter(pk=flight_id).first()
    if flight is None:
        raise FlightNotFound()
    if flight.estado == EstadoVuelo.REALIZADO:
        return flight
    if flight.estado != EstadoVuelo.PROGRAMADO or flight.salida_utc > timezone.now():
        raise ValidationError("Confirma la operación solo después de la salida programada.")
    flight.estado = EstadoVuelo.REALIZADO
    flight.save(update_fields=["estado"])
    flight.noticias.update(vigente=False)
    flight.promotions.update(active=False, disabled_reason="flight_performed")
    for reservation in Reserva.objects.filter(estado=EstadoReserva.VIGENTE).filter(
        Q(vuelo=flight) | Q(vuelo_regreso=flight)
    ):
        _release(reservation, EstadoReserva.VENCIDA)
    audit(actor, "flight_performed", flight)
    return flight
