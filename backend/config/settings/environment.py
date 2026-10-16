import environ
from django.core.exceptions import ImproperlyConfigured


def required(env, name):
    value = env(name)
    if not value.strip():
        raise ImproperlyConfigured(f"{name} no puede estar vacío.")
    return value


def database(env, variable="DATABASE_URL"):
    # Nunca aceptar SQLite ni convertir un error de configuración en otra base.
    config = environ.Env.db_url_config(required(env, variable))
    if config.get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured(f"{variable} debe utilizar PostgreSQL.")
    if not all(config.get(key) for key in ("NAME", "USER", "PASSWORD", "HOST")):
        raise ImproperlyConfigured(f"{variable} requiere base, usuario, contraseña y host.")
    config.setdefault("OPTIONS", {})["connect_timeout"] = 3
    config["CONN_MAX_AGE"] = 0
    config["CONN_HEALTH_CHECKS"] = True
    return config
