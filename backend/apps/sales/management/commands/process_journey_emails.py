from django.core.management.base import BaseCommand, CommandError

from apps.sales.journey_mail import process_journey_emails


class Command(BaseCommand):
    help = (
        "Procesa avisos de cambios, reembolsos, acceso rápido y pasabordos pendientes. "
        "Pensado para ejecutarse de forma programada; es idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--batch-size debe estar entre 1 y 1000.")
        sent, failed = process_journey_emails(batch_size=size)
        self.stdout.write(f"Enviados: {sent}; fallidos: {failed}.")
