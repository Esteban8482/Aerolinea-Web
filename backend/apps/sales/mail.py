from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import NotificacionCompra


def render_notificacion_compra(notificacion: NotificacionCompra) -> tuple[str, str]:
    """Asunto y cuerpo del correo con el código de reserva para el viajero."""
    tiquete = notificacion.tiquete
    compra = tiquete.compra
    vuelo = tiquete.vuelo
    viajero = tiquete.viajero
    subject = f"Tu tiquete {tiquete.codigo_tiquete} - Aerolínea Web"
    body = (
        f"Hola {viajero.nombres} {viajero.apellidos},\n\n"
        f"Tu compra fue confirmada. Código de reserva (localizador): {compra.localizador}.\n"
        f"Tiquete: {tiquete.codigo_tiquete}\n"
        f"Vuelo: {vuelo.codigo_vuelo} ({vuelo.ruta.origen.nombre} -> {vuelo.ruta.destino.nombre})\n"
        f"Salida: {vuelo.fecha_salida.isoformat()} {vuelo.hora_salida.isoformat()}\n"
        f"Clase: {tiquete.get_clase_display()} - Silla: {tiquete.silla.numero_silla}\n"
    )
    return subject, body


def process_purchase_emails(*, batch_size=100):
    """Outbox con arrendamiento recuperable; SMTP siempre fuera de la transacción.

    Un fallo de correo no revierte la compra: la notificación queda pendiente
    con reintento por espera exponencial.
    """
    if transaction.get_connection().in_atomic_block:
        raise RuntimeError("Procesa el correo después del commit, fuera de una transacción.")
    sent = failed = 0
    for _ in range(batch_size):
        now = timezone.now()
        lease_id = uuid4()
        with transaction.atomic():
            job = (
                NotificacionCompra.objects.select_for_update(skip_locked=True, of=("self",))
                .filter(sent_at__isnull=True, next_attempt_at__lte=now)
                .filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now))
                .order_by("pk")
                .first()
            )
            if job is None:
                break
            job.lease_id = lease_id
            job.lease_until = now + timedelta(minutes=5)
            job.attempts += 1
            job.save(update_fields=["lease_id", "lease_until", "attempts"])

        job = NotificacionCompra.objects.select_related(
            "tiquete__compra",
            "tiquete__vuelo__ruta__origen",
            "tiquete__vuelo__ruta__destino",
            "tiquete__viajero",
            "tiquete__silla",
        ).get(pk=job.pk)
        subject, body = render_notificacion_compra(job)
        try:
            result = send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [job.recipient],
                fail_silently=False,
            )
            delivered = result == 1
        except Exception:
            # Nunca persistir excepciones SMTP: pueden contener credenciales o destinatarios.
            delivered = False
        with transaction.atomic():
            current = NotificacionCompra.objects.select_for_update().get(pk=job.pk)
            if current.lease_id != lease_id:
                continue
            current.lease_until = current.lease_id = None
            current.last_error = "" if delivered else "mail_unavailable"
            if delivered:
                current.sent_at = timezone.now()
            else:
                delay = min(3600, 60 * 2 ** min(current.attempts - 1, 6))
                current.next_attempt_at = timezone.now() + timedelta(seconds=delay)
            current.save(
                update_fields=[
                    "lease_until",
                    "lease_id",
                    "last_error",
                    "sent_at",
                    "next_attempt_at",
                ]
            )
        sent += int(delivered)
        failed += int(not delivered)
    return sent, failed
