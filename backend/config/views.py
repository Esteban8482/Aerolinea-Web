import logging

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.serializers import HealthStatusSerializer

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        responses={
            200: HealthStatusSerializer,
            503: HealthStatusSerializer,
        },
    )
    def get(self, request):
        del request
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            logger.warning("database_unavailable")
            return Response(
                {"status": "unavailable", "application": "ok", "database": "unavailable"},
                status=503,
            )

        return Response({"status": "ok", "application": "ok", "database": "ok"})
