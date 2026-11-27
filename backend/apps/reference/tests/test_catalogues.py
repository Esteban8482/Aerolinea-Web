import pytest
from rest_framework.test import APIClient

from apps.reference.importer import read_snapshot
from apps.reference.models import Country, Locality, Option, Subdivision


def test_snapshot_integrity_and_worldwide_scope():
    data = read_snapshot()
    assert len(data["countries"]) == 250
    assert len(data["cities"]) == 172238
    assert {"CO", "US", "AR", "JP", "ZA"} <= {r[1] for r in data["countries"]}


@pytest.mark.django_db
def test_geography_parent_filtering_and_search(reference_city):
    client = APIClient()
    base = "/api/v1/reference/"
    assert client.get(base + "countries/", {"q": "COLOMBIA"}).data["results"][0]["code"] == "CO"
    assert client.get(base + "subdivisions/").status_code == 400
    assert client.get(base + "cities/", {"country_id": 48}).status_code == 400
    params = {"country_id": 48, "subdivision_id": 2879, "q": "Péreira"}
    response = client.get(base + "cities/", params)
    assert response.data["results"][0]["label"] == "Pereira, Risaralda, Colombia"
    params["country_id"] = 99999
    assert client.get(base + "cities/", params).data["results"] == []
    reference_city.active = False
    reference_city.save()
    params["country_id"] = 48
    assert client.get(base + "cities/", params).data["results"] == []


@pytest.mark.django_db
def test_country_without_subdivision_and_inactive_options():
    country = Country.objects.create(id=999, code="XX", name="Test", search_text="test")
    Locality.objects.create(id=999, country=country, name="Test city", search_text="test city")
    client = APIClient()
    assert client.get("/api/v1/reference/cities/", {"country_id": 999}).data["count"] == 1
    Option.objects.filter(category="gender", code="F").update(active=False)
    response = client.get("/api/v1/reference/options/", {"category": "gender"})
    assert "F" not in {row["code"] for row in response.data["results"]}
    assert not Subdivision.objects.filter(country=country).exists()
