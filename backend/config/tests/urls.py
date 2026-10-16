from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response
from rest_framework.views import APIView


class ProtectedView(APIView):
    def post(self, request):
        return Response({"ok": True})


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({"ok": True})


urlpatterns = [
    path("_test/protected/", ProtectedView.as_view()),
    path("_test/csrf/", csrf_cookie),
]
