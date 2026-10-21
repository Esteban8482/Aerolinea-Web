from datetime import timedelta
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import EmailVerification, RegistrationEvent, User
from .services import verification_token


def validate_frontend_url(target, *, setting_name="EMAIL_VERIFICATION_FRONTEND_URL"):
    parts = urlsplit(target)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.netloc
        or parts.fragment
        or parts.query
        or parts.username
        or parts.password
        or (not settings.DEBUG and parts.scheme != "https")
    ):
        raise ImproperlyConfigured(
            f"Configura {setting_name} sin query ni fragmento, HTTPS fuera de DEBUG."
        )


def process_verification_emails(*, batch_size=100):
    """Outbox con arrendamiento recuperable; SMTP siempre fuera de la transacción."""
    if transaction.get_connection().in_atomic_block:
        raise RuntimeError("Procesa el correo después del commit, fuera de una transacción.")
    target = settings.EMAIL_VERIFICATION_FRONTEND_URL
    validate_frontend_url(target)
    sent = failed = 0
    for _ in range(batch_size):
        now = timezone.now()
        lease_id = uuid4()
        with transaction.atomic():
            job = (
                EmailVerification.objects.select_for_update(skip_locked=True, of=("self",))
                .filter(
                    sent_at__isnull=True,
                    consumed_at__isnull=True,
                    superseded_at__isnull=True,
                    expires_at__gt=now,
                    next_attempt_at__lte=now,
                    user__is_email_verified=False,
                    user__is_active=True,
                    user__role=User.Role.CLIENTE,
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
        # Fragmento: el navegador no lo envía como URL ni Referer al servidor.
        link = target + "#" + urlencode({"token": verification_token(job)})
        try:
            result = send_mail(
                "Verifica tu correo",
                f"Abre {link}\nEl enlace vence a las {job.expires_at.isoformat()}.\n"
                "Confirma la verificación en la página. "
                "Si no solicitaste esta cuenta, ignora el mensaje.",
                settings.DEFAULT_FROM_EMAIL,
                [job.recipient],
                fail_silently=False,
            )
            delivered = result == 1
        except Exception:
            # Nunca persistir excepciones SMTP: pueden contener credenciales o destinatarios.
            delivered = False
        with transaction.atomic():
            current = EmailVerification.objects.select_for_update().get(pk=job.pk)
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
            RegistrationEvent.objects.create(
                user_id=current.user_id,
                verification=current,
                kind=RegistrationEvent.Kind.MAIL_SENT
                if delivered
                else RegistrationEvent.Kind.MAIL_FAILED,
            )
        sent += int(delivered)
        failed += int(not delivered)
    return sent, failed
