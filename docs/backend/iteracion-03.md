# Iteration 03 — backend diagnosis, implementation and handoff

Date: 2026-11-26. Branch: `iteracion-03`. Integration baseline: `d52abe5`.

**Delivery status: backend implemented and locally verified.** This document supersedes
its initial planning-only draft. Frontend adaptation, operational scheduling, target-environment
integration and team review remain separate delivery steps, listed below. No commits, pushes, PRs, deployments, production data
changes, or real SMTP deliveries are part of this work.

## Scope and work plan

The user authorized repairing the started backend workflows before completing HU-002,
HU-003, HU-004, HU-014, HU-016 and HU-017. This includes the necessary HU-001/012/013
contracts, permissions, inventory, refund records and integration tests. Existing users,
sessions, wallet persistence and teammates' domain models are reused. New frontend screens,
payment-method/withdrawal infrastructure, recommendations and chatbot are outside this
backend delivery.

Ordered implementation:

1. Inspect baseline, requirements, existing services, migrations and teammates' changes.
2. Repair authorization, traveler validation, inventory transactions and payment traceability.
3. Finish editing/cancellation and the shared notification/audit paths.
4. Implement scheduled promotions and one price resolver for confirmation and presentation.
5. Complete customer cancellation, seat changes and check-in/PDF/access workflows.
6. Write boundary, permission, rollback, retry and PostgreSQL concurrency tests.
7. Validate migrations, OpenAPI and regressions; provide exact integration instructions.

The initial instruction to defer tests was explicitly lifted. The user subsequently approved
isolated backend tests and clarified promotions, relocation, magic-link lifetime and request
limits. See DEC-23–26 in the project clarifications for the adopted rules and provenance.

## Diagnosis of the merged implementation

The initial checkout at `9abcfc5` did not contain flights/sales. The user integrated teammates'
work; the current baseline includes HU-012 (`d86e415`) and HU-013 (`c7cedce`) along with
iteration-02 flights, sales, wallet movements and frontend work. There is no pending merge.
The initial branch diagnosis must not be mistaken for the current baseline.

| Finding | Required correction |
|---|---|
| Seat-change service ignored actor ownership | Owner-scoped lookup and client authorization; guest access separately scoped |
| Sales views allowed any authenticated role and unverified account | Client role and verified-email checks in API and domain services |
| Default first-class fare was economy × 1.50 | Explicit independent class fares; remove undocumented multiplier |
| Price recalculated without checking what customer accepted | Quote endpoint and required `accepted_total`; conflict before debit |
| Purchase creation had no persistent request idempotency | Actor/action/key/payload records committed with the result |
| Lock orders differed among purchase, expiry, cancellation and seat change | Shared PostgreSQL transaction advisory lock plus row locks |
| Refund primitive had no enforced purchase debit or ticket reference | Purchase-to-debit and ticket-to-refund relationships; paid-value checks |
| Cancellation omitted unpaid reservations | Release complete retained itineraries without creating refunds |
| Rescheduling did not update reservation deadlines or check-ins | Original 24-hour maximum, earliest-leg deadline, explicit check-in invalidation |
| Notification recipients were a placeholder mailbox | Real buyer/traveler recipients, transactional outbox and retry processor |
| Ticket schema did not prevent duplicate active seat assignment | Partial unique constraint on active ticket seat |
| Traveler lookup reused private data using document number alone | Operation-specific traveler snapshot; normalize type and number together |
| Password minimum had been reduced to eight in merged settings | Restore the documented minimum of twelve |
| Verification/recovery ran mail processors inside post-commit callbacks | Restore durable worker-controlled delivery so missing URL/SMTP does not fail the business request |
| Route PATCH used Python truthiness on raw input | Validate through its existing serializer before persistence |

Existing creation, reservation, purchase, cancellation and seat-change tests were retained
and updated where they asserted superseded behavior. In particular, tests no longer expect
placeholder recipients, silently ignored immutable fields, undocumented fares or one
aggregated refund movement for several tickets. They now provide emergency-contact data,
accepted totals and operation keys where required.

## Implementation map

