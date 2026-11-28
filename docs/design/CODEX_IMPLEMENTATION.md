# Codex — Reference-driven implementation brief

Use `docs/design/` as the proposed visual reference for Alas. The user requests a professional commercial experience, not a new architecture. Inspect the actual working tree and current Markdown decisions first. Do not revert backend work or restore outdated ERS requirements.

## Scope and visual authority

- Read `DESIGN_SYSTEM.md`, `UX_GUIDELINES.md`, `SCREEN_MAP.md` and `manifest.json`.
- For each assigned milestone, open the matching HTML, `assets/design.css`, and desktop/mobile screenshots. Reproduce composition, spacing, hierarchy, typography, controls and visual states in existing React components. The CSS is reference code, not a command to overwrite styles blindly.
- The screenshots contain fictional data; connect UI to current authorized APIs and exact models. Never copy static prices, balances, metrics, contact data, brand inference or navigation demo links as real application behavior.
- `demo.js` is only a local interactive illustration; do not copy mock business logic, demo toasts, footer labels or preview navigation to production components.
- Significant visual identity, navigation, data model or business policy changes require explicit approval. Resolve open decisions in `UX_GUIDELINES.md` before implementing affected behavior; continue independent approved tasks. Preserve existing repository instructions and AGENTS files.

## Ordered milestones (one at a time)

1. Stabilize actual runtime. Verify CSRF cookie/header/Origin and Django trusted origins; do not weaken CSRF. Check `api.ts` BASE prefix and call activity as `/auth/session/activity/` if BASE still `/api/v1`. All three demo roles authenticate, logout and preserve correct session/role states. Fix common layout containers, field styling, duplicated labels and responsive overflow. Build shared reusable components and selectors.
2. Registration and profile. Move mandatory billing location/address from user creation to individual payment methods. Verify serializer, model constraints, service, profile contract, migrations and tests. Do not discard old billing data. Keep birthplace worldwide and hierarchical.
3. Payment methods, wallet and checkout. Inspect current PaymentMethod and deposit contracts; change to approved 16-digit test card and per-method billing requirements. No real banking. CVV demo client-side only; reject real PAN through explicit synthetic fixture validation. Preserve HMAC and last four, owner/expiry/active checks, atomic deposits and idempotency, historical reference. Existing bank-account support preserved pending decision. Use normal commercial wording including history/reference defaults; do not rewrite historical transactions. New customer zero balance; no usable method means funding disabled with add-method CTA. Preserve checkout context and requote before purchase. No HU-011 implementation.
4. Flight search and cards. Implement `precio_min`, `precio_max`, stable ordering price/time if approved, consistent current eligible class price, no sort on stale base fare; validate range. Apply filters to whole result set, not only an arbitrary page. Preserve class, availability, date and route constraints and separate commercial vs admin catalogues. Handle compatible return flights and review total. Clarify unspecified-class and default order.
5. My trips, cancellations, check-in and seats. Preserve existing ownership, pending resolution, refund integrity, time cutoffs, group/guest scope and PDF rules. Ensure affected itinerary and exact total refund shown before confirmation; review reprogramming incompatibility and already-performed legs. Do not invent new entitlement or new cancellation policy. Use actual API IDs and seat map.
6. ADMINISTRADOR and ROOT. Professional operational layout and security/account forms, no wallet or client actions for these roles. Preserve admin-only flight management and ROOT-only administrator management. Use existing backend password-change endpoints; force re-login after own ROOT password change. Any proposed additional dashboard metrics require approval.
7. Integrated acceptance and documentation. Use the running application, screenshots and functional checks. Update project decisions, API schema, tests and cumulative delivery checkpoint; keep historical evidence separate.

## Per-milestone verification

- Build `npm ci` when needed and `npm run build`. Run targeted backend checks and pytest on isolated PostgreSQL; full suite at integration checkpoint. Do not weaken tests or use shared/production databases.
- Browser: desktop 1440×1000, tablet 768×1024, mobile 390×844. Use Playwright if available/authorized. Inspect real DOM and screenshot (not static HTML alone); compare with reference. Verify no page-level horizontal overflow, no clipped CTA, visible focus, correct errors and no console/network failures in the assigned flow. Test loading, empty, error, success and uncertain request outcome, not just happy path.
- Record actual test evidence (command, result, environment, commit/worktree), screenshot paths, known blockers and next bounded step. If browser automation unavailable, provide exact manual checks and mark them unverified. Never claim full-stack verification based on design screenshots or a build.

## Constraints

Resource limits are significant. Work on one explicitly assigned milestone; avoid repository-wide repeated scans. Read only relevant files, run targeted tests, document checkpoint before stopping. Do not commit, push, merge, deploy, send real email, delete volumes or modify shared/production data without explicit authorization. Communicate decisions and results in Spanish.

## Short continuation prompt

> Read docs/design/CODEX_IMPLEMENTATION.md and the latest project checkpoint. Implement only milestone [N]. Use the relevant HTML and PNG as visual references, preserve current backend contracts except explicitly approved changes, verify in the running browser and record evidence. Ask before implementing unresolved decisions. Stop after the milestone.
