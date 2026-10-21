from django.conf import settings
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .limits import (
    REGISTER_PER_ORIGIN,
    RESEND_INTERVAL_SECONDS,
    RESEND_PER_ACCOUNT,
    RESEND_PER_ORIGIN,
    consume_limit,
    request_origin,
)
from .policy import current_registration_policy
from .serializers import (
    CsrfSerializer,
    PolicySerializer,
    RegistrationErrorSerializer,
    RegistrationResultSerializer,
    RegistrationSerializer,
    ResendResultSerializer,
    ResendSerializer,
    VerificationResultSerializer,
    VerificationSerializer,
)
from .services import confirm_email, register_customer, resend_verification

CSRF_HEADER = OpenApiParameter(
    "X-CSRFToken",
    str,
    OpenApiParameter.HEADER,
    required=True,
    description="Token de GET /api/v1/auth/csrf/; enviar también su cookie csrftoken.",
)


class CsrfView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CsrfSerializer}, auth=[], tags=["Registro"])
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, MultiPartParser]

    @extend_schema(
        request=RegistrationSerializer,
        responses={
            201: RegistrationResultSerializer,
            **{code: RegistrationErrorSerializer for code in [400, 403, 409, 415, 429, 500, 503]},
        },
        parameters=[CSRF_HEADER],
        auth=[],
        tags=["Registro"],
        description="Alta sin sesión automática; "
        "máximo 10 solicitudes por origen en una hora móvil. "
        "Obtén política vigente con GET /api/v1/auth/registration-policy/. "
        "JSON sin imagen o multipart/form-data con image opcional JPEG/PNG/WebP, "
        "hasta 2 MiB y 4096×4096. Producción requiere política aprobada. "
        "Configuración ausente: 503 registration_unavailable. Comprobación HTTPS por rango "
        "Pwned Passwords (3 s, sin reintentos): fallo 503 password_check_unavailable; "
        "reintentar más tarde. Contraseña comprometida: 400 invalid. "
        "Límite excedido: 429 con Retry-After.",
    )
    def post(self, request):
        current_registration_policy()
        consume_limit(
            scope="register_origin", subject=request_origin(request), maximum=REGISTER_PER_ORIGIN
        )
        register_customer(data=request.data)
        return Response({"status": "unverified", "delivery": "pending"}, status=201)


class RegistrationPolicyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: PolicySerializer, 503: RegistrationErrorSerializer},
        auth=[],
        tags=["Registro"],
        description="Referencia y versión determinadas por el servidor. "
        "El formulario debe mostrar el documento y enviar ambos valores sin alterarlos. "
        "is_test_document=true identifica una referencia de prueba sin aprobación legal.",
    )
    def get(self, request):
        return Response(current_registration_policy())


class TestPolicyDocumentView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    def get(self, request):
        if settings.REGISTRATION_PRODUCTION:
            from rest_framework.exceptions import NotFound

            raise NotFound()
        return HttpResponse(
            "DOCUMENTO DE PRUEBA — test-v1\n"
            "Referencia sintética para probar registro y consentimiento con datos ficticios.\n"
            "No es una política legal, no está aprobada y no habilita un registro productivo.\n",
            content_type="text/plain; charset=utf-8",
        )


@method_decorator(csrf_protect, name="dispatch")
class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(
        request=ResendSerializer,
        responses={
            202: ResendResultSerializer,
            **{code: RegistrationErrorSerializer for code in [400, 403, 415, 429, 500]},
        },
        parameters=[CSRF_HEADER],
        auth=[],
        tags=["Registro"],
        description="Respuesta uniforme para correo desconocido, inactivo o verificado. "
        "Cuenta sin verificar: encola nuevo enlace e invalida los anteriores, sin crear cuenta "
        "ni billetera. Máximo 20 solicitudes por origen/hora móvil y 5 por correo/hora móvil; "
        "espera 60 segundos desde el envío inicial o último reenvío solicitado. "
        "Límites también para correos desconocidos/verificados. 429 con Retry-After.",
    )
    def post(self, request):
        consume_limit(
            scope="resend_origin", subject=request_origin(request), maximum=RESEND_PER_ORIGIN
        )
        serializer = ResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        consume_limit(
            scope="resend_account",
            subject=email,
            maximum=RESEND_PER_ACCOUNT,
            interval=RESEND_INTERVAL_SECONDS,
        )
        resend_verification(email=email)
        return Response({"status": "requested"}, status=202)


@method_decorator(csrf_protect, name="dispatch")
class ConfirmEmailView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(
        request=VerificationSerializer,
        responses={
            200: VerificationResultSerializer,
            **{code: RegistrationErrorSerializer for code in [400, 403, 409, 410, 415, 500]},
        },
        parameters=[CSRF_HEADER],
        auth=[],
        tags=["Registro"],
        description="Confirmación explícita por POST. Token inválido: 400 verification_invalid; "
        "vencido: 410 verification_expired; "
        "consumido o cuenta ya verificada: 409 verification_used. "
        "Una repetición conserva la cuenta verificada. No inicia sesión.",
    )
    def post(self, request):
        serializer = VerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirm_email(**serializer.validated_data)
        return Response({"status": "verified"})
