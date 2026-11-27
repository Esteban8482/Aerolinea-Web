import secrets
import string
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.flights.models import (
    ClaseTiquete,
    EstadoSilla,
    EstadoVuelo,
    Promotion,
    Silla,
    TipoVuelo,
    Vuelo,
)
from apps.wallets.models import MovimientoBilletera
from apps.wallets.services import debitar_para_compra, reembolsar_a_billetera

from .errors import (
    CancellationResolutionPending,
    CancellationWindowClosed,
    CheckinAlreadyConfirmed,
    InsufficientSeats,
    PurchaseNotCancellable,
    ReservationNotActive,
    ReservationWindowClosed,
    SeatChangeLimitReached,
    SeatNotAvailable,
)
from .events import audit, notify
from .locking import inventory_transaction
from .models import (
    Compra,
    EstadoCompra,
    EstadoReserva,
    EstadoTiquete,
    JourneyNotification,
    NotificacionCompra,
    Reserva,
    ReservaViajero,
    TipoTrayecto,
    Tiquete,
    Viajero,
)
from .rules import capacity_field, client_required, identity, itinerary, owned, travelers


class PriceChanged(APIException):
    status_code = 409
    default_code = "price_changed"
    default_detail = "El precio cambió. Confirma el nuevo total antes de comprar."


def generar_localizador():
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def generar_codigo_tiquete(localizador, indice):
    return f"{localizador}-{indice:02d}"


def calcular_limite_vigencia_reserva(vuelo, now=None):
    now = now or timezone.now()
    cutoff = vuelo.salida_utc - timedelta(hours=1 if vuelo.tipo_vuelo == TipoVuelo.NACIONAL else 3)
    return cutoff, min(now + timedelta(hours=24), cutoff)


def resolver_precio_vigente(vuelo, clase, fecha=None, reservation_created_at=None):
    capacity_field(clase)
    now = fecha or timezone.now()
    base = (
        vuelo.costo_persona_primera
        if clase == ClaseTiquete.PRIMERA_CLASE
        else vuelo.costo_persona_economica
    )
    promotions = Promotion.objects.filter(
        vuelo=vuelo, clase=clase, active=True, starts_at__lte=now, ends_at__gt=now, price__lt=base
    )
    if reservation_created_at is not None:
        promotions = promotions.filter(
            starts_at__lte=reservation_created_at, created_at__lte=reservation_created_at
        )
    promotion = promotions.order_by("pk").first()
    return promotion.price if promotion else base


def contar_tiquetes_activos_cliente_en_vuelo(cliente, vuelo):
    return (
        ReservaViajero.objects.filter(
            reserva__cliente=cliente,
            reserva__estado=EstadoReserva.VIGENTE,
            reserva__limite_vigencia__gt=timezone.now(),
        )
        .filter(Q(reserva__vuelo=vuelo) | Q(reserva__vuelo_regreso=vuelo))
        .count()
        + Tiquete.objects.filter(
            compra__cliente=cliente, vuelo=vuelo, estado=EstadoTiquete.ACTIVO
        ).count()
    )


def obtener_o_crear_viajero(data):
    # Snapshot per operation: never reuse another buyer's private contact data.
    data = dict(data)
    data["tipo_documento"], data["documento"] = identity(data)
    return Viajero.objects.create(**data)


def _flights(outbound, inbound=None):
    ids = [outbound] + ([inbound] if inbound else [])
    rows = {
        f.pk: f
        for f in Vuelo.objects.select_for_update()
        .select_related("ruta")
        .filter(pk__in=ids)
        .order_by("pk")
    }
    if len(rows) != len(set(ids)):
        raise NotFound()
    return [rows[i] for i in ids]


def _change_capacity(flight, clase, delta):
    field = capacity_field(clase)
    value = getattr(flight, field) + delta
    maximum = (
        flight.cupos_primera_clase
        if clase == ClaseTiquete.PRIMERA_CLASE
        else flight.cupos_economica
    )
    if value < 0:
        raise InsufficientSeats()
    if value > maximum:
        raise ValidationError("El inventario requiere conciliación; no se modificó la operación.")
    setattr(flight, field, value)
    flight.save(update_fields=[field])


def _release(reservation, state):
    if reservation.estado != EstadoReserva.VIGENTE:
        return False
    for flight in _flights(reservation.vuelo_id, reservation.vuelo_regreso_id):
        _change_capacity(flight, reservation.clase, reservation.viajeros_reserva.count())
    reservation.estado = state
    reservation.save(update_fields=["estado"])
    return True


@inventory_transaction
def liberar_reserva_si_vencida(reserva):
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado == EstadoReserva.VIGENTE and timezone.now() >= reserva.limite_vigencia:
        return _release(reserva, EstadoReserva.VENCIDA)
    return False


