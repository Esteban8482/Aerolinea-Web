from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.users.administration_views import AdministratorsView, RootPasswordView
from apps.users.auth_views import (
    LoginView,
    LogoutView,
    RecoveryRequestView,
    ResetPasswordView,
    SessionActivityView,
    SessionView,
)
from apps.users.views import (
    ConfirmEmailView,
    CsrfView,
    RegisterView,
    RegistrationPolicyView,
    ResendVerificationView,
    TestPolicyDocumentView,
)
from config.views import HealthCheckView

urlpatterns = [
    path("api/v1/users/administrators/", AdministratorsView.as_view(), name="administrators"),
    path("api/v1/users/root/password/", RootPasswordView.as_view(), name="root-password"),
    path("api/v1/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/v1/auth/session/", SessionView.as_view(), name="auth-session"),
    path("api/v1/auth/session/activity/", SessionActivityView.as_view(), name="auth-activity"),
    path("api/v1/auth/password-recovery/", RecoveryRequestView.as_view(), name="auth-recovery"),
    path("api/v1/auth/password-reset/", ResetPasswordView.as_view(), name="auth-password-reset"),
    path("api/health/", HealthCheckView.as_view(), name="api-health"),
    path("api/v1/auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("api/v1/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/v1/auth/verify-email/", ConfirmEmailView.as_view(), name="auth-verify-email"),
    path("api/v1/auth/resend-verification/", ResendVerificationView.as_view(), name="auth-resend"),
    path(
        "api/v1/auth/registration-policy/",
        RegistrationPolicyView.as_view(),
        name="registration-policy",
    ),
    path(
        "api/v1/auth/registration-policy/test-document/",
        TestPolicyDocumentView.as_view(),
        name="test-policy-document",
    ),
]

handler404 = "config.exceptions.not_found"
handler500 = "config.exceptions.server_error"

if settings.API_DOCUMENTATION_ENABLED:
    urlpatterns += [
        path(
            "api/schema/", SpectacularAPIView.as_view(permission_classes=[AllowAny]), name="schema"
        ),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
            name="swagger-ui",
        ),
    ]
