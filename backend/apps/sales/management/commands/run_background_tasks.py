"""Small durable-outbox scheduler; no broker or external task infrastructure."""

import logging
import signal
from threading import Event

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

TASKS = (
    "liberar_reservas_vencidas",
    "process_verification_emails",
    "process_recovery_emails",
    "process_administrator_notifications",
    "process_purchase_emails",
    "process_journey_emails",
)


class Command(BaseCommand):
    help = "Procesa expiraciones y notificaciones durables; admite --once para supervisión externa."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=int, default=30)

    def handle(self, *args, **options):
        if options["interval"] < 5:
            raise CommandError("El intervalo mínimo es cinco segundos.")
        stop = Event()
        previous = {}
        if not options["once"]:
            for signum in (signal.SIGTERM, signal.SIGINT):
                previous[signum] = signal.signal(signum, lambda *_: stop.set())
        try:
            while not stop.is_set():
                failures = []
                for name in TASKS:
                    close_old_connections()
                    try:
                        call_command(name, batch_size=100, stdout=self.stdout, stderr=self.stderr)
                    except Exception:
                        # Log the task and exception type; do not log email bodies or credentials.
                        logging.getLogger(__name__).error("background_task_failed task=%s", name)
                        failures.append(name)
                if options["once"]:
                    if failures:
                        raise CommandError("Fallaron tareas: " + ", ".join(failures))
                    return
                stop.wait(options["interval"])
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