| Story / support | Implementation |
|---|---|
| HU-001 dependency | Explicit fares, controlled flight codes, timezone/DST validation, administrator-only writes |
| HU-012 dependency | Shared itinerary/traveler validation, expired-capacity recovery, retained-capacity accounting, idempotent API creation |
| HU-013 dependency | Quote/accepted total, current promotion pricing, secure locator generation with collision retry, atomic debit/tickets/seats, payment linkage |
| HU-002 | Immutable-input rejection, edit reason, arrival recalculation, deadlines, notices, audit, check-in invalidation, invalid-discount removal |
| HU-003 | Full transactional cancellation/refund, unpaid release, historical retention, news/promotion removal, relocation offer/decision workflow |
| HU-004 | Scheduled per-flight/class promotion, nonoverlapping intervals, discounted new operations, news publication and price presentation |
| HU-014 | Owner-only cancellation, national/international boundaries, per-ticket paid-value refunds and repeat-safe inventory release |
| HU-017 | Ownership, flight/time/class checks, same-seat no-op, one voluntary change, active-seat uniqueness and audit |
| HU-016 | Group validation before confirmation, buyer session or scoped magic link, private PDF, durable email and retry |

Business rules live in `sales/services.py`, `sales/rules.py`, `sales/checkin.py` and
`flights/operations.py`. HTTP adapters are in the existing views plus `sales/journey_views.py`.
`events.py` writes durable notification/audit records. `journey_mail.py` processes pending
notifications outside database transactions; ReportLab generates PDFs outside check-in locks.

Inventory-changing services use `sales/locking.py`: one PostgreSQL transaction-scoped
advisory lock serializes cross-flight inventory changes, with ORM row locks retained for
persistence. Wallet-only operations do not acquire it. This is a deliberate correctness
tradeoff for the academic load. It is **not** evidence of the documented throughput or
latency goals; measure before replacing it with finer-grained locking.

## Adopted behavior

### Promotions and prices

Administrators provide both class fares directly. A promotion belongs to one flight/class,
has a positive price below its base fare and an interval ending no later than departure.
Intervals for the same flight/class cannot overlap. There is no consumable promotion quota.
A promotion may start immediately or be scheduled in advance; it must end in the future.
Only new direct purchases and reservations created while that promotion is in effect are
eligible; older reservations do not become eligible retroactively. Confirmation still uses
the price valid at payment time. Existing paid tickets never change price.

`precio_vigente_economica` and `precio_vigente_primera` are the current display fields.
`costo_persona_*` remain base fares for administration. Quote and purchase use the same
resolver; a quote does not retain seats or guarantee a later price. At confirmation, a
changed total produces HTTP 409 `price_changed` with `details.current_total`. The UI must
show the new amount and obtain another explicit confirmation.

### Cancellation and relocation

Voluntary purchase cancellation is allowed strictly before departure minus one hour for
national flights or three hours for international flights. At the exact cutoff it fails.
Unpaid reservations never generate money. Refunds use each ticket's paid amount and return
to the original buyer. Repeated cancellation does not generate another refund/release.
A mandatory refund persistence failure rolls back all cancellation changes.

An administrator offers a compatible same-route/class replacement. The buyer accepts or
requests a refund through their session. Destination availability is checked again at the
moment of acceptance. If no compatible capacity remains, the result is a refund. No extra
charge is made and the replacement preserves the paid price and its original-ticket link.
The voluntary seat-change count carries over; relocation itself does not consume a change.
Reubicate adults first so minors retain an accompanying adult in each destination flight.

Resolve relocation offers before final cancellation of the source flight. Final flight
cancellation refunds any tickets still active there. Sending `REUBICACION` to the cancel endpoint requires buyer decisions when eligible
alternatives exist; if none exist, the recorded outcome is refund. It cannot silently
record a refund as relocation. Buyer choice is persisted.

### Rescheduling and check-in

Reservation expiry stays bounded by original creation + 24 hours and all current flight
cutoffs. Expired reservations are never revived. An incompatible unpaid itinerary is
released and explicitly notified. Incompatible paid itineraries are flagged for review,
with notice and an operational refund path rather than a silent change to the other flight.

Rescheduling resets confirmed check-in and cancels pending stale boarding-pass jobs. The
customer must confirm again within the new window. An active buyer session retains access
to existing ticket check-in/seat changes during email reverification; new bookings and wallet
operations remain blocked until verification. The API stops serving the invalid pass.
Already downloaded or emailed files cannot be recalled; users are notified to replace them.

