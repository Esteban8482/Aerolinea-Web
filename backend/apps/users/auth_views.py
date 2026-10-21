from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_serializers import (
    EmptySerializer,
    LoginSerializer,
    LogoutResultSerializer,
    RecoveryRequestSerializer,
    ResetPasswordResultSerializer,
    ResetPasswordSerializer,
    SessionStateSerializer,
)
from .auth_services import (
    LOGIN_PER_ORIGIN,
    LOGIN_WINDOW_SECONDS,
    RECOVERY_INTERVAL_SECONDS,
    RECOVERY_PER_ACCOUNT,
    RECOVERY_PER_ORIGIN,
    end_session,
    record_activity,
    request_recovery,
    reset_password,
    session_state,
    start_session,
)
from .limits import consume_limit, request_origin
from .serializers import RegistrationErrorSerializer, ResendResultSerializer
from .views import CSRF_HEADER

ERRORS = {code: RegistrationErrorSerializer for code in [400, 403, 409, 415, 429, 500]}


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(
        request=LoginSerializer,
        responses={200: SessionStateSerializer, 401: RegistrationErrorSerializer, **ERRORS},
        auth=[],
        parameters=[CSRF_HEADER],
        tags=["Sesión"],
        description="Credenciales incorrectas, cuenta inactiva o inexistente: "
        "401 invalid_credentials. "
        "ROOT solo root_id; otros roles solo email. Cinco fallos/15 min bloquean 15 min; "
        "30 solicitudes por origen/15 min. 429 throttled con Retry-After. "
        "Rota sesión y CSRF. Obtener otro token CSRF tras el éxito. "
        "Correo sin verificar permite login. Inactividad: 30 min; solo session/activity/ renueva.",
        examples=[
            OpenApiExample(
                "Correo",
                value={"email": "persona@example.invalid", "password": "CONTRASEÑA-SINTÉTICA"},
                request_only=True,
            ),
            OpenApiExample(
                "ROOT",
                value={"root_id": "root-de-prueba", "password": "CONTRASEÑA-SINTÉTICA"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        origin = request_origin(request)
        consume_limit(
            scope="HU008.login_origin",
            subject=origin,
            maximum=LOGIN_PER_ORIGIN,
            window_seconds=LOGIN_WINDOW_SECONDS,
        )
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = start_session(
            request=request._request, credentials=serializer.validated_data, origin=origin
        )
        return Response(result)


class SessionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: SessionStateSerializer},
        tags=["Sesión"],
        auth=[],
        description="Estado mínimo. Sin sesión: authenticated=false, role=null. "
        "No renueva el plazo, ni siquiera mediante polling. No devuelve ID de sesión ni perfil.",
    )
    def get(self, request):
        return Response(session_state(request.user))


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(
        request=EmptySerializer,
        responses={200: LogoutResultSerializer, **ERRORS},
        auth=[],
        parameters=[CSRF_HEADER],
        tags=["Sesión"],
        description="Revoca en PostgreSQL la sesión actual. "
        "Idempotente para visitantes. CSRF obligatorio.",
    )
    def post(self, request):
        serializer = EmptySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        end_session(request=request._request, origin=request_origin(request))
        return Response({"status": "logged_out"})


@method_decorator(csrf_protect, name="dispatch")
class SessionActivityView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @extend_schema(
        request=EmptySerializer,
        responses={200: SessionStateSerializer, **ERRORS},
        parameters=[CSRF_HEADER],
        tags=["Sesión"],
        description="Solo tras interacción real del usuario; máximo una vez/minuto desde login "
        "o última actividad. Antes: 429 Retry-After. Renueva 30 min; sesión vencida: 403 "
        "not_authenticated. Una revocación concurrente puede devolver 409 session_invalidated.",
    )
    def post(self, request):
        serializer = EmptySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record_activity(request=request._request)
        return Response(session_state(request.user))


@method_decorator(csrf_protect, name="dispatch")
class RecoveryRequestView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(
        request=RecoveryRequestSerializer,
        responses={202: ResendResultSerializer, **ERRORS},
        auth=[],
        parameters=[CSRF_HEADER],
        tags=["Recuperación"],
        description="Respuesta uniforme para correo existente, desconocido, inactivo o sin "
        "contraseña utilizable. Solo cuentas activas con correo reciben enlace. ROOT recupera "
        "por su correo opcional; no hay alternativa sin correo. 3/correo/h, 20/origen/h, "
        "intervalo 60 s (también desconocidos). Nuevo enlace de 30 min sustituye anteriores. "
        "Solo persiste intención; no envía SMTP en la solicitud.",
    )
    def post(self, request):
        origin = request_origin(request)
        consume_limit(scope="HU008.recovery_origin", subject=origin, maximum=RECOVERY_PER_ORIGIN)
        serializer = RecoveryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        consume_limit(
            scope="HU008.recovery_account",
            subject=email,
            maximum=RECOVERY_PER_ACCOUNT,
            interval=RECOVERY_INTERVAL_SECONDS,
        )
        request_recovery(email=email, origin=origin)
        return Response({"status": "requested"}, status=202)


@method_decorator(csrf_protect, name="dispatch")
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={
            200: ResetPasswordResultSerializer,
            410: RegistrationErrorSerializer,
            503: RegistrationErrorSerializer,
            **ERRORS,
        },
        auth=[],
        parameters=[CSRF_HEADER],
        tags=["Recuperación"],
        description="POST explícito: GET no consume. 400 recovery_invalid o invalid (campos); "
        "410 recovery_expired, 409 recovery_used. Reutiliza validadores de contraseña, "
        "Argon2id y API por rango: fallo 503 password_check_unavailable conserva clave y token. "
        "Sin login automático ni verificación de correo. Todas las sesiones anteriores dejan "
        "de autenticar en su próxima petición, incluida la del solicitante.",
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = serializer.validated_data
        reset_password(
            token=attrs["token"], password=attrs["password"], origin=request_origin(request)
        )
        return Response({"status": "password_reset"})
