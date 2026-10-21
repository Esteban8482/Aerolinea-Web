"""Outbox específica de recuperación; leases y entrega fuera de transacciones."""

from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .auth_services import audit, password_fingerprint, recovery_token
from .mail import validate_frontend_url
from .models import AuthenticationEvent, PasswordRecovery


def process_recovery_emails(*, batch_size=100):
    if transaction.get_connection().in_atomic_block:
        raise RuntimeError("Procesa el correo después del commit, fuera de una transacción.")
    target = settings.PASSWORD_RECOVERY_FRONTEND_URL
    validate_frontend_url(target, setting_name="PASSWORD_RECOVERY_FRONTEND_URL")
    sent = failed = 0
    for _ in range(batch_size):
        now = timezone.now()
        lease_id = uuid4()
        with transaction.atomic():
            job = (
                PasswordRecovery.objects.select_for_update(skip_locked=True, of=("self",))
                .select_related("user")
                .filter(
                    sent_at__isnull=True,
                    consumed_at__isnull=True,
                    superseded_at__isnull=True,
                    expires_at__gt=now,
                    next_attempt_at__lte=now,
                    user__is_active=True,
                    recipient=F("user__email"),
                )
                .filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now))
                .order_by("pk")
                .first()
            )
            if job is None:
                break
            # No enviar un enlace invalidado por otra vía de cambio de credenciales.
            if job.password_fingerprint != password_fingerprint(job.user):
                job.superseded_at = now
                job.save(update_fields=["superseded_at"])
                continue
            job.lease_id = lease_id
            job.lease_until = now + timedelta(minutes=5)
            job.attempts += 1
            job.save(update_fields=["lease_id", "lease_until", "attempts"])
        link = target + "#" + urlencode({"token": recovery_token(job)})
        try:
            delivered = (
                send_mail(
                    "Restablece tu contraseña",
                    f"Abre {link}\nEl enlace vence a las {job.expires_at.isoformat()}.\n"
                    "Confirma la nueva contraseña en la página. "
                    "Si no solicitaste recuperar tu cuenta, ignora este mensaje.",
                    settings.DEFAULT_FROM_EMAIL,
                    [job.recipient],
                    fail_silently=False,
                )
                == 1
            )
        except Exception:
            delivered = False
        with transaction.atomic():
            current = PasswordRecovery.objects.select_for_update().get(pk=job.pk)
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
            audit(
                AuthenticationEvent.Kind.MAIL_SENT
                if delivered
                else AuthenticationEvent.Kind.MAIL_FAILED,
                user=current.user,
                recovery=current,
            )
        sent += int(delivered)
        failed += int(not delivered)
    return sent, failed
