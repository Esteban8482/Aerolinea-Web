from django.urls import path

from .views import ReferenceView

urlpatterns = [
    path("countries/", ReferenceView.as_view(kind="countries"), name="reference-countries"),
    path(
        "subdivisions/", ReferenceView.as_view(kind="subdivisions"), name="reference-subdivisions"
    ),
    path("cities/", ReferenceView.as_view(kind="cities"), name="reference-cities"),
    path("options/", ReferenceView.as_view(kind="options"), name="reference-options"),
]
