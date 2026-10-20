from rest_framework.exceptions import APIException


class RegistrationUnavailable(APIException):
    status_code = 503
    default_code = "registration_unavailable"
    default_detail = "El registro no está disponible con la configuración actual."


class EmailAlreadyRegistered(APIException):
    status_code = 409
    default_code = "email_already_registered"
    default_detail = (
        "El correo ya está registrado. Utiliza la recuperación de acceso cuando esté disponible."
    )


class InvalidVerification(APIException):
    status_code = 400
    default_code = "verification_invalid"
    default_detail = "El enlace de verificación no es válido."


class ExpiredVerification(APIException):
    status_code = 410
    default_code = "verification_expired"
    default_detail = "El enlace venció. Solicita un nuevo envío cuando esté disponible."


class UsedVerification(APIException):
    status_code = 409
    default_code = "verification_used"
    default_detail = "El enlace ya fue utilizado."
