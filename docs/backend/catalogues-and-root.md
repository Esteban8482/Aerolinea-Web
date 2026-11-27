# Database-backed selectors and ROOT wallet restriction

Date: 2026-11-27. Addendum to cumulative iterations 01–03.

## Approved scope and implementation order

1. Inspect existing roles, registration, flights, sales and financial contracts.
2. Preserve ROOT authentication, session security, administrator creation/listing/password resets,
   and ROOT password change/recovery. Remove wallet access only, following the user's clarification.
3. Introduce geography independently of the airline coverage catalogue; migrate references without
   deleting history; import a versioned offline dataset.
4. Validate registration/traveler categorical inputs and implement dependent flight selectors.
5. Verify with isolated PostgreSQL, document migrations and frontend integration requirements.

## Diagnosis and decisions

Previously `birth_place`, document type and gender accepted arbitrary text; the frontend bundled
Colombian municipalities. Airline `Ciudad` records represented service locations, not a worldwide
address catalogue. Reusing that table for worldwide geography would incorrectly expand coverage.
Flight search also accepted free-text origin/destination aliases. ROOT could access wallet APIs.

The new `reference` app stores countries, subdivisions, localities and stable option codes.
Countries include territories: 250 country/territory records, 5,327 subdivisions and 172,238
localities. This is a pinned community dataset, not a claim that every settlement is represented
or that administrative boundaries can never change. Provenance, checksum, licenses and a curated
Buenos Aires city-level supplement are in `backend/apps/reference/data/`.
Bogotá uses its actual source subdivision, Bogotá D.C.; it is not assigned to Cundinamarca.

`User.birth_city` and `billing_city` are protected foreign keys. New customer registrations require
both; historical users retain nullable references and their original birthplace text. The display
snapshot `birth_place` is derived from the selected locality for new registrations. No ambiguous
historical names are automatically assigned to a city. No user, movement or wallet was deleted.
`Ciudad.locality` links existing service cities to geographic records without changing routes.

ROOT receives 403 from all wallet endpoints, including payment methods, deposits and movements.
Financial domain services reject ROOT as well, regardless of Django superuser/staff flags.
Its profile returns `wallet_balance: null`. The historical wallet row remains inaccessible.
All other existing ROOT account/administrator-security operations are retained.

## API contracts

All listed endpoints use GET and the existing paginated envelope
`{count, next, previous, results}`. Follow `next`; do not assume all options fit one page.

| Endpoint under `/api/v1/` | Parameters and response records |
| --- | --- |
| `reference/countries/` | Optional `q`, `page`; `{id, code, name}` |
| `reference/subdivisions/` | Required `country_id`; optional `q`, `page`; `{id, country_id, code, name}` |
| `reference/cities/` | Required `country_id` and, when that country has subdivisions, `subdivision_id`; optional `q`, `page`; `{id, country_id, subdivision_id, name, label}` |
| `reference/options/` | Optional `category`, `q`, `page`; `{category, code, label}` |
| `flights/city-options/` | Required `side=origin` or `destination`; optional counterpart `destination_id` or `origin_id`, `q`, `date`, `passengers` (1–5), `travel_class`, `page` |

Search ignores case and accents. Geography must be traversed country → subdivision → locality;
for a country without subdivisions, request cities directly. A mismatched parent or no matching
records produces an empty result. Disabled records are excluded.

Flight selector IDs are **airline Ciudad IDs**, not reference locality IDs. Records include
`id`, `nombre`, `label`, `codigo_pais`, `country`, `country_id`, `subdivision`,
`subdivision_id`, `locality_id`. Example query:
`flights/city-options/?side=destination&origin_id=<airline-city-id>&q=Colombia`.
Reverse lookup uses `side=origin&destination_id=...`. Only direct, future scheduled flights on
active routes/cities with enough capacity in one class qualify. An optional date/class narrows
this further. No matching connection means `results: []`; no fallback to unrelated cities.
Availability can change: selection does not reserve inventory; purchase/reservation revalidates it.

Public flight search uses existing Spanish keys `origen_id`, `destino_id`, `fecha_salida`,
`pasajeros`, `clase`; the new selector uses the English keys above. Free-text `origen`/`destino`
search inputs now return 400. Active airline IDs remain the supported search contract.

Registration: send `birth_city_id`, `billing_city_id`, `document_type`, `gender` along with the
existing account, address and consent fields. Stop sending `birth_place`; it is output-only.
City IDs must exist and have active country/subdivision/locality records.
`billing_address` remains free text for the street/building/unit; names, document numbers,
passwords, cancellation explanations and amounts also remain inputs, not invented catalogues.
Travelers use the same document and gender codes in `tipo_documento` and `genero`.

Available option categories: `gender`, `document_type`, `travel_class`, `trip_type`, `flight_type`,
`payment_method_type`, `relocation_decision`, `cancellation_alternative`.
Codes preserve the existing domain enums. Gender/document values are now validated against active
DB options; other categories retain their domain enum validation. Treat these as controlled seed
catalogues, not an authorization to invent new business classes or workflow states in the DB.
Seats and scheduled flight choices remain dynamic existing domain endpoints, not static options.

## Frontend handoff (implementation pending)

| Consumer | Required adaptation |
| --- | --- |
| `RegisterPage.tsx`, registration types | Replace bundled `MUNICIPIOS`/birthplace strings with two dependent country/subdivision/city selectors; submit city IDs; obtain gender/document options from API. |
| `ProfilePage.tsx`, profile types | Accept nullable city IDs for legacy accounts and nullable ROOT wallet balance; keep legacy birthplace display. Never render ROOT wallet controls. |
| `FlightsPage.tsx`, flight search components/types | Use `city-options` for commercial search. Pass opposite selection; search country or city; display full label, store airline ID. Keep administrative scheduling on the existing route catalogue, which can include routes with no flights yet. |
| Traveler forms | Replace document/gender text inputs or mismatched local enums with the catalogue codes. |
| Class/trip/payment/relocation controls | Load relevant option categories; submit codes, not translated labels. Existing domain validation still governs the action. |
| ROOT navigation | Remove wallet links only. Retain existing authentication and administrator account/security controls. |

For every searchable selector: debounce requests, cancel/ignore stale responses, follow pagination,
clear children when a parent changes, clear incompatible opposite flight selections, and disable
selection when results are empty. Typed text is a query, never an accepted option. Surface loading,
empty and validation states. Do not fabricate a fallback option or silently submit the typed text.
These frontend changes have **not** been implemented or browser-tested in this backend delivery.
Include geographic data attribution in the interface/about page when displaying the dataset.

## Migration and operating instructions

In the configured backend environment, with the intended database selected:

```sh
python manage.py migrate
python manage.py load_reference_catalogues
```

New migrations: `reference/0001_initial`, `reference/0002_seed_options`,
`users/0007_user_billing_city_user_birth_city_and_more`, `flights/0004_ciudad_locality`.
Small option codes are seeded by migration. Worldwide geography is loaded explicitly offline,
not during every application startup or test database creation. Import checks SHA-256, IDs and
parent relationships, runs atomically, preserves disabled flags and existing references, and can
be rerun. Run after airline catalogue initialization so its existing cities can be linked.
New service cities require an explicitly reviewed `locality` link; an unlinked city is excluded
from commercial selector results. No public geography-editing endpoint is introduced.

Do not re-enable free-text locations to accommodate an unadapted frontend. Deploy the migrations,
import and frontend contract changes together. Keep historical unresolved city references null
until a reliable mapping or user selection is available. Preserve dataset notices on redistribution.
