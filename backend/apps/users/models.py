from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower, Trim
from django.utils import timezone

from .images import PrivateProfileStorage
from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ROOT = "ROOT", "Root"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        CLIENTE = "CLIENTE", "Cliente"

    # Nombre de perfil (RF-USU-05), independiente de las credenciales.
    username = models.CharField(max_length=40, blank=True)
    root_id = models.CharField(max_length=254, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CLIENTE)
    is_email_verified = models.BooleanField(default=False)
    document_type = models.CharField(max_length=20, blank=True)
    document_number = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    birth_place = models.CharField(max_length=100, blank=True)
    billing_address = models.CharField(max_length=200, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    profile_image_url = models.URLField(max_length=255, blank=True)
    profile_image = models.FileField(storage=PrivateProfileStorage(), blank=True, max_length=255)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.role}:{self.pk}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=("ROOT", "ADMINISTRADOR", "CLIENTE")),
                name="users_role_is_supported",
            ),
            models.UniqueConstraint(
                fields=["role"],
                condition=Q(role="ROOT"),
                name="users_single_root_account",
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="users_email_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(role="ROOT") | (Q(email__isnull=False) & ~Q(email="")),
                name="users_non_root_email_required",
            ),
            models.CheckConstraint(
                condition=Q(email__isnull=True) | (~Q(email="") & Q(email=Lower(Trim("email")))),
                name="users_email_normalized",
            ),
            models.CheckConstraint(
                condition=(Q(role="ROOT", root_id__isnull=False) & ~Q(root_id=""))
                | (~Q(role="ROOT") & Q(root_id__isnull=True)),
                name="users_root_identifier_by_role",
            ),
        ]

    def clean(self):
        super().clean()
        self._normalize_identifiers()
        errors = {}
        if self.role != self.Role.ROOT and not self.email:
            errors["email"] = "Este rol requiere correo electrónico."
        if self.role == self.Role.ROOT and not self.root_id:
            errors["root_id"] = "Root requiere un identificador de acceso."
        if self.role != self.Role.ROOT and self.root_id:
            errors["root_id"] = "El identificador root solo corresponde al rol ROOT."
        # RF-USU-06 permite completar posteriormente el perfil del administrador.
        if self.role == self.Role.CLIENTE:
            for field in (
                "username",
                "first_name",
                "last_name",
                "document_number",
                "birth_date",
                "birth_place",
                "billing_address",
                "gender",
            ):
                value = getattr(self, field)
                if not value or (isinstance(value, str) and not value.strip()):
                    errors[field] = "Este dato es obligatorio para el cliente."
        if errors:
            raise ValidationError(errors)

    def _normalize_identifiers(self):
        self.email = self.email.strip().lower() if self.email and self.email.strip() else None
        self.root_id = self.root_id.strip() if self.root_id and self.root_id.strip() else None

    def save(self, *args, **kwargs):
        self._normalize_identifiers()
        return super().save(*args, **kwargs)


class RegistrationConsent(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="registration_consent")
    policy_reference = models.CharField(max_length=200)
    # Consentimientos previos sin versión no reciben una versión ficticia en migración.
    policy_version = models.CharField(max_length=100, null=True)
    policy_url = models.URLField(max_length=500)
    accepted_at = models.DateTimeField(default=timezone.now)


class EmailVerification(models.Model):
    """Intención persistente de envío y consumo; nunca almacena el token firmado."""

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="email_verifications")
    recipient = models.EmailField()
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_id = models.UUIDField(null=True, blank=True)
    last_error = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("created_at")),
                name="users_verification_positive_lifetime",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__lte=models.F("created_at") + timezone.timedelta(hours=24)),
                name="users_verification_max_24h",
            ),
        ]


