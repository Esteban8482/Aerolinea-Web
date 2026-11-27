from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .catalogue import normalized
from .models import Country, Locality, Option, Subdivision
from .serializers import (
    CountrySerializer,
    LocalitySerializer,
    OptionSerializer,
    ReferencePageSerializer,
    ReferenceQuery,
    SubdivisionSerializer,
)


class ReferenceView(APIView):
    permission_classes = [AllowAny]
    kind = "countries"

    @extend_schema(parameters=[ReferenceQuery], responses=ReferencePageSerializer)
    def get(self, request):
        query = ReferenceQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        if self.kind == "options":
            queryset, serializer = Option.objects.filter(active=True), OptionSerializer
            if "category" in params:
                queryset = queryset.filter(category=params["category"])
            # Options are small; fold accents consistently with geography search.
            queryset = [
                x
                for x in queryset
                if normalized(params.get("q", "")) in normalized(f"{x.label} {x.code}")
            ]
        else:
            model, serializer = {
                "countries": (Country, CountrySerializer),
                "subdivisions": (Subdivision, SubdivisionSerializer),
                "cities": (Locality, LocalitySerializer),
            }[self.kind]
            queryset = model.objects.filter(active=True)
            if self.kind != "countries":
                if "country_id" not in params:
                    raise ValidationError({"country_id": "Selecciona primero un país."})
                queryset = queryset.filter(country_id=params["country_id"], country__active=True)
            if self.kind == "cities":
                if "subdivision_id" in params:
                    queryset = queryset.filter(
                        subdivision_id=params["subdivision_id"], subdivision__active=True
                    )
                elif Subdivision.objects.filter(
                    country_id=params["country_id"], active=True
                ).exists():
                    raise ValidationError(
                        {"subdivision_id": "Selecciona primero una división territorial."}
                    )
                else:
                    queryset = queryset.filter(subdivision__isnull=True)
                queryset = queryset.select_related("country", "subdivision")
            for token in normalized(params.get("q", "")).split():
                queryset = queryset.filter(search_text__contains=token)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(serializer(page, many=True).data)
