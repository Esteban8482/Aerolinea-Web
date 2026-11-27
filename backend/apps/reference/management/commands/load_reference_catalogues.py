from django.core.management.base import BaseCommand, CommandError

from apps.reference.importer import import_geography


class Command(BaseCommand):
    help = "Importa geografía verificada y opciones estáticas sin borrar historia."

    def add_arguments(self, parser):
        parser.add_argument("--if-needed", action="store_true")

    def handle(self, *args, **options):
        if options["if_needed"]:
            import json
            from pathlib import Path

            from apps.reference import importer
            from apps.reference.models import CatalogueLoad

            manifest = json.loads(
                (Path(importer.__file__).parent / "data" / "manifest.json").read_text()
            )
            if CatalogueLoad.objects.filter(name="geography", checksum=manifest["sha256"]).exists():
                self.stdout.write("Catálogo geográfico ya inicializado en esta versión.")
                return
        try:
            counts = import_geography()
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS(str(counts)))
