from .base import *  # noqa: F403
from .environment import database

DEBUG = False
SECRET_KEY = "test-only-key-with-no-access-to-any-real-environment"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": database(env, "TEST_DATABASE_URL")}
if not DATABASES["default"]["NAME"].startswith("test_"):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("TEST_DATABASE_URL debe apuntar a una base exclusiva test_*.")
DATABASES["default"]["TEST"] = {"NAME": "test_" + DATABASES["default"]["NAME"]}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@example.invalid"
API_DOCUMENTATION_ENABLED = True
