from .models import JourneyNotification, OperationAudit


def audit(actor, action, resource, **details):
    OperationAudit.objects.create(
        actor=actor, action=action, resource_id=resource.pk, details=details
    )


def notify(recipients, subject, body):
    for recipient in sorted({r.strip().lower() for r in recipients if r}):
        JourneyNotification.objects.create(recipient=recipient, subject=subject, body=body)
