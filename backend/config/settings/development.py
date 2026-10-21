from .base import *  # noqa: F403
from .environment import database, required

env.read_env(BASE_DIR.parent / ".env")
EMAIL_VERIFICATION_FRONTEND_URL = env("EMAIL_VERIFICATION_FRONTEND_URL", default="")
REGISTRATION_PRODUCTION = False
REGISTRATION_POLICY_REFERENCE = env("REGISTRATION_POLICY_REFERENCE", default="DOCUMENTO-DE-PRUEBA")
REGISTRATION_POLICY_VERSION = env("REGISTRATION_POLICY_VERSION", default="test-v1")
REGISTRATION_POLICY_URL = env(
    "REGISTRATION_POLICY_URL",
    default="http://localhost:8000/api/v1/auth/registration-policy/test-document/",
)
# Desarrollo no presenta una política de prueba como aprobación legal.
REGISTRATION_POLICY_APPROVED = False
REGISTRATION_POLICY_IS_TEST = True
PRIVATE_MEDIA_ROOT = env("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private-media"))
REGISTRATION_TRUSTED_PROXIES = env.list("REGISTRATION_TRUSTED_PROXIES", default=[])
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

PASSWORD_RECOVERY_FRONTEND_URL = env("PASSWORD_RECOVERY_FRONTEND_URL", default="")
