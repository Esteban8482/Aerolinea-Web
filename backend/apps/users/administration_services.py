"""Operaciones de HU-009; las consultas externas preceden a los bloqueos de datos."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.wallets.models import Wallet

from .administration_serializers import AdministratorCreateSerializer
from .auth_services import private_key
from .errors import EmailAlreadyRegistered
from .models import AdministrationEvent, AdministratorNotification, User
from .password_check import validate_registration_password


def administration_event(*, kind, action, actor=None, target=None, origin=""):
    return AdministrationEvent.objects.create(
        actor=actor if actor is not None and actor.is_authenticated else None,
        target=target,
        created_at=timezone.now(),
        kind=kind,
        action=action,
        origin_key=private_key("origin", origin) if origin else "",
    )


def root_user(actor, *, lock=False):
    if actor is None or not actor.is_authenticated:
        return None
    users = User.objects.filter(pk=actor.pk, role=User.Role.ROOT, is_active=True)
    if lock:
        users = users.select_for_update()
    return users.first()


def deny_root_action(actor, *, action, origin):
    administration_event(
        kind=AdministrationEvent.Kind.DENIED, action=action, actor=actor, origin=origin
    )
    raise PermissionDenied()


def check_new_password(password, user):
    try:
        validate_password(password, user=user)
        validate_registration_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": exc.messages}) from None


def create_administrator(*, actor, data, origin):
    if root_user(actor) is None:
        deny_root_action(actor, action=AdministrationEvent.Action.CREATE, origin=origin)
    serializer = AdministratorCreateSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    attrs = dict(serializer.validated_data)
    password = attrs.pop("password")
    attrs.pop("phone", "")
    user = User(
        **attrs,
        role=User.Role.ADMINISTRADOR,
        is_active=True,
        is_staff=False,
        is_superuser=False,
        is_email_verified=False,
    )
    user.full_clean(exclude=["password"], validate_unique=False, validate_constraints=False)
    check_new_password(password, user)
    user.set_password(password)
    lost_access = False
    try:
        with transaction.atomic():
            root = root_user(actor, lock=True)
            if root is None:
                lost_access = True
            else:
                user.save(force_insert=True)
                Wallet.objects.create(user=user)
                now = timezone.now()
                AdministratorNotification.objects.create(
                    user=user, recipient=user.email, created_at=now, next_attempt_at=now
                )
                administration_event(
                    kind=AdministrationEvent.Kind.CREATED,
                    action=AdministrationEvent.Action.CREATE,
                    actor=root,
                    target=user,
                    origin=origin,
                )
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
        if constraint in {"users_user_email_243f6e77_uniq", "users_email_ci_unique"}:
            raise EmailAlreadyRegistered() from None
        raise
    if lost_access:
        # La denegación debe sobrevivir al aborto de la operación de negocio.
        deny_root_action(actor, action=AdministrationEvent.Action.CREATE, origin=origin)
    return user


# DEC-21/22: independientes de los límites de login/recuperación de HU-008.
CREATE_PER_ROOT = 10
CREATE_PER_ORIGIN = 20
ROOT_PASSWORD_WINDOW = 900
ROOT_PASSWORD_FAILURES = 5
ROOT_PASSWORD_BLOCK = 900
ROOT_PASSWORD_PER_ORIGIN = 30


def _prepare_password_guard(guard):
    import math

    from django.utils import timezone
    from rest_framework.exceptions import Throttled

    now = timezone.now()
    if guard.blocked_until and now < guard.blocked_until:
        raise Throttled(wait=max(1, math.ceil((guard.blocked_until - now).total_seconds())))
    if guard.blocked_until:
        guard.failures = []
        guard.blocked_until = None
    guard.failures = [t for t in guard.failures if t > now.timestamp() - ROOT_PASSWORD_WINDOW]
    return now


def change_root_password(*, actor, current_password, password, origin):
    from datetime import timedelta

    from django.contrib.auth.hashers import check_password
    from rest_framework.exceptions import Throttled

    from .errors import CredentialsChanged, CurrentPasswordInvalid
    from .models import LoginGuard

    action = AdministrationEvent.Action.PASSWORD
    if root_user(actor) is None:
        deny_root_action(actor, action=action, origin=origin)
    key = private_key("HU009.root-password", str(actor.pk))
    LoginGuard.objects.get_or_create(key=key)
    error = None
    with transaction.atomic():
        guard = LoginGuard.objects.select_for_update().get(key=key)
        now = _prepare_password_guard(guard)
        root = root_user(actor, lock=True)
        if root is not None:
            # Sin setter: comprobar la clave actual no puede rehashear ni invalidar sesiones
            # antes de saber si la política y el proveedor aceptan la nueva contraseña.
            if not check_password(current_password, root.password):
                guard.failures.append(now.timestamp())
                administration_event(
                    kind=AdministrationEvent.Kind.PASSWORD_FAILED,
                    action=action,
                    actor=root,
                    origin=origin,
                )
                error = CurrentPasswordInvalid()
                if len(guard.failures) >= ROOT_PASSWORD_FAILURES:
                    guard.blocked_until = now + timedelta(seconds=ROOT_PASSWORD_BLOCK)
                    administration_event(
                        kind=AdministrationEvent.Kind.PASSWORD_BLOCKED,
                        action=action,
                        actor=root,
                        origin=origin,
                    )
                    error = Throttled(wait=ROOT_PASSWORD_BLOCK)
            guard.save(update_fields=["failures", "blocked_until"])
    if root is None:
        deny_root_action(actor, action=action, origin=origin)
    if error:
        raise error
    previous_hash = root.password
    # La consulta externa está fuera de ambas transacciones y no mantiene bloqueos.
    check_new_password(password, root)
    with transaction.atomic():
        guard = LoginGuard.objects.select_for_update().get(key=key)
        _prepare_password_guard(guard)
        root = root_user(actor, lock=True)
        if root is not None:
            if root.password != previous_hash:
                raise CredentialsChanged()
            try:
                validate_password(password, user=root)
            except DjangoValidationError as exc:
                raise ValidationError({"password": exc.messages}) from None
            root.set_password(password)
            root.save(update_fields=["password"])
            guard.failures = []
            guard.blocked_until = None
            guard.save(update_fields=["failures", "blocked_until"])
            administration_event(
                kind=AdministrationEvent.Kind.PASSWORD_CHANGED,
                action=action,
                actor=root,
                target=root,
                origin=origin,
            )
    if root is None:
        deny_root_action(actor, action=action, origin=origin)
    # No conservar la sesión actual con update_session_auth_hash: todas se invalidan
    # por el mecanismo de Django en su siguiente petición, como se aprobó para HU-009.


def change_administrator_password(*, actor, admin_id, password, origin):
    action = AdministrationEvent.Action.PASSWORD
    if root_user(actor) is None:
        deny_root_action(actor, action=action, origin=origin)
    try:
        admin = User.objects.get(pk=admin_id, role=User.Role.ADMINISTRADOR, is_active=True)
    except User.DoesNotExist:
        raise ValidationError({"admin_id": ["No se encontró el administrador especificado."]})
    check_new_password(password, admin)
    with transaction.atomic():
        admin.set_password(password)
        admin.save(update_fields=["password"])
        administration_event(
            kind=AdministrationEvent.Kind.PASSWORD_CHANGED,
            action=action,
            actor=actor,
            target=admin,
            origin=origin,
        )
    return admin
