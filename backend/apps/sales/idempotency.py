import hashlib
import json

from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.exceptions import ValidationError

from .locking import inventory_transaction
from .models import OperationRequest


@inventory_transaction
def execute(actor, action, key, payload, callback):
    if not key or len(key) > 128:
        raise ValidationError(
            {"Idempotency-Key": "Envía una clave de operación de 1 a 128 caracteres."}
        )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, cls=DjangoJSONEncoder, separators=(",", ":")).encode()
    ).hexdigest()
    previous = OperationRequest.objects.filter(actor=actor, action=action, key=key).first()
    if previous:
        if previous.fingerprint != digest:
            raise ValidationError("La clave de operación ya se utilizó con datos diferentes.")
        return previous.result
    result = callback()
    OperationRequest.objects.create(
        actor=actor, action=action, key=key, fingerprint=digest, result=result
    )
    return result
