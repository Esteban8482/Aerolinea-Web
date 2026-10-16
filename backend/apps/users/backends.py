from asgiref.sync import sync_to_async
from django.contrib.auth.backends import ModelBackend

from .models import User


class AccountBackend(ModelBackend):
    """Credenciales explícitas para evitar colisiones entre ID root y correo."""

    def authenticate(self, request, username=None, password=None, root_id=None, **kwargs):
        if root_id is None:
            return super().authenticate(request, username=username, password=password, **kwargs)
        if password is None or username is not None or kwargs.get("email") is not None:
            return None
        try:
            user = User.objects.get(root_id=root_id.strip(), role=User.Role.ROOT)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    async def aauthenticate(self, request, username=None, password=None, root_id=None, **kwargs):
        return await sync_to_async(self.authenticate, thread_sensitive=True)(
            request, username=username, password=password, root_id=root_id, **kwargs
        )
