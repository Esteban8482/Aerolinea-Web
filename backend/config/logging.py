import logging


class SafeEventFormatter(logging.Formatter):
    """No serializar mensajes arbitrarios, URLs, SQL, cuerpos ni excepciones."""

    EVENTS = frozenset({"database_unavailable", "unhandled_api_error"})

    def format(self, record):
        event = record.msg if isinstance(record.msg, str) and record.msg in self.EVENTS else "event"
        status = getattr(record, "status_code", None)
        status_text = f" status={status}" if isinstance(status, int) else ""
        return f"{self.formatTime(record)} {record.levelname} {record.name} {event}{status_text}"
