from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Aplica migraciones e inicializa referencias sin recrear la base ni datos de usuario."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False)
        call_command("load_reference_catalogues", if_needed=True)
        call_command("check")