class RegistrationEvent(models.Model):
    class Kind(models.TextChoices):
        REGISTERED = "registered", "Cuenta registrada"
        VERIFIED = "verified", "Correo verificado"
        MAIL_SENT = "mail_sent", "Correo aceptado por el backend de correo"
        MAIL_FAILED = "mail_failed", "Fallo de correo"
        RESENT = "resent", "Nuevo enlace solicitado"

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    verification = models.ForeignKey(EmailVerification, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    created_at = models.DateTimeField(default=timezone.now)


class RegistrationRateBucket(models.Model):
    """Ventana móvil compartida; la clave no contiene correo ni IP en claro."""

    key = models.CharField(max_length=64, unique=True)
    timestamps = models.JSONField(default=list)
    last_accepted_at = models.DateTimeField(null=True, blank=True)


class LoginGuard(models.Model):
    """Estado por identificador HMAC, incluso cuando la cuenta no existe."""

    key = models.CharField(max_length=64, unique=True)
    failures = models.JSONField(default=list)
    blocked_until = models.DateTimeField(null=True, blank=True)


class AccountSession(models.Model):
    """Actividad compartida de una sesión Django; no representa otro token."""

    session = models.OneToOneField("sessions.Session", primary_key=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_activity_at = models.DateTimeField(default=timezone.now)


class PasswordRecovery(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    recipient = models.EmailField()
    password_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_id = models.UUIDField(null=True, blank=True)
    last_error = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("created_at")),
                name="users_recovery_positive_lifetime",
            ),
            models.CheckConstraint(
                condition=Q(
                    expires_at__lte=models.F("created_at") + timezone.timedelta(minutes=30)
                ),
                name="users_recovery_max_30m",
            ),
        ]


class AuthenticationEvent(models.Model):
    class Kind(models.TextChoices):
        LOGIN = "login", "Inicio de sesión"
        LOGIN_FAILED = "login_failed", "Autenticación fallida"
        LOGIN_BLOCKED = "login_blocked", "Identificador bloqueado"
        LOGOUT = "logout", "Cierre de sesión"
        SESSION_EXPIRED = "session_expired", "Sesión vencida por inactividad"
        RECOVERY_REQUESTED = "recovery_requested", "Recuperación solicitada"
        PASSWORD_RESET = "password_reset", "Contraseña restablecida"
        MAIL_SENT = "mail_sent", "Correo aceptado"
        MAIL_FAILED = "mail_failed", "Fallo de correo"

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    recovery = models.ForeignKey(PasswordRecovery, on_delete=models.PROTECT, null=True)
    kind = models.CharField(max_length=25, choices=Kind.choices)
    subject_key = models.CharField(max_length=64, blank=True)
    origin_key = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class AdministratorNotification(models.Model):
    """Aviso de alta, sin contraseña inicial ni token; entrega posterior al commit."""

    user = models.OneToOneField(User, on_delete=models.PROTECT)
    recipient = models.EmailField()
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_id = models.UUIDField(null=True, blank=True)
    last_error = models.CharField(max_length=30, blank=True)


class AdministrationEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED = "administrator_created", "Administrador creado"
        DENIED = "access_denied", "Acceso denegado"
        PASSWORD_CHANGED = "root_password_changed", "Contraseña de ROOT cambiada"
        PASSWORD_FAILED = "root_password_failed", "Contraseña actual incorrecta"
        PASSWORD_BLOCKED = "root_password_blocked", "Cambio de contraseña bloqueado"
        MAIL_SENT = "mail_sent", "Aviso aceptado por correo"
        MAIL_FAILED = "mail_failed", "Fallo del aviso de alta"

    class Action(models.TextChoices):
        CREATE = "create_administrator", "Crear administrador"
        LIST = "list_administrators", "Consultar administradores"
        PASSWORD = "change_root_password", "Cambiar contraseña propia de ROOT"
        MAIL = "notify_administrator", "Procesar aviso de alta"

    actor = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="administration_actions"
    )
    target = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="administration_events"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    action = models.CharField(max_length=30, choices=Action.choices)
    origin_key = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
