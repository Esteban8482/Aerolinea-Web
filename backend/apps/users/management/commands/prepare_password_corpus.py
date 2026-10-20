from django.core.management.base import BaseCommand, CommandError

from apps.users.password_corpus import prepare_corpus


class Command(BaseCommand):
    help = "Prepara un corpus local SHA1:COUNT ordenado por hash, sin consultar servicios externos."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--destination", required=True)
        parser.add_argument("--label", required=True)
        parser.add_argument("--synthetic", action="store_true")

    def handle(self, *args, **options):
        try:
            count = prepare_corpus(
                options["source"],
                options["destination"],
                label=options["label"],
                synthetic=options["synthetic"],
            )
        except (ValueError, OSError):
            raise CommandError(
                "No se pudo preparar el corpus; revisa formato, orden y destino nuevo."
            ) from None
        self.stdout.write(f"Corpus preparado: {count} registros.")
