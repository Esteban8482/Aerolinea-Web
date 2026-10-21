"""Casos de uso de HU-008; sin red dentro de las operaciones atómicas."""

import math
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import NotAuthenticated, Throttled, ValidationError

from .errors import ExpiredRecovery, InvalidCredentials, InvalidRecovery, UsedRecovery
from .models import AccountSession, AuthenticationEvent, LoginGuard, PasswordRecovery, User
from .password_check import validate_registration_password

IDLE_SECONDS = 1800
ACTIVITY_INTERVAL_SECONDS = 60
LOGIN_WINDOW_SECONDS = 900
LOGIN_FAILURES = 5
LOGIN_BLOCK_SECONDS = 900
LOGIN_PER_ORIGIN = 30
RECOVERY_LIFETIME_SECONDS = 1800
RECOVERY_PER_ACCOUNT = 3
RECOVERY_PER_ORIGIN = 20
RECOVERY_INTERVAL_SECONDS = 60
RECOVERY_SALT = "users.HU008.password-recovery.v1"


def private_key(scope, value):
    return salted_hmac("HU008." + scope, value, algorithm="sha256").hexdigest()


def audit(kind, *, user=None, recovery=None, subject="", origin=""):
    AuthenticationEvent.objects.create(
        kind=kind,
        user=user,
        recovery=recovery,
        subject_key=subject,
        origin_key=private_key("origin", origin) if origin else "",
    )


def session_state(user):
    authenticated = user.is_authenticated
    return {
        "authenticated": authenticated,
        "role": user.role if authenticated else None,
        "is_email_verified": bool(authenticated and user.is_email_verified),
    }


def start_session(*, request, credentials, origin):
    mode = "email" if "email" in credentials else "root_id"
    key = private_key("login." + mode, credentials[mode])
    LoginGuard.objects.get_or_create(key=key)
    error = None
    with transaction.atomic():
        guard = LoginGuard.objects.select_for_update().get(key=key)
        now = timezone.now()
        if guard.blocked_until and now < guard.blocked_until:
            error = Throttled(wait=max(1, math.ceil((guard.blocked_until - now).total_seconds())))
        else:
            if guard.blocked_until:
                guard.failures = []
                guard.blocked_until = None
            guard.failures = [
                t for t in guard.failures if t > now.timestamp() - LOGIN_WINDOW_SECONDS
            ]
            user = authenticate(request, **credentials)
            if user:
                # Cerrar la carrera con un restablecimiento o desactivación concurrente.
                current = User.objects.select_for_update().get(pk=user.pk)
                if not current.is_active or current.password != user.password:
                    user = None
                else:
                    user = current
            if user is None:
                guard.failures.append(now.timestamp())
                audit(AuthenticationEvent.Kind.LOGIN_FAILED, subject=key, origin=origin)
                error = InvalidCredentials()
                if len(guard.failures) >= LOGIN_FAILURES:
                    guard.blocked_until = now + timedelta(seconds=LOGIN_BLOCK_SECONDS)
                    audit(AuthenticationEvent.Kind.LOGIN_BLOCKED, subject=key, origin=origin)
                    error = Throttled(wait=LOGIN_BLOCK_SECONDS)
            else:
                guard.failures = []
                old_key = request.session.session_key
                login(request, user)
                # Django ya rota al pasar de visitante a usuario; forzar también al reautenticar.
                if request.session.session_key == old_key:
                    request.session.cycle_key()
                request.session.set_expiry(now + timedelta(seconds=IDLE_SECONDS))
                request.session.save()
                AccountSession.objects.create(
                    session_id=request.session.session_key, user=user, last_activity_at=now
                )
                audit(AuthenticationEvent.Kind.LOGIN, user=user, subject=key, origin=origin)
            guard.save(update_fields=["failures", "blocked_until"])
    # Los fallos y bloqueos deben confirmarse, no revertirse al lanzar el error HTTP.
    if error:
        raise error
    return session_state(user)


def end_session(*, request, origin):
    with transaction.atomic():
        if request.user.is_authenticated:
            audit(AuthenticationEvent.Kind.LOGOUT, user=request.user, origin=origin)
        logout(request)


