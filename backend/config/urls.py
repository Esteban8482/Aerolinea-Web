from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from config.views import HealthCheckView

urlpatterns = [
    path("api/health/", HealthCheckView.as_view(), name="api-health"),
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
