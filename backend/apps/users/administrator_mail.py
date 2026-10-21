"""Aviso persistente de creación de administrador; nunca transporta su contraseña."""

from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .administration_services import administration_event
from .models import AdministrationEvent, AdministratorNotification, User


def process_administrator_notifications(*, batch_size=100):
    if transaction.get_connection().in_atomic_block:
        raise RuntimeError("Procesa el correo después del commit, fuera de una transacción.")
    sent = failed = 0
    for _ in range(batch_size):
        now = timezone.now()
        lease_id = uuid4()
        with transaction.atomic():
            job = (
                AdministratorNotification.objects.select_for_update(skip_locked=True, of=("self",))
                .filter(
                    sent_at__isnull=True,
                    next_attempt_at__lte=now,
                    user__is_active=True,
                    user__role=User.Role.ADMINISTRADOR,
                    recipient=F("user__email"),
                )
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
        try:
            delivered = (
                send_mail(
                    "Cuenta de administrador creada",
                    "Se creó una cuenta de administrador asociada a este correo en Aerolínea Web.\n"
                    "Puedes iniciar sesión con tu correo y la contraseña inicial. "
                    "Si no dispones de ella, utiliza la recuperación de acceso de la plataforma.\n"
                    "Este mensaje no contiene contraseñas ni enlaces de acceso.\n",
                    settings.DEFAULT_FROM_EMAIL,
                    [job.recipient],
                    fail_silently=False,
                )
                == 1
            )
        except Exception:
            delivered = False
        with transaction.atomic():
            current = AdministratorNotification.objects.select_for_update().get(pk=job.pk)
            if current.lease_id != lease_id:
                continue
            current.lease_id = current.lease_until = None
            current.last_error = "" if delivered else "mail_unavailable"
            if delivered:
                current.sent_at = timezone.now()
            else:
                current.next_attempt_at = timezone.now() + timedelta(
                    seconds=min(3600, 60 * 2 ** min(current.attempts - 1, 6))
                )
            current.save(
                update_fields=[
                    "lease_id",
                    "lease_until",
                    "last_error",
                    "sent_at",
                    "next_attempt_at",
                ]
            )
            administration_event(
                kind=AdministrationEvent.Kind.MAIL_SENT
                if delivered
                else AdministrationEvent.Kind.MAIL_FAILED,
                action=AdministrationEvent.Action.MAIL,
                target=current.user,
            )
        sent += int(delivered)
        failed += int(not delivered)
    return sent, failed
