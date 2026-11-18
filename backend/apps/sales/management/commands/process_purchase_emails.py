from django.core.management.base import BaseCommand, CommandError

from apps.sales.mail import process_purchase_emails


class Command(BaseCommand):
    help = (
        "Envía los códigos de reserva pendientes a los viajeros (outbox de compras, HU-013). "
        "Pensado para ejecutarse de forma programada; es idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--batch-size debe estar entre 1 y 1000.")
        sent, failed = process_purchase_emails(batch_size=size)
        self.stdout.write(f"Enviados: {sent}; fallidos: {failed}.")
