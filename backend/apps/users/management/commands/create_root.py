from getpass import getpass

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import User
from apps.users.services import provision_root


class Command(BaseCommand):
    help = "Crear root y su billetera sin contraseña predeterminada."

    def add_arguments(self, parser):
        parser.add_argument("--root-id", required=True, help="Identificador de acceso de root.")
        parser.add_argument("--email", default=None, help="Correo opcional de root.")

    def handle(self, *args, **options):
        del args
        root_id = options["root_id"].strip()
        if not root_id:
            raise CommandError("El identificador root no puede estar vacío.")
        if User.objects.filter(role=User.Role.ROOT).exists():
            self.stdout.write("Ya existe la cuenta ROOT; no se modificó.")
            return

        password = getpass("Contraseña: ")
        confirmation = getpass("Confirme la contraseña: ")
        if password != confirmation:
            raise CommandError("Las contraseñas no coinciden.")

        try:
            _, created = provision_root(root_id=root_id, password=password, email=options["email"])
        except (ValueError, ValidationError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("Cuenta ROOT creada con su billetera." if created else "ROOT ya existe.")
