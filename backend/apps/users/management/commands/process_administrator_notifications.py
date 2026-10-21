from django.core.management.base import BaseCommand, CommandError

from apps.users.administrator_mail import process_administrator_notifications


class Command(BaseCommand):
    help = "Procesa avisos de alta confirmados y recupera arrendamientos vencidos."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--batch-size debe estar entre 1 y 1000.")
        sent, failed = process_administrator_notifications(batch_size=size)
        self.stdout.write(f"Enviados: {sent}; fallidos: {failed}.")