def _expire_for(flights):
    ids = [f.pk for f in flights]
    for reservation in (
        Reserva.objects.filter(estado=EstadoReserva.VIGENTE, limite_vigencia__lte=timezone.now())
        .filter(Q(vuelo_id__in=ids) | Q(vuelo_regreso_id__in=ids))
        .order_by("pk")
    ):
        liberar_reserva_si_vencida(reservation)
    for flight in flights:
        flight.refresh_from_db()


@inventory_transaction
def crear_reserva(
    cliente, vuelo_id, clase, viajeros_data, tipo_trayecto=TipoTrayecto.UNICO, vuelo_regreso_id=None
):
    client_required(cliente)
    flights = _flights(vuelo_id, vuelo_regreso_id)
    _expire_for(flights)
    now = timezone.now()
    itinerary(flights, tipo_trayecto, now)
    travelers(viajeros_data, flights, cliente, now)
    expiry = min(calcular_limite_vigencia_reserva(f, now)[1] for f in flights)
    if now >= expiry:
        raise ReservationWindowClosed()
    for flight in flights:
        _change_capacity(flight, clase, -len(viajeros_data))
    reservation = Reserva.objects.create(
        cliente=cliente,
        vuelo=flights[0],
        vuelo_regreso=flights[1] if len(flights) > 1 else None,
        tipo_trayecto=tipo_trayecto,
        clase=clase,
        limite_vigencia=expiry,
    )
    for data in viajeros_data:
        ReservaViajero.objects.create(reserva=reservation, viajero=obtener_o_crear_viajero(data))
    audit(cliente, "reservation_created", reservation)
    return reservation


@inventory_transaction
def cancelar_reserva(reserva_id, cliente):
    client_required(cliente)
    reservation = owned(Reserva.objects.select_for_update(), cliente, pk=reserva_id)
    if reservation.estado == EstadoReserva.CANCELADA:
        return reservation
    if reservation.estado != EstadoReserva.VIGENTE or timezone.now() >= reservation.limite_vigencia:
        raise ReservationNotActive()
    _release(reservation, EstadoReserva.CANCELADA)
    audit(cliente, "reservation_cancelled", reservation)
    notify(
        [cliente.email, *reservation.viajeros_reserva.values_list("viajero__correo", flat=True)],
        "Reserva cancelada",
        f"La reserva {reservation.pk} fue cancelada. No existía un pago que reembolsar.",
    )
    return reservation


@inventory_transaction
def comprar_tiquetes(
    cliente,
    vuelo_id=None,
    clase=ClaseTiquete.ECONOMICA,
    viajeros_data=None,
    reserva_id=None,
    tipo_trayecto=TipoTrayecto.UNICO,
    vuelo_regreso_id=None,
    accepted_total=None,
):
    client_required(cliente)
    reservation = None
    now = timezone.now()
    if reserva_id:
        reservation = owned(Reserva.objects.select_for_update(), cliente, pk=reserva_id)
        if reservation.estado != EstadoReserva.VIGENTE or now >= reservation.limite_vigencia:
            raise ReservationNotActive()
        vuelo_id, vuelo_regreso_id = reservation.vuelo_id, reservation.vuelo_regreso_id
        clase, tipo_trayecto = reservation.clase, reservation.tipo_trayecto
        passengers = [r.viajero for r in reservation.viajeros_reserva.select_related("viajero")]
        fields = [
            "documento",
            "tipo_documento",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "genero",
            "telefono",
            "correo",
            "nombre_contacto",
            "telefono_contacto",
        ]
        viajeros_data = [{key: getattr(v, key) for key in fields} for v in passengers]
    flights = _flights(vuelo_id, vuelo_regreso_id)
    _expire_for(flights)
    now = timezone.now()
    itinerary(flights, tipo_trayecto, now)
    travelers(viajeros_data or [], flights, cliente, now, reserva_id)
    prices = [
        (
            resolver_precio_vigente(f, clase, now, reservation_created_at=reservation.creada_en)
            if reservation
            else resolver_precio_vigente(f, clase, now)
        )
        for f in flights
    ]
    total = sum(prices) * len(viajeros_data)
    if accepted_total is None or Decimal(str(accepted_total)) != total:
        error = PriceChanged()
        error.current_total = str(total)
        raise error
    if not reservation:
        passengers = [obtener_o_crear_viajero(data) for data in viajeros_data]
        for flight in flights:
            _change_capacity(flight, clase, -len(passengers))
    # Retry only locator collisions inside savepoints, not arbitrary integrity failures.
    for _ in range(10):
        locator = generar_localizador()
        try:
            with transaction.atomic():
                purchase = Compra.objects.create(
                    cliente=cliente,
                    localizador=locator,
                    valor_pagado=total,
                    tipo_trayecto=tipo_trayecto,
                    reserva_origen=reservation,
                )
            break
        except IntegrityError:
            if not Compra.objects.filter(localizador=locator).exists():
                raise
    else:
        raise ValidationError("No fue posible generar el localizador. Reintenta.")
    debit = debitar_para_compra(cliente.wallet.pk, total, f"Compra tiquetes localizador {locator}")
    purchase.debit = debit
    purchase.save(update_fields=["debit"])
    index = 0
    for flight, price in zip(flights, prices, strict=True):
        seats = list(
            Silla.objects.select_for_update()
            .filter(vuelo=flight, clase=clase, estado=EstadoSilla.DISPONIBLE)
            .order_by("pk")
        )
        if len(seats) < len(passengers):
            raise InsufficientSeats()
        for passenger in passengers:
            seat = seats.pop(secrets.randbelow(len(seats)))
            seat.estado = EstadoSilla.OCUPADA
            seat.save(update_fields=["estado"])
            index += 1
            ticket = Tiquete.objects.create(
                compra=purchase,
                vuelo=flight,
                viajero=passenger,
                silla=seat,
                clase=clase,
                precio_pagado=price,
                codigo_tiquete=generar_codigo_tiquete(locator, index),
            )
            NotificacionCompra.objects.create(tiquete=ticket, recipient=passenger.correo)
    if reservation:
        reservation.estado = EstadoReserva.COMPRADA
        reservation.save(update_fields=["estado"])
    audit(cliente, "purchase_confirmed", purchase, total=str(total))
    return purchase


