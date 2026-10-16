import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
timeout = 30
# Sin query strings, direcciones, cookies ni cabeceras en los access logs.
accesslog = "-"
access_log_format = "%(m)s %(s)s %(L)s"
errorlog = "-"
capture_output = False

# Los errores del servidor tampoco deben volcar argumentos o excepciones con datos.
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "safe": {"()": "config.logging.SafeEventFormatter"},
        "access": {"format": "%(message)s"},
    },
    "handlers": {
        "error": {"class": "logging.StreamHandler", "formatter": "safe"},
        "access": {"class": "logging.StreamHandler", "formatter": "access"},
    },
    "root": {"handlers": ["error"], "level": "INFO"},
    "loggers": {
        "gunicorn.error": {"handlers": ["error"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}
