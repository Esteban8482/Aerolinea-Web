from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from .errors import RegistrationUnavailable


def current_registration_policy():
    reference = settings.REGISTRATION_POLICY_REFERENCE
    version = settings.REGISTRATION_POLICY_VERSION
    url = settings.REGISTRATION_POLICY_URL
    if not reference or not version or not url:
        raise RegistrationUnavailable()
    try:
        URLValidator(schemes=["https"] if settings.REGISTRATION_PRODUCTION else ["http", "https"])(
            url
        )
    except ValidationError:
        raise RegistrationUnavailable() from None
    if settings.REGISTRATION_PRODUCTION and (
        not settings.REGISTRATION_POLICY_APPROVED or settings.REGISTRATION_POLICY_IS_TEST
    ):
        raise RegistrationUnavailable()
    return {
        "reference": reference,
        "version": version,
        "url": url,
        "is_test_document": settings.REGISTRATION_POLICY_IS_TEST,
    }