Check-in is enabled at `departure - 24 h`, inclusive, and closes at departure, exclusive.
Every selected ticket must be active, authorized and in the correct window. A mixed invalid
group is rejected without partially confirming it. Repeating confirmation does not create
another boarding-pass job. A PDF/SMTP failure preserves check-in and remains retryable.

A magic link authenticates one traveler within one purchase/locator; it is not a general
user session. It remains usable until each relevant flight closes check-in. A new link
revokes previous links for that traveler/purchase. The credential is sent in the URL fragment
and then `X-Checkin-Token`, never a query parameter. The access table stores its digest;
the pending delivery body necessarily contains the secret link and requires private database
access. The secret delivery body is cleared after successful delivery or revocation. Requests require CSRF and have a generic response for unknown travelers. Limits:
60 seconds between requests, five per traveler/hour and twenty per origin/hour.

### Seat map and history

Seats are assigned only at purchase, inside the purchased class. Reservations retain
aggregate capacity rather than numbered seats. Public seat data contains no traveler
identity. Clients must not draw imaginary numbered reservations. Ticket state, assigned
seat, price and check-in remain visible through the owner's existing purchase detail.

## API handoff

All paths below start at `/api/v1/`. Session mutations require CSRF. Guest mutations also
require CSRF from `/auth/csrf/`, even without a user session. Money is a decimal string;
current baseline monetary examples use COP. Send ISO 8601 timestamps with an explicit offset.

| Method / path | Input and authorization |
|---|---|
| `POST flights/` | Administrator; both class fares required |
| `PATCH flights/{id}/` | Administrator; `motivo` plus date/time and/or base fares; immutable fields rejected |
| `POST flights/{id}/cancel/` | Administrator; `motivo`, `alternativa: REINTEGRO`; remaining active tickets refunded |
| `POST sales/quote/` | Verified client; `vuelo_id`, optional return/class/trip and `passenger_count`, or `reserva_id` |
| `POST sales/reservations/` | Verified client; travelers including phone/emergency contact; `Idempotency-Key` header |
| `POST sales/purchases/` | Verified client; existing purchase input plus `accepted_total`; `Idempotency-Key` header |
| `POST sales/reservations/{id}/cancel/` | Verified owner; no refund for unpaid reservation |
| `POST sales/purchases/{id}/cancel/` | Verified owner; per-ticket refund within the applicable window |
| `POST sales/tickets/{id}/change-seat/` | Active client owner; `nueva_silla_id` |
| `POST sales/flights/{id}/promotions/` | Administrator; `clase`, `price`, `starts_at`, `ends_at` |
| `GET sales/flight-news/` | Public paginated active flight/promotion news |
| `POST sales/relocations/` | Administrator; `ticket_id`, `destination_id` |
| `GET sales/relocations/{id}/` | Verified buyer; inspect offer and resolution |
| `POST sales/relocations/{id}/` | Verified buyer; `decision: ACCEPT` or `REFUND` |
| `GET sales/check-in/` | Buyer session or `X-Checkin-Token`; paginated authorized tickets |
| `POST sales/check-in/` | Buyer session or magic-link header; `ticket_ids: [...]` |
| `POST sales/check-in/access/` | Public + CSRF; `locator`, `document_type`, `document`, `email`; generic 202 |
| `POST sales/check-in/tickets/{id}/seat/` | Magic-link header + CSRF; `seat_id` |
| `GET sales/tickets/{id}/boarding-pass/` | Owner or magic-link header; private `application/pdf` attachment |
| `POST sales/flights/{id}/performed/` | Administrator; explicit operational confirmation after scheduled departure |

Reuse the same idempotency key and exactly the same payload after a network failure.
A different payload with that key is rejected. Use a new key for a new action or an
explicitly accepted revised quote. Do not generate a new key for every automatic retry.

Important integration changes: the existing frontend must supply both fares, an edit
reason, required emergency-contact fields, operation keys and the accepted total. Display
current price fields rather than treating base fares as discounted prices. A consumer that
has not been adapted to these contracts is not an end-to-end verified flow. New check-in,
promotion and relocation screens remain frontend work. Frontend password hints/validation
still describing eight characters must be updated to the restored twelve-character minimum;
the backend does not add a mandatory-digit rule.

