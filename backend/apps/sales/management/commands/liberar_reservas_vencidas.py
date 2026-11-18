from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.sales.models import EstadoReserva, Reserva
from apps.sales.services import liberar_reserva_si_vencida


class Command(BaseCommand):
    help = (
        "Libera las reservas vigentes que alcanzaron su límite de vigencia y devuelve "
        "sus cupos al vuelo (DEC-07). Pensado para ejecutarse de forma programada; es idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["batch_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--batch-size debe estar entre 1 y 1000.")

        candidatas = Reserva.objects.filter(
            estado=EstadoReserva.VIGENTE,
            limite_vigencia__lte=timezone.now(),
        ).order_by("limite_vigencia")[:size]

        liberadas = 0
        for reserva in candidatas:
            if liberar_reserva_si_vencida(reserva):
                liberadas += 1

        self.stdout.write(f"Reservas liberadas: {liberadas}.")
