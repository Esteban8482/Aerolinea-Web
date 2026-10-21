from rest_framework.exceptions import APIException


class RegistrationUnavailable(APIException):
    status_code = 503
    default_code = "registration_unavailable"
    default_detail = "El registro no está disponible con la configuración actual."


class PasswordCheckUnavailable(APIException):
    status_code = 503
    default_code = "password_check_unavailable"
    default_detail = "No se pudo comprobar la contraseña. Intenta de nuevo más tarde."


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


class InvalidCredentials(APIException):
    status_code = 401
    default_code = "invalid_credentials"
    default_detail = "No se pudo iniciar sesión con las credenciales enviadas."


class InvalidRecovery(APIException):
    status_code = 400
    default_code = "recovery_invalid"
    default_detail = "El enlace de recuperación no es válido. Solicita uno nuevo."


class ExpiredRecovery(APIException):
    status_code = 410
    default_code = "recovery_expired"
    default_detail = "El enlace de recuperación venció. Solicita uno nuevo."


class UsedRecovery(APIException):
    status_code = 409
    default_code = "recovery_used"
    default_detail = "El enlace de recuperación ya fue utilizado."
