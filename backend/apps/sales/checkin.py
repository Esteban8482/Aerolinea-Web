import hashlib
import secrets
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from apps.flights.models import EstadoVuelo

from .events import audit
from .locking import inventory_transaction
from .models import EstadoCheckin, EstadoTiquete, GuestAccess, JourneyNotification, Tiquete
from .rules import client_required
from .services import change_seat


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


@inventory_transaction
def request_link(locator, document_type, document, email):
    base = getattr(settings, "GUEST_CHECKIN_FRONTEND_URL", "")
    parsed = urlsplit(base)
    if (
        not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.scheme not in ("https", "http")
        or (not settings.DEBUG and parsed.scheme != "https")
    ):
        error = APIException("El acceso rápido aún no está configurado.")
        error.status_code = 503
        error.default_code = "guest_access_unavailable"
        raise error
    tickets = Tiquete.objects.filter(
        compra__localizador=locator.upper(),
        viajero__tipo_documento__iexact=document_type.strip(),
        viajero__documento__iexact=document.strip(),
        viajero__correo__iexact=email.strip(),
        estado=EstadoTiquete.ACTIVO,
        vuelo__estado=EstadoVuelo.PROGRAMADO,
        vuelo__salida_utc__gt=timezone.now(),
    ).select_related("viajero", "compra")
    ticket = tickets.first()
    if ticket is None:
        return
    old_access = GuestAccess.objects.filter(
        compra=ticket.compra, viajero=ticket.viajero, revoked_at__isnull=True
    )
    JourneyNotification.objects.filter(guest_access__in=old_access, sent_at__isnull=True).update(
        cancelled_at=timezone.now(), body=""
    )
    old_access.update(revoked_at=timezone.now())
    token = secrets.token_urlsafe(32)
    access = GuestAccess.objects.create(
        token_digest=digest(token), compra=ticket.compra, viajero=ticket.viajero
    )
    # Fragment keeps the credential out of ordinary HTTP URL/access logs.
    JourneyNotification.objects.create(
        recipient=ticket.viajero.correo,
        subject="Acceso seguro al check-in",
        guest_access=access,
        body=(
            f"Abre {base}#token={token}. Acceso limitado a tus tiquetes hasta "
            f"el cierre de check-in de cada vuelo."
        ),
    )


def authorized_tickets(actor=None, token=None):
    if token:
        access = GuestAccess.objects.filter(
            token_digest=digest(token), revoked_at__isnull=True
        ).first()
        if access is None:
            raise PermissionDenied()
        return Tiquete.objects.filter(
            compra_id=access.compra_id,
            viajero_id=access.viajero_id,
            vuelo__salida_utc__gt=timezone.now(),
            vuelo__estado=EstadoVuelo.PROGRAMADO,
            estado=EstadoTiquete.ACTIVO,
        )
    client_required(actor, require_verified=False)
    return Tiquete.objects.filter(compra__cliente=actor)


def check_window(ticket, now):
    if (
        ticket.estado != EstadoTiquete.ACTIVO
        or ticket.vuelo.estado != EstadoVuelo.PROGRAMADO
        or not ticket.vuelo.salida_utc - timedelta(hours=24) <= now < ticket.vuelo.salida_utc
    ):
        raise ValidationError(
            "El check-in solo está disponible durante las 24 horas anteriores a la salida."
        )


@inventory_transaction
def confirm_checkin(ticket_ids, actor=None, token=None):
    if not ticket_ids or len(ticket_ids) != len(set(ticket_ids)) or len(ticket_ids) > 10:
        raise ValidationError("Selecciona entre 1 y 10 tiquetes distintos.")
    tickets = list(
        authorized_tickets(actor, token)
        .select_for_update()
        .select_related("vuelo", "viajero")
        .filter(pk__in=ticket_ids)
        .order_by("pk")
    )
    if len(tickets) != len(ticket_ids):
        raise NotFound()
    if len({t.compra_id for t in tickets}) != 1:
        raise ValidationError("Selecciona tiquetes del mismo localizador.")
    now = timezone.now()
    for ticket in tickets:
        check_window(ticket, now)
    for ticket in tickets:
        if ticket.estado_checkin == EstadoCheckin.CONFIRMADO:
            continue
        ticket.estado_checkin = EstadoCheckin.CONFIRMADO
        ticket.fecha_checkin = now
        ticket.save(update_fields=["estado_checkin", "fecha_checkin"])
        audit(actor if not token else None, "checkin_confirmed", ticket)
        JourneyNotification.objects.create(
            recipient=ticket.viajero.correo,
            subject="Pasabordo",
            body=f"Check-in confirmado para el tiquete {ticket.codigo_tiquete}.",
            ticket=ticket,
            boarding_pass=True,
        )
    return tickets


@inventory_transaction
def guest_change_seat(ticket_id, seat_id, token):
    ticket = (
        authorized_tickets(token=token)
        .select_for_update()
        .select_related("vuelo")
        .filter(pk=ticket_id)
        .first()
    )
    if ticket is None:
        raise NotFound()
    return change_seat(ticket, seat_id)


def boarding_pdf(ticket):
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    if (
        ticket.estado != EstadoTiquete.ACTIVO
        or not ticket.checkin_confirmado
        or ticket.vuelo.estado == EstadoVuelo.CANCELADO
    ):
        raise ValidationError(
            "El pasabordo no está disponible; revisa el estado del tiquete y del check-in."
        )
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(595, 842))
    pdf.setTitle("Pasabordo")
    lines = [
        "PASABORDO",
        f"{ticket.viajero.nombres} {ticket.viajero.apellidos}",
        f"Vuelo: {ticket.vuelo.codigo_vuelo}",
        f"{ticket.vuelo.ruta.origen.nombre} - {ticket.vuelo.ruta.destino.nombre}",
        f"Salida: {ticket.vuelo.fecha_salida} {ticket.vuelo.hora_salida} "
        f"({ticket.vuelo.ruta.origen.zona_horaria})",
        f"Llegada: {ticket.vuelo.fecha_llegada} {ticket.vuelo.hora_llegada} "
        f"({ticket.vuelo.ruta.destino.zona_horaria})",
        f"Clase: {ticket.clase}; silla: {ticket.silla.numero_silla}",
        f"Localizador: {ticket.compra.localizador}; tiquete: {ticket.codigo_tiquete}",
    ]
    pdf.setFont("Helvetica", 12)
    y = 790
    for line in lines:
        for part in simpleSplit(str(line).replace("\n", " "), "Helvetica", 12, 525):
            pdf.drawString(35, y, part)
            y -= 20
        y -= 10
    pdf.save()
    return stream.getvalue()