def _refund_ticket(ticket):
    pending_resolution = ticket.estado == EstadoTiquete.PENDIENTE_RESOLUCION
    if ticket.estado not in (EstadoTiquete.ACTIVO, EstadoTiquete.PENDIENTE_RESOLUCION):
        return
    purchase = Compra.objects.select_for_update().get(pk=ticket.compra_id)
    debit = purchase.debit
    if (
        debit is None
        or debit.tipo != MovimientoBilletera.Tipo.COMPRA
        or debit.wallet.user_id != purchase.cliente_id
    ):
        raise ValidationError(
            "No existe un débito conciliado para este tiquete; se requiere revisión financiera."
        )
    legacy_unresolved = purchase.tiquetes.filter(
        estado=EstadoTiquete.CANCELADO, refund__isnull=True, replacement__isnull=True
    ).exists()
    original_total = sum(
        purchase.tiquetes.filter(replacement_of__isnull=True).values_list(
            "precio_pagado", flat=True
        ),
        Decimal("0"),
    )
    if legacy_unresolved or original_total != debit.valor or purchase.valor_pagado != debit.valor:
        raise ValidationError("El historial financiero requiere conciliación antes de reembolsar.")
    refunded = sum(
        purchase.tiquetes.filter(refund__isnull=False).values_list("refund__valor", flat=True),
        Decimal("0"),
    )
    if refunded + ticket.precio_pagado > debit.valor:
        raise ValidationError("El reembolso excede el débito original.")
    refund = reembolsar_a_billetera(
        debit.wallet_id, ticket.precio_pagado, f"Reembolso tiquete {ticket.pk}; débito {debit.pk}"
    )
    JourneyNotification.objects.filter(
        ticket=ticket, boarding_pass=True, sent_at__isnull=True
    ).update(cancelled_at=timezone.now())
    ticket.refund = refund
    ticket.estado = EstadoTiquete.CANCELADO
    ticket.save(update_fields=["refund", "estado"])
    Silla.objects.filter(pk=ticket.silla_id).update(estado=EstadoSilla.DISPONIBLE)
    flight = Vuelo.objects.select_for_update().get(pk=ticket.vuelo_id)
    if not pending_resolution:
        _change_capacity(flight, ticket.clase, 1)
    if not purchase.tiquetes.filter(
        estado__in=[EstadoTiquete.ACTIVO, EstadoTiquete.PENDIENTE_RESOLUCION]
    ).exists():
        purchase.estado = EstadoCompra.CANCELADA
        purchase.fecha_cancelacion = timezone.now()
        purchase.save(update_fields=["estado", "fecha_cancelacion"])


