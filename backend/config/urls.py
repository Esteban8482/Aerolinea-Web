from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

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
