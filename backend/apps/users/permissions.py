from rest_framework.permissions import BasePermission


class HasVerifiedEmail(BasePermission):
    """Combinar con autenticación, rol y propiedad en cada HU protegida."""

    message = "Debes verificar tu correo electrónico para realizar esta operación."
    code = "email_not_verified"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_email_verified)
