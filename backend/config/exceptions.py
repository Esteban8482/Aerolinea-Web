import logging

from django.http import JsonResponse
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        set_rollback()
        logger.error("unhandled_api_error")
        return Response(
            {"code": "internal_error", "message": "Error interno del servidor.", "details": {}},
            status=500,
        )
    code = getattr(exc, "default_code", "request_error")
    if isinstance(exc, PermissionDenied) and str(exc.detail).startswith("CSRF Failed"):
        code = "csrf_failed"
    if isinstance(exc, ValidationError):
        message, details = "Revisa los datos enviados.", response.data
    else:
        messages = {
            "not_authenticated": "Se requiere una sesión autenticada.",
            "permission_denied": "No tienes permiso para esta operación.",
            "csrf_failed": "No se pudo verificar la protección CSRF.",
            "not_found": "Recurso no encontrado.",
            "method_not_allowed": "Método no permitido.",
            "parse_error": "El cuerpo de la solicitud no es válido.",
        }
        message, details = messages.get(code, "No se pudo procesar la solicitud."), {}
    response.data = {"code": code, "message": message, "details": details}
    return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "code": "csrf_failed",
            "message": "No se pudo verificar la protección CSRF.",
            "details": {},
        },
        status=403,
    )


def not_found(request, exception):
    return JsonResponse(
        {"code": "not_found", "message": "Recurso no encontrado.", "details": {}}, status=404
    )


def server_error(request):
    return JsonResponse(
        {"code": "internal_error", "message": "Error interno del servidor.", "details": {}},
        status=500,
    )