### Frontend integration examples

Obtain the current quote before asking the buyer to confirm:

```json
POST /api/v1/sales/quote/
{"vuelo_id": 42, "clase": "ECONOMICA", "tipo_trayecto": "UNICO", "passenger_count": 1}
```

Use the returned decimal `total` as `accepted_total` in the purchase request after the
buyer explicitly accepts it. Include the complete traveler/contact input and a random
`Idempotency-Key` retained across retries of that same action. If HTTP 409 returns a new
total, display it and obtain another confirmation; do not automatically charge it. A new
accepted payload uses a new operation key. The quote request itself does not reserve capacity.
For conversion of an existing reservation, quote with `reserva_id` to apply its eligibility.

For guest access, request the link with locator, document type/number and recorded email.
The frontend must remove `#token=...` from browser history after reading it, avoid logging
or analytics capture, and retain it privately for the check-in flow. Use same-origin requests
with `X-Checkin-Token`; never grant a general logged-in UI role from that credential.

```json
POST /api/v1/sales/check-in/
{"ticket_ids": [101, 102]}
```

Send cookie/header CSRF for this POST as well. Select only the authorized tickets whose
individual flight windows are open; an outbound and return ticket may have different
windows. To download a guest boarding pass, fetch it with the credential header and create
a local blob download. Do not append the credential to a PDF URL or use a public file path.
A failed PDF request can be retried without repeating a business confirmation.

For relocation, the administrator's offer returns its ID. The buyer retrieves that offer,
loads the destination flight details, and explicitly submits `ACCEPT` or `REFUND`. Present
the **returned** decision: capacity may disappear before acceptance and cause the required
refund fallback. Do not report a completed relocation merely because an offer was created.

## Migrations and development operation

Do not rewrite shared migrations. New migrations add promotions, debit/refund references,
operation/audit records, guest access, relocation offers, notification jobs, constraints and
itinerary-disruption status. Existing purchases receive a debit link only when the old
wallet reference, owner and amount match exactly one movement. Missing/ambiguous legacy
records stay unresolved and refund fails closed for reconciliation. No synthetic debit or
refund is created. Duplicate active seats or invalid historical movements must be reconciled
before adding their constraints; migrations do not delete conflicting history.

From the repository root with Docker available:

```bash
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py liberar_reservas_vencidas --batch-size 100
docker compose exec backend python manage.py process_verification_emails --batch-size 100
docker compose exec backend python manage.py process_recovery_emails --batch-size 100
docker compose exec backend python manage.py process_administrator_notifications --batch-size 100
docker compose exec backend python manage.py process_purchase_emails --batch-size 100
docker compose exec backend python manage.py process_journey_emails --batch-size 100
```

Integration must schedule expiry at least once per minute and the mail processors frequently
enough for the documented delivery goal. These manual commands do not establish a scheduler.
The demo commands now reject execution outside DEBUG and supply the stricter service
inputs; they remain synthetic development utilities. Repository-wide lint/formatting fixes
were necessary for the documented CI checks.

The application retains jobs after provider failures. Email delivery is at least once:
a process crash after SMTP accepts a message but before acknowledgement can repeat an email;
it cannot repeat a purchase/refund/check-in.

Configure `GUEST_CHECKIN_FRONTEND_URL` to the check-in frontend page, without credentials,
query or fragment; HTTPS is required outside DEBUG. The frontend reads and removes the
fragment, keeps the credential private and sends it only to check-in APIs. `.env.example`
contains an empty placeholder. Install the regenerated hashed requirements (ReportLab added)
using the documented Python 3.13.16 toolchain; do not hand-edit lock hashes.

## Verification record

The original restriction on tests was lifted by the user. Docker was unavailable in WSL,
so validation uses an isolated Python 3.13.16 environment and a temporary PostgreSQL 16.15
cluster bound to loopback port 55439. Dependencies are installed from the repository's
hashed lock files. No project or production database is used. PostgreSQL 17.11 remains the
project's Compose target; this local run does not certify that target environment.

