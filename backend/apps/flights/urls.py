from django.urls import path

from .views import CitiesView, FlightCancelView, FlightDetailView, FlightsView, RoutesView

urlpatterns = [
    path("", FlightsView.as_view(), name="flights-list-create"),
    path("<int:pk>/", FlightDetailView.as_view(), name="flights-detail"),
    path("<int:pk>/cancel/", FlightCancelView.as_view(), name="flights-cancel"),
    path("cities/", CitiesView.as_view(), name="flights-cities"),
    path("routes/", RoutesView.as_view(), name="flights-routes"),
]
