from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Persistencia de credenciales; los flujos de cuenta pertenecen a servicios."""

    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email.strip(), role__in=("CLIENTE", "ADMINISTRADOR"))

    async def aget_by_natural_key(self, email):
        return await self.aget(email__iexact=email.strip(), role__in=("CLIENTE", "ADMINISTRADOR"))

    def create_user(self, email, password=None, role="CLIENTE", **extra_fields):
        if role not in ("CLIENTE", "ADMINISTRADOR"):
            raise ValueError("create_user solo admite clientes o administradores.")
        user = self.model(email=email.strip().lower() if email else None, role=role, **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_root(self, root_id, password, email=None):
        if not password:
            raise ValueError("Root requiere una contraseña.")
        user = self.model(
            root_id=root_id.strip(), email=email.strip().lower() if email else None, role="ROOT"
        )
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user
