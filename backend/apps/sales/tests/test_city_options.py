import pytest
from rest_framework.test import APIClient

from apps.flights.models import EstadoVuelo
from apps.reference.models import Locality

pytestmark = pytest.mark.django_db


def link_flight(flight, city):
    origin = flight.ruta.origen
    origin.locality = Locality.objects.create(
        id=149237,
        country=city.country,
        subdivision=city.subdivision,
        name="Bogotá",
        search_text="bogota colombia",
    )
    origin.save()
    destination = flight.ruta.destino
    destination.locality = city
    destination.save()


def test_direct_options_search_both_directions(vuelo_nacional, reference_city):
    link_flight(vuelo_nacional, reference_city)
    client = APIClient()
    path = "/api/v1/flights/city-options/"
    origin, destination = vuelo_nacional.ruta.origen_id, vuelo_nacional.ruta.destino_id
    result = client.get(path, {"side": "destination", "origin_id": origin, "q": "Colombia"})
    assert [r["id"] for r in result.data["results"]] == [destination]
    result = client.get(path, {"side": "origin", "destination_id": destination, "q": "Bogota"})
    assert [r["id"] for r in result.data["results"]] == [origin]
    assert client.get(path, {"side": "destination", "origin_id": destination}).data["count"] == 0
    assert client.get(path, {"side": "origin", "destination_id": 999999}).data["count"] == 0
    assert client.get(path, {"side": "origin", "origin_id": origin}).status_code == 400


@pytest.mark.parametrize("reason", ["cancelled", "full", "inactive_route", "inactive_locality"])
def test_unavailable_flights_supply_no_options(vuelo_nacional, reference_city, reason):
    link_flight(vuelo_nacional, reference_city)
    if reason == "cancelled":
        vuelo_nacional.estado = EstadoVuelo.CANCELADO
    elif reason == "full":
        vuelo_nacional.cupos_disponibles_economica = 0
        vuelo_nacional.cupos_disponibles_primera = 0
    elif reason == "inactive_route":
        vuelo_nacional.ruta.activa = False
        vuelo_nacional.ruta.save()
    else:
        reference_city.active = False
        reference_city.save()
    vuelo_nacional.save()
    response = APIClient().get("/api/v1/flights/city-options/", {"side": "destination"})
    assert response.data["results"] == []
