"""La actividad se comprueba en PostgreSQL, independientemente del worker o de la cookie."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import SESSION_KEY, logout
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from .auth_services import IDLE_SECONDS, audit
from .models import AccountSession, AuthenticationEvent


class ApiSessionMiddleware(SessionMiddleware):
    def process_response(self, request, response):
        try:
            return super().process_response(request, response)
        except SessionInterrupted:
            # Otra petición revocó la sesión mientras esta petición estaba en curso.
            response = JsonResponse(
                {
                    "code": "session_invalidated",
                    "message": "La sesión dejó de estar disponible. Inicia sesión de nuevo.",
                    "details": {},
                },
                status=409,
            )
            response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            return response


class IdleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Usar la cookie para poder registrar el vencimiento incluso si Django ya
        # descartaría la sesión por expire_date. Nunca se registra su valor.
        key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if key:
            state = AccountSession.objects.filter(session_id=key).first()
            now = timezone.now()
            if state and now >= state.last_activity_at + timedelta(seconds=IDLE_SECONDS):
                with transaction.atomic():
                    state = (
                        AccountSession.objects.select_for_update().filter(session_id=key).first()
                    )
                    if state and now >= state.last_activity_at + timedelta(seconds=IDLE_SECONDS):
                        audit(AuthenticationEvent.Kind.SESSION_EXPIRED, user=state.user)
                        Session.objects.filter(pk=key).delete()
                        logout(request)
        if request.user.is_authenticated:
            if not AccountSession.objects.filter(
                session_id=request.session.session_key, user=request.user
            ).exists():
                # Sesiones anteriores a HU-008 no acreditan un instante de actividad.
                logout(request)
        elif SESSION_KEY in request.session:
            # Cuenta desactivada o backend que ya no reconoce al titular.
            request.session.flush()
        return self.get_response(request)