| Verification | Result |
|---|---|
| Final complete backend suite (including config and all application tests) | **455 passed** in 120.68 s |
| Application statement coverage (`--cov=apps`) | **89.05%**: 3,529 / 3,963 statements |
| Business-service subset | **91.20%**: 1,140 / 1,250 statements across flights/services+operations, sales/services+rules+checkin+idempotency+locking, user services and wallet services |
| Real PostgreSQL concurrency cases | Passed, including competing seats, last capacity, duplicate purchase key and duplicate cancellation |
| New and upgrade migrations on the isolated PostgreSQL database | Passed; no pending migrations |
| `makemigrations --check --dry-run` | No changes detected |
| Django system check | No issues |
| OpenAPI `--validate --fail-on-warn` | Passed without warnings |
| Repository-wide `ruff check .` and `ruff format --check .` | Passed; 147 Python files formatted |
| `pip check` and `git diff --check` | Passed |

The first broad run exposed 14 inherited user-mail regressions. Removing synchronous
post-commit mail processing restored the durable-worker contract; its targeted suite passed
142 tests before the final full run. Earlier failed runs are diagnostic history, not the
current verification result. New business services individually exceed the project's 70%
statement-coverage reference; this is test evidence, not proof of all possible behaviors.

To repeat the suite in the project target environment (Docker commands are documented,
not executed in this WSL session):

```bash
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest --cov=apps --cov-report=term-missing
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

The source of the tests is versioned in `backend/apps/*/tests/`, including the new
`sales/tests/test_iteration03.py`. Generated local schema/coverage reports are temporary
artifacts; no CI run or external review is claimed.

Coverage cases include client/administrator/guest authorization, ownership, paid-price
preservation, explicit price acceptance, duplicate request payloads, promotion boundaries,
unpaid cancellation, exact national/international cutoffs, full refund rollback, active-seat
uniqueness, grouped check-in atomicity, PDF retry, guest CSRF/throttling, and real concurrent
seat/refund operations using separate PostgreSQL connections and synchronization barriers.
No finite test suite proves every possible input or execution schedule.

## Instructions for teammates' AI assistants

1. Read root/docs AGENTS, the current clarifications, this report and the relevant HU/CU.
2. Start from the selected integrated baseline; preserve Spanish domain models and existing
   migrations. Do not recreate duplicate flights/sales schemas from the old users-only branch.
3. Use the common services and transaction boundary for every inventory mutation. Do not
   directly edit counters, active seats or balances from a new view, signal or command.
4. Integrate the API changes above before claiming frontend completion. Server errors and
   eligibility are authoritative; browser seat maps and totals are snapshots.
5. Preserve paid prices and original-buyer refunds. Reconcile ambiguous legacy accounting
   rather than bypassing the new debit requirement to make a demo succeed.
6. Never use ROOT/staff/superuser as a substitute for administrator business permissions.
7. Do not log magic links, passwords, CSRF/session cookies, full traveler data or SMTP errors.
8. Preserve durable notification jobs and process external work outside business locks.
9. Record test environment/results accurately. PostgreSQL 16 local results, PostgreSQL 17
   CI, real SMTP, frontend integration, performance and deployment are distinct evidence.
10. Commit/push/PR/deployment still require an explicit request. This branch's expanded task
    does not rewrite the team's general per-HU review/squash convention.


## Remaining integration work and practical limits

- Rebuild/install the hashed backend dependencies and apply the new migrations in the
  intended development environment; only the isolated test database was migrated here.
- Adapt frontend request fields, quote confirmation, operation keys and the new workflow
  screens. The backend work does not certify the current UI as end-to-end complete.
- Configure the check-in frontend URL and schedule expiry plus **all** user, purchase and
  journey mail processors. No real SMTP provider or OS/container scheduler was exercised.
- Repeat target deployment checks on the project's PostgreSQL 17.11/Compose environment.
  CI, deployment, load/latency goals and academic/team review were not observed.
- Reconcile ambiguous legacy accounting or duplicate active seats before migration/use;
  safeguards intentionally reject unsupported refunds rather than fabricate transactions.
- HU-010/011 payment methods, withdrawal second factor, general HU-018 subscriptions and
  international return-route expansion are not implemented by this iteration. Promotions
  publish queryable news; subscriber-management infrastructure remains its own story.
- A downloaded boarding pass cannot be recalled. The system invalidates its check-in and
  stops serving it through authorized APIs after the relevant change.
