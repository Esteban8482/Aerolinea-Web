from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .checkin import boarding_pdf
from .models import JourneyNotification, Tiquete


def process_journey_emails(*, batch_size=100):
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
                JourneyNotification.objects.select_for_update(skip_locked=True, of=("self",))
                .filter(sent_at__isnull=True, cancelled_at__isnull=True, next_attempt_at__lte=now)
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

        job = JourneyNotification.objects.select_related(
            "ticket__compra",
            "ticket__vuelo__ruta__origen",
            "ticket__vuelo__ruta__destino",
            "ticket__viajero",
            "ticket__silla",
        ).get(pk=job.pk)
        if job.guest_access_id:
            access = job.guest_access
            valid = (
                access.revoked_at is None
                and Tiquete.objects.filter(
                    compra_id=access.compra_id,
                    viajero_id=access.viajero_id,
                    estado="ACTIVO",
                    vuelo__estado="PROGRAMADO",
                    vuelo__salida_utc__gt=timezone.now(),
                ).exists()
            )
            if not valid:
                JourneyNotification.objects.filter(pk=job.pk, lease_id=lease_id).update(
                    cancelled_at=timezone.now(),
                    body="",
                    lease_id=None,
                    lease_until=None,
                    last_error="access_expired",
                )
                continue
        try:
            message = EmailMessage(
                job.subject, job.body, settings.DEFAULT_FROM_EMAIL, [job.recipient]
            )
            if job.boarding_pass:
                message.attach(
                    f"boarding-pass-{job.ticket_id}.pdf",
                    boarding_pdf(job.ticket),
                    "application/pdf",
                )
            result = message.send(fail_silently=False)
            delivered = result == 1
        except Exception:
            # Nunca persistir excepciones SMTP: pueden contener credenciales o destinatarios.
            delivered = False
        with transaction.atomic():
            current = JourneyNotification.objects.select_for_update().get(pk=job.pk)
            if current.lease_id != lease_id:
                continue
            current.lease_until = current.lease_id = None
            current.last_error = "" if delivered else "mail_unavailable"
            if delivered:
                current.sent_at = timezone.now()
                if current.guest_access_id:
                    current.body = ""
            else:
                delay = min(3600, 60 * 2 ** min(current.attempts - 1, 6))
                current.next_attempt_at = timezone.now() + timedelta(seconds=delay)
            current.save(
                update_fields=[
                    "body",
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
