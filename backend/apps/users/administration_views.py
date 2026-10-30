from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .administration_serializers import (
    AdministratorCreatedSerializer,
    AdministratorCreateSerializer,
    AdministratorPasswordChangeSerializer,
    AdministratorSerializer,
    RootPasswordResultSerializer,
    RootPasswordSerializer,
)
from .administration_services import (
    CREATE_PER_ORIGIN,
    CREATE_PER_ROOT,
    ROOT_PASSWORD_PER_ORIGIN,
    ROOT_PASSWORD_WINDOW,
    change_administrator_password,
    change_root_password,
    create_administrator,
    deny_root_action,
    root_user,
)
from .limits import consume_limit, request_origin
from .models import AdministrationEvent, User
from .permissions import IsRoot
from .serializers import RegistrationErrorSerializer
from .views import CSRF_HEADER

ERRORS = {code: RegistrationErrorSerializer for code in [400, 403, 409, 415, 429, 500, 503]}


@method_decorator(csrf_protect, name="dispatch")
class AdministratorsView(GenericAPIView):
    permission_classes = [IsRoot]
    parser_classes = [JSONParser]
    serializer_class = AdministratorSerializer
    queryset = (
        User.objects.filter(role=User.Role.ADMINISTRADOR)
        .only("id", "email", "first_name", "last_name", "document_number", "role")
        .order_by("pk")
    )

    @property
    def administration_action(self):
        return (
            AdministrationEvent.Action.LIST
            if self.request.method == "GET"
            else AdministrationEvent.Action.CREATE
        )

    @extend_schema(
        responses={200: AdministratorSerializer(many=True), 403: RegistrationErrorSerializer},
        tags=["Administradores"],
        description="Solo ROOT activo. Lista paginada de administradores (20 por página), "
        "sin contraseñas, documentos, tokens, privilegios técnicos ni datos de clientes. "
        "No renueva el plazo de inactividad de HU-008.",
    )
    def get(self, request):
        allowed = False
        with transaction.atomic():
            if root_user(request.user, lock=True) is not None:
                allowed = True
                page = self.paginate_queryset(self.get_queryset())
                response = self.get_paginated_response(
                    AdministratorSerializer(page, many=True).data
                )
        if not allowed:
            deny_root_action(
                request.user, action=AdministrationEvent.Action.LIST, origin=request_origin(request)
            )
        return response

    @extend_schema(
        request=AdministratorCreateSerializer,
        responses={201: AdministratorCreatedSerializer, **ERRORS},
        parameters=[CSRF_HEADER],
        tags=["Administradores"],
        description="Solo ROOT activo, independientemente de staff/superuser o verificación. "
        "Correo, contraseña inicial, nombres, apellidos, DNI y teléfono obligatorios. "
        "Rol ADMINISTRADOR fijado por servidor. Máximo 10 solicitudes por ROOT/hora y 20/origen/hora; "
        "429 con Retry-After. Cuenta, billetera cero, aviso y auditoría atómicos. "
        "No envía la contraseña por correo ni marca el correo como verificado. "
        "Correo duplicado: 409 email_already_registered; Pwned Passwords no disponible: "
        "503 password_check_unavailable sin creación parcial.",
        examples=[
            OpenApiExample(
                "Alta de prueba",
                request_only=True,
                value={
                    "email": "admin@example.invalid",
                    "first_name": "Persona",
                    "last_name": "De Prueba",
                    "document_number": "000TEST009",
                    "phone": "3001234567",
                    "password": "CONTRASEÑA-SINTÉTICA",
                },
            )
        ],
    )
    def post(self, request):
        origin = request_origin(request)
        consume_limit(scope="HU009.create_origin", subject=origin, maximum=CREATE_PER_ORIGIN)
        consume_limit(
            scope="HU009.create_root", subject=str(request.user.pk), maximum=CREATE_PER_ROOT
        )
        user = create_administrator(
            actor=request.user, data=request.data, origin=request_origin(request)
        )
        result = AdministratorSerializer(user).data
        result["delivery"] = "pending"
        return Response(result, status=201)


@method_decorator(csrf_protect, name="dispatch")
class RootPasswordView(APIView):
    permission_classes = [IsRoot]
    parser_classes = [JSONParser]
    administration_action = AdministrationEvent.Action.PASSWORD

    @extend_schema(
        request=RootPasswordSerializer,
        responses={200: RootPasswordResultSerializer, 401: RegistrationErrorSerializer, **ERRORS},
        parameters=[CSRF_HEADER],
        tags=["Administradores"],
        description="Solo contraseña del ROOT autenticado; no recibe ID de otro usuario. "
        "Exige clave actual, nueva y confirmación. Cinco fallos de clave actual/15 min "
        "bloquean los cambios 15 min sin bloquear login; 30 solicitudes/origen/15 min. "
        "401 current_password_invalid; 429 throttled y Retry-After. "
        "503 password_check_unavailable conserva clave y sesiones. "
        "Un cambio correcto invalida todas las sesiones de ROOT, incluida la actual, "
        "en su siguiente petición. Sin login automático. "
        "Carrera con otro cambio: 409 credentials_changed. No renueva actividad.",
    )
    def post(self, request):
        origin = request_origin(request)
        consume_limit(
            scope="HU009.root_password_origin",
            subject=origin,
            maximum=ROOT_PASSWORD_PER_ORIGIN,
            window_seconds=ROOT_PASSWORD_WINDOW,
        )
        serializer = RootPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = serializer.validated_data
        change_root_password(
            actor=request.user,
            current_password=attrs["current_password"],
            password=attrs["password"],
            origin=origin,
        )
        return Response({"status": "password_changed"})


@method_decorator(csrf_protect, name="dispatch")
class AdministratorPasswordChangeView(APIView):
    permission_classes = [IsRoot]
    parser_classes = [JSONParser]
    administration_action = AdministrationEvent.Action.PASSWORD

    @extend_schema(
        request=AdministratorPasswordChangeSerializer,
        responses={200: RootPasswordResultSerializer, **ERRORS},
        parameters=[CSRF_HEADER],
        tags=["Administradores"],
        description="Solo ROOT activo. Permite actualizar la contraseña de un administrador existente.",
    )
    def post(self, request):
        origin = request_origin(request)
        serializer = AdministratorPasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = serializer.validated_data
        change_administrator_password(
            actor=request.user,
            admin_id=attrs["admin_id"],
            password=attrs["password"],
            origin=origin,
        )
        return Response({"status": "password_changed"})
