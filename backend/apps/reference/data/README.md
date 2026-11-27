# Geography snapshot

Data by Countries States Cities Database:
https://github.com/dr5hn/countries-states-cities-database — ODbL v1.0.
See `manifest.json` for pinned revision, SHA-256, counts and retrieval date.

The derived database (`geography.json.gz`) is distributed under ODbL v1.0.
Transformation: retain source country/subdivision/locality IDs and parent IDs, country ISO2,
Spanish country names (English fallback), English country names for search, subdivision codes,
and locality names. Remove coordinates, postal data and other unused attributes. Arrays are
`countries: [id, code, name, english_name]`, `subdivisions: [id, country_id, code, name]`,
`cities: [id, country_id, subdivision_id|null, name]`.

Local addition: ID 900000001 is the Buenos Aires city-level option under its autonomous city
subdivision; the upstream country record names that capital but its locality list contains
neighborhoods. This reserved local ID is not represented as an upstream identifier.

Keep `LICENSE-ODbL.txt`, `LICENSE-Unicode-3.0.txt`, and upstream `SOURCES.txt` with copies.
Credits include GeoNames (CC BY 4.0), © OpenStreetMap contributors (ODbL), Wikidata (CC0),
and Unicode CLDR country translations. Full upstream source credits, modifications and known
source review status are preserved in `SOURCES.txt`. The import does not access a remote API.
