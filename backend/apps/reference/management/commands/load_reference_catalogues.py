from django.core.management.base import BaseCommand, CommandError

from apps.reference.importer import import_geography


class Command(BaseCommand):
    help = "Importa geografía verificada y opciones estáticas sin borrar historia."

    def handle(self, *args, **options):
        try:
            counts = import_geography()
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS(str(counts)))
