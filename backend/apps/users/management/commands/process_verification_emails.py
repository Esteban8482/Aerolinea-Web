from django.core.management.base import BaseCommand, CommandError

from apps.users.mail import process_verification_emails


class Command(BaseCommand):
    help = (
        "Procesa un lote de correos de verificación confirmados y recupera arrendamientos vencidos."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--batch-size debe estar entre 1 y 1000.")
        sent, failed = process_verification_emails(batch_size=size)
        self.stdout.write(f"Enviados: {sent}; fallidos: {failed}.")
