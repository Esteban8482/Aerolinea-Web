from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import User

# Credenciales sintéticas definidas en cargar_datos_demostracion.py.
KNOWN_DEV_CREDENTIALS = {
    "admin.demo@aerolinea.local": "AdminDemo2026*",
    "carlos.viajero@aerolinea.local": "CarlosViajero2026*",
    "maria.turista@aerolinea.local": "MariaTurista2026*",
}

UNKNOWN_PASSWORD = "(no conocida: definida manualmente o por flujo de registro)"

ROLE_SECTIONS = [
    (User.Role.ROOT, "ROOT"),
    (User.Role.ADMINISTRADOR, "ADMINISTRADORES"),
    (User.Role.CLIENTE, "CLIENTES"),
]


class Command(BaseCommand):
    help = "Herramienta de desarrollo: lista usuarios por rol con sus credenciales conocidas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Restablece las contrasenas de los usuarios demo a sus valores sinteticos.",
        )

    def handle(self, *args, **options):
        del args
        if not settings.DEBUG:
            raise CommandError(
                "Este comando es exclusivo de desarrollo y no esta disponible con DEBUG=False."
            )

        if options["reset_demo"]:
            self._reset_demo_passwords()

        self.stdout.write(
            self.style.WARNING(
                "HERRAMIENTA DE DESARROLLO - Las contrasenas se almacenan con hash;\n"
                "solo se muestran las credenciales sinteticas conocidas que aun coinciden."
            )
        )

        for role, title in ROLE_SECTIONS:
            users = User.objects.filter(role=role).order_by("pk")
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(f"== {title} ({users.count()}) =="))
            if not users:
                self.stdout.write("  (sin usuarios)")
                continue
            for user in users:
                self._print_user(user)

        self.stdout.write("")
        self.stdout.write("Ayuda rapida:")
        self.stdout.write(
            "  - Crear datos demo:        python manage.py cargar_datos_demostracion"
        )
        self.stdout.write(
            "  - Restablecer claves demo: python manage.py list_dev_users --reset-demo"
        )
        self.stdout.write("  - Crear cuenta ROOT:       python manage.py create_root --root-id root")

    def _print_user(self, user):
        if user.role == User.Role.ROOT:
            identifier = f"root_id: {user.root_id}"
            if user.email:
                identifier += f"  |  correo: {user.email}"
        else:
            identifier = f"correo: {user.email}"

        password = self._known_password(user)
        verified = "si" if user.is_email_verified else "no"
        self.stdout.write(f"  - {identifier}")
        self.stdout.write(f"      password: {password}")
        self.stdout.write(f"      correo verificado: {verified}")

    def _known_password(self, user):
        candidate = KNOWN_DEV_CREDENTIALS.get(user.email)
        if candidate and user.check_password(candidate):
            return candidate
        return UNKNOWN_PASSWORD

    def _reset_demo_passwords(self):
        reset = 0
        for email, password in KNOWN_DEV_CREDENTIALS.items():
            user = User.objects.filter(email=email).first()
            if user and not user.check_password(password):
                user.set_password(password)
                user.save(update_fields=["password"])
                reset += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Contrasenas demo restablecidas a sus valores sinteticos: {reset} actualizada(s)."
            )
        )
