import ipaddress
import math

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import Throttled

from .models import RegistrationRateBucket

REGISTER_PER_ORIGIN = 10
RESEND_PER_ORIGIN = 20
RESEND_PER_ACCOUNT = 5
RESEND_INTERVAL_SECONDS = 60
WINDOW_SECONDS = 3600


def request_origin(request):
    remote = request.META.get("REMOTE_ADDR", "")
    if remote in settings.REGISTRATION_TRUSTED_PROXIES:
        remote = request.META.get("HTTP_X_REAL_IP", remote)
    try:
        return str(ipaddress.ip_address(remote))
    except ValueError:
        return "unknown"


def bucket_key(scope, subject):
    return salted_hmac("HU007.rate." + scope, subject, algorithm="sha256").hexdigest()


def consume_limit(*, scope, subject, maximum, interval=0):
    key = bucket_key(scope, subject)
    # get_or_create usa unicidad para el primer reclamo simultáneo.
    RegistrationRateBucket.objects.get_or_create(key=key)
    with transaction.atomic():
        bucket = RegistrationRateBucket.objects.select_for_update().get(key=key)
        now = timezone.now()
        timestamps = [t for t in bucket.timestamps if t > now.timestamp() - WINDOW_SECONDS]
        wait = 0
        if len(timestamps) >= maximum:
            wait = timestamps[0] + WINDOW_SECONDS - now.timestamp()
        if interval and bucket.last_accepted_at:
            wait = max(wait, interval - (now - bucket.last_accepted_at).total_seconds())
        if wait > 0:
            raise Throttled(wait=max(1, math.ceil(wait)))
        timestamps.append(now.timestamp())
        bucket.timestamps = timestamps
        bucket.last_accepted_at = now
        bucket.save(update_fields=["timestamps", "last_accepted_at"])


def initial_verification_cooldown(email, now):
    key = bucket_key("resend_account", email)
    bucket, _ = RegistrationRateBucket.objects.get_or_create(key=key)
    bucket = RegistrationRateBucket.objects.select_for_update().get(pk=bucket.pk)
    if not bucket.last_accepted_at or bucket.last_accepted_at < now:
        bucket.last_accepted_at = now
        bucket.save(update_fields=["last_accepted_at"])
