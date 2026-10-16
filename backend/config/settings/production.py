from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .environment import database, required

DEBUG = False
SECRET_KEY = required(env, "DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured(
        "Production DJANGO_SECRET_KEY must be at least 50 characters with sufficient entropy."
    )
DATABASES = {"default": database(env)}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or any("*" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Configura hosts de producción explícitos, sin comodines.")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") or "*" in origin for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("Configura orígenes CSRF explícitos con HTTPS.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS")
if SECURE_HSTS_SECONDS <= 0:
    raise ImproperlyConfigured("DJANGO_SECURE_HSTS_SECONDS debe ser positivo.")
# No comprometer todos los subdominios ni solicitar preload sin decisión de despliegue.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
if env.bool("DJANGO_TRUST_PROXY", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = required(env, "EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_HOST_USER = required(env, "EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = required(env, "EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL")
if EMAIL_USE_TLS == EMAIL_USE_SSL:
    raise ImproperlyConfigured("SMTP requiere exactamente uno de TLS o SSL.")
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = required(env, "DEFAULT_FROM_EMAIL")
API_DOCUMENTATION_ENABLED = False