def record_activity(*, request):
    now = timezone.now()
    with transaction.atomic():
        state = (
            AccountSession.objects.select_for_update()
            .filter(session_id=request.session.session_key, user=request.user)
            .first()
        )
        if state is None or now >= state.last_activity_at + timedelta(seconds=IDLE_SECONDS):
            raise NotAuthenticated()
        elapsed = (now - state.last_activity_at).total_seconds()
        if elapsed < ACTIVITY_INTERVAL_SECONDS:
            raise Throttled(wait=max(1, math.ceil(ACTIVITY_INTERVAL_SECONDS - elapsed)))
        state.last_activity_at = now
        state.save(update_fields=["last_activity_at"])
        request.session.set_expiry(now + timedelta(seconds=IDLE_SECONDS))
        # Guardar bajo el mismo bloqueo: logout concurrente no puede resucitar la sesión.
        request.session.save()


def password_fingerprint(user):
    return private_key("password-version", user.password)


def recovery_token(recovery):
    return signing.Signer(salt=RECOVERY_SALT).sign_object(
        {"recovery": recovery.pk, "account": recovery.user_id}
    )


def request_recovery(*, email, origin):
    with transaction.atomic():
        user = User.objects.select_for_update().filter(email=email, is_active=True).first()
        if user is None or not user.has_usable_password():
            return
        now = timezone.now()
        PasswordRecovery.objects.filter(
            user=user, consumed_at__isnull=True, superseded_at__isnull=True
        ).update(superseded_at=now)
        job = PasswordRecovery.objects.create(
            user=user,
            recipient=user.email,
            password_fingerprint=password_fingerprint(user),
            created_at=now,
            expires_at=now + timedelta(seconds=RECOVERY_LIFETIME_SECONDS),
            next_attempt_at=now,
        )
        audit(AuthenticationEvent.Kind.RECOVERY_REQUESTED, user=user, recovery=job, origin=origin)


def _recovery_ids(token):
    try:
        value = signing.Signer(salt=RECOVERY_SALT).unsign_object(token)
        if (
            not isinstance(value, dict)
            or set(value) != {"recovery", "account"}
            or any(type(item) is not int or not 0 < item < 2**63 for item in value.values())
        ):
            raise InvalidRecovery()
        return value["account"], value["recovery"]
    except (signing.BadSignature, ValueError, TypeError, UnicodeError):
        raise InvalidRecovery() from None


def _check_recovery(user, job):
    if (
        user is None
        or job is None
        or job.superseded_at
        or not user.is_active
        or not user.email
        or job.recipient != user.email
    ):
        raise InvalidRecovery()
    if job.consumed_at:
        raise UsedRecovery()
    if timezone.now() >= job.expires_at:
        raise ExpiredRecovery()
    if not constant_time_compare(job.password_fingerprint, password_fingerprint(user)):
        raise InvalidRecovery()


def reset_password(*, token, password, origin):
    user_id, job_id = _recovery_ids(token)
    user = User.objects.filter(pk=user_id).first()
    job = PasswordRecovery.objects.filter(pk=job_id, user_id=user_id).first()
    _check_recovery(user, job)
    try:
        validate_password(password, user=user)
        # La única llamada externa ocurre sin atomic ni bloqueos; su fallo no consume el enlace.
        validate_registration_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": exc.messages}) from None
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user_id)
        job = PasswordRecovery.objects.select_for_update().get(pk=job_id, user=user)
        _check_recovery(user, job)
        # Revalidar atributos de usuario que pudieron cambiar durante la consulta externa.
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages}) from None
        user.set_password(password)
        user.save(update_fields=["password"])
        job.consumed_at = timezone.now()
        job.save(update_fields=["consumed_at"])
        audit(AuthenticationEvent.Kind.PASSWORD_RESET, user=user, recovery=job, origin=origin)
        # Django compara el hash de autenticación en la siguiente petición de cada sesión.
        # No llamar update_session_auth_hash: tampoco se conserva la sesión del solicitante.