@inventory_transaction
def cancelar_compra(compra_id, cliente):
    client_required(cliente)
    purchase = owned(Compra.objects.select_for_update(), cliente, pk=compra_id)
    if purchase.tiquetes.filter(estado=EstadoTiquete.PENDIENTE_RESOLUCION).exists():
        raise CancellationResolutionPending()
    if purchase.estado == EstadoCompra.CANCELADA:
        return purchase
    tickets = list(
        purchase.tiquetes.filter(estado=EstadoTiquete.ACTIVO).select_related("vuelo", "viajero")
    )
    if not tickets:
        raise PurchaseNotCancellable()
    now = timezone.now()
    for ticket in tickets:
        if ticket.refund_id:
            raise PurchaseNotCancellable()
        if now >= calcular_limite_vigencia_reserva(ticket.vuelo, now)[0]:
            raise CancellationWindowClosed()
    for ticket in tickets:
        _refund_ticket(ticket)
    audit(cliente, "purchase_cancelled", purchase)
    notify(
        [cliente.email, *[t.viajero.correo for t in tickets]],
        "Compra cancelada",
        f"Compra {purchase.localizador}: reembolso al comprador confirmado.",
    )
    purchase.refresh_from_db()
    return purchase


@inventory_transaction
def reembolsar_tiquetes_por_cancelacion_vuelo(vuelo_id):
    tickets = list(
        Tiquete.objects.filter(vuelo_id=vuelo_id, estado=EstadoTiquete.ACTIVO)
        .select_related("compra__cliente", "viajero")
        .order_by("compra__cliente_id", "pk")
    )
    for ticket in tickets:
        _refund_ticket(ticket)
        notify(
            [ticket.compra.cliente.email, ticket.viajero.correo],
            "Vuelo cancelado",
            f"El tiquete {ticket.codigo_tiquete} fue reembolsado al comprador.",
        )
    return len(tickets)


@inventory_transaction
def cambiar_silla_tiquete(tiquete_id, nueva_silla_id, actor):
    client_required(actor, require_verified=False)
    ticket = (
        Tiquete.objects.select_for_update()
        .select_related("compra", "vuelo")
        .filter(pk=tiquete_id, compra__cliente=actor)
        .first()
    )
    if ticket is None:
        raise NotFound()
    return change_seat(ticket, nueva_silla_id, actor)


def change_seat(ticket, seat_id, actor=None):
    if (
        ticket.estado != EstadoTiquete.ACTIVO
        or ticket.vuelo.estado != EstadoVuelo.PROGRAMADO
        or ticket.vuelo.salida_utc <= timezone.now()
    ):
        raise SeatNotAvailable()
    if ticket.checkin_confirmado:
        raise CheckinAlreadyConfirmed()
    if ticket.silla_id == seat_id:
        return ticket
    if ticket.numero_cambios_silla >= 1:
        raise SeatChangeLimitReached()
    seat = (
        Silla.objects.select_for_update()
        .filter(
            pk=seat_id, vuelo_id=ticket.vuelo_id, clase=ticket.clase, estado=EstadoSilla.DISPONIBLE
        )
        .first()
    )
    if seat is None:
        raise SeatNotAvailable()
    previous = ticket.silla_id
    Silla.objects.filter(pk=previous).update(estado=EstadoSilla.DISPONIBLE)
    seat.estado = EstadoSilla.OCUPADA
    seat.save(update_fields=["estado"])
    ticket.silla = seat
    ticket.numero_cambios_silla += 1
    ticket.save(update_fields=["silla", "numero_cambios_silla"])
    audit(actor, "seat_changed", ticket, previous_seat=previous, new_seat=seat.pk)
    return ticket


@inventory_transaction
def quote_purchase(
    cliente,
    vuelo_id=None,
    clase=ClaseTiquete.ECONOMICA,
    viajeros_data=None,
    reserva_id=None,
    tipo_trayecto=TipoTrayecto.UNICO,
    vuelo_regreso_id=None,
):
    """Return a current total; a quote never retains capacity or debits money."""
    client_required(cliente)
    reservation = None
    if reserva_id:
        reservation = owned(Reserva.objects.all(), cliente, pk=reserva_id)
        if (
            reservation.estado != EstadoReserva.VIGENTE
            or timezone.now() >= reservation.limite_vigencia
        ):
            raise ReservationNotActive()
        vuelo_id, vuelo_regreso_id = reservation.vuelo_id, reservation.vuelo_regreso_id
        clase, tipo_trayecto = reservation.clase, reservation.tipo_trayecto
        count = reservation.viajeros_reserva.count()
    else:
        count = len(viajeros_data or [])
        if not 1 <= count <= 5:
            raise ValidationError("Selecciona entre uno y cinco viajeros.")
    flights = _flights(vuelo_id, vuelo_regreso_id)
    itinerary(flights, tipo_trayecto, timezone.now())
    prices = [
        resolver_precio_vigente(
            f, clase, reservation_created_at=reservation.creada_en if reservation else None
        )
        for f in flights
    ]
    return {
        "total": str(sum(prices) * count),
        "currency": "COP",
        "prices": [str(p) for p in prices],
        "quoted_at": timezone.now().isoformat(),
    }
