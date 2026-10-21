from rest_framework.permissions import BasePermission


class HasVerifiedEmail(BasePermission):
    """Combinar con autenticación, rol y propiedad en cada HU protegida."""

    message = "Debes verificar tu correo electrónico para realizar esta operación."
    code = "email_not_verified"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_email_verified)


class IsRoot(BasePermission):
    """Solo el rol ROOT activo, sin sustituciones por privilegios técnicos."""

    message = "Esta operación requiere una sesión de ROOT."

    def has_permission(self, request, view):
        from .administration_services import administration_event
        from .limits import request_origin
        from .models import AdministrationEvent, User

        user = request.user
        allowed = bool(
            user and user.is_authenticated and user.is_active and user.role == User.Role.ROOT
        )
        if not allowed and getattr(view, "administration_action", None):
            administration_event(
                kind=AdministrationEvent.Kind.DENIED,
                action=view.administration_action,
                actor=user,
                origin=request_origin(request),
            )
        return allowed


class IsAdministrator(BasePermission):
    """Permiso reutilizable para las futuras HU de vuelos y promociones."""

    def has_permission(self, request, view):
        from .models import User

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == User.Role.ADMINISTRADOR
        )


class IsClient(BasePermission):
    """Combinar con verificación y propiedad en futuras reservas y compras."""

    def has_permission(self, request, view):
        from .models import User

        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and user.role == User.Role.CLIENTE
        )
