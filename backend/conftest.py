import pytest


@pytest.fixture(autouse=True)
def reference_options(request):
    # Transactional tests flush data migrations; restore the production option catalogue.
    if request.node.get_closest_marker("django_db") or "db" in request.fixturenames:
        request.getfixturevalue("db")
        from apps.reference.catalogue import seed_options

        seed_options()


@pytest.fixture
def reference_city(db):
    from apps.reference.models import Country, Locality, Subdivision

    country, _ = Country.objects.get_or_create(
        id=48, defaults={"code": "CO", "name": "Colombia", "search_text": "colombia co"}
    )
    state, _ = Subdivision.objects.get_or_create(
        id=2879,
        defaults={"country": country, "name": "Risaralda", "search_text": "risaralda colombia"},
    )
    city, _ = Locality.objects.get_or_create(
        id=21195,
        defaults={
            "country": country,
            "subdivision": state,
            "name": "Pereira",
            "search_text": "pereira risaralda colombia",
        },
    )
    return city
