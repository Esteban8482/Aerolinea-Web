from .base import *  # noqa: F403
from .environment import database, required

env.read_env(BASE_DIR.parent / ".env")
SECRET_KEY = required(env, "DJANGO_SECRET_KEY")
DATABASES = {"default": database(env)}
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
DEBUG = env.bool("DJANGO_DEBUG", default=True)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@example.invalid"
API_DOCUMENTATION_ENABLED = True
