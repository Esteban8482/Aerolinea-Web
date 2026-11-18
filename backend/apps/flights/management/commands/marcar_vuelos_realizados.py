from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.flights.models import EstadoVuelo, Vuelo


class Command(BaseCommand):
    help = (
        "Marca como REALIZADO los vuelos programados cuya llegada_utc ya pasó. "
        "Pensado para ejecutarse de forma programada (cron/scheduler); es idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--batch-size debe estar entre 1 y 1000.")

        with transaction.atomic():
            ids = list(
                Vuelo.objects.select_for_update(skip_locked=True)
                .filter(estado=EstadoVuelo.PROGRAMADO, llegada_utc__lte=timezone.now())
                .order_by("llegada_utc")
                .values_list("id", flat=True)[:size]
            )
            marcados = Vuelo.objects.filter(id__in=ids).update(estado=EstadoVuelo.REALIZADO)

        self.stdout.write(f"Vuelos marcados como realizados: {marcados}.")
