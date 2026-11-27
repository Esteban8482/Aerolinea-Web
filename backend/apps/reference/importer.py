"""Offline, checksummed, idempotent import. Never delete user data or referenced places."""

import gzip
import hashlib
import json
from pathlib import Path

from django.db import transaction

from .catalogue import normalized, seed_options
from .models import Country, Locality, Subdivision

AIRLINE_LOCALITIES = {
    "Pereira": 21195,
    "Bogotá": 149237,
    "Medellín": 21074,
    "Cali": 20634,
    "Cartagena": 20659,
    "Barranquilla": 20574,
    "Bucaramanga": 20603,
    "Santa Marta": 21421,
    "Cúcuta": 20772,
    "Manizales": 21059,
    "Armenia": 20550,
    "Ibagué": 20944,
    "Pasto": 21184,
    "Villavicencio": 21612,
    "Montería": 21102,
    "Neiva": 143894,
    "Valledupar": 21582,
    "Popayán": 21219,
    "Riohacha": 21291,
    "Sincelejo": 21461,
    "San Andrés": 21331,
    "Leticia": 21027,
    "Madrid": 35186,
    "Londres": 50388,
    "Nueva York": 122795,
    "Buenos Aires": 900000001,
    "Miami": 121746,
}


def read_snapshot():
    folder = Path(__file__).parent / "data"
    manifest = json.loads((folder / "manifest.json").read_text())
    raw = (folder / "geography.json.gz").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Geography snapshot checksum mismatch")
    data = json.loads(gzip.decompress(raw))
    for key in ("countries", "subdivisions", "cities"):
        if len(data[key]) != manifest[key] or len({row[0] for row in data[key]}) != len(data[key]):
            raise ValueError("Invalid reference counts or duplicate source IDs")
    countries = {r[0] for r in data["countries"]}
    states = {r[0]: r[1] for r in data["subdivisions"]}
    if any(r[1] not in countries for r in data["subdivisions"]):
        raise ValueError("Unknown subdivision country")
    if any(
        r[1] not in countries or (r[2] is not None and states.get(r[2]) != r[1])
        for r in data["cities"]
    ):
        raise ValueError("Invalid city hierarchy")
    return data


def upsert(model, rows, fields):
    model.objects.bulk_create(
        rows, batch_size=2000, update_conflicts=True, unique_fields=["id"], update_fields=fields
    )


@transaction.atomic
def import_geography():
    data = read_snapshot()
    country_names = {r[0]: f"{r[2]} {r[3]} {r[1]}" for r in data["countries"]}
    subdivision_names = {r[0]: r[3] for r in data["subdivisions"]}
    upsert(
        Country,
        [
            Country(id=i, code=code, name=name, search_text=normalized(f"{name} {en} {code}"))
            for i, code, name, en in data["countries"]
        ],
        ["code", "name", "search_text"],
    )
    upsert(
        Subdivision,
        [
            Subdivision(
                id=i,
                country_id=c,
                code=code,
                name=name,
                search_text=normalized(f"{name} {country_names[c]}"),
            )
            for i, c, code, name in data["subdivisions"]
        ],
        ["country", "code", "name", "search_text"],
    )
    upsert(
        Locality,
        [
            Locality(
                id=i,
                country_id=c,
                subdivision_id=s,
                name=name,
                search_text=normalized(f"{name} {subdivision_names.get(s, '')} {country_names[c]}"),
            )
            for i, c, s, name in data["cities"]
        ],
        ["country", "subdivision", "name", "search_text"],
    )
    seed_options()
    from apps.flights.models import Ciudad

    for name, locality_id in AIRLINE_LOCALITIES.items():
        locality = Locality.objects.select_related("country").get(pk=locality_id)
        # An existing link is not silently reassigned to another place.
        Ciudad.objects.filter(
            nombre=name, codigo_pais=locality.country.code, locality__isnull=True
        ).update(locality_id=locality_id)
    return {
        "countries": len(data["countries"]),
        "subdivisions": len(data["subdivisions"]),
        "cities": len(data["cities"]),
    }
