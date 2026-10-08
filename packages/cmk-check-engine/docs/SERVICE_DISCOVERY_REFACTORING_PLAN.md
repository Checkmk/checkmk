# Service Discovery Refactoring — Plan

**Epic:** CMK-32255 _Simplify/Rewrite Service Discovery_
**Target release:** 3.0.0 — not a roadmap priority; correctness over speed.
**Component ownership:** Check and Discovery Engine only. No cross-component sign-off needed.
**Status:** Phase 0 delivered. **Backend track (Phases 2–3) live; UI track (Phases 4–5) parked** — see
"Two tracks" below. (Phase 1 was absorbed into Phase 3 on 2026-09-17.)
**Companion documents:** `SERVICE_DISCOVERY_DOMAIN_MODEL.md` (the target model, cited as DM) and
`SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md` (today's behaviour, the divergences and the guardrail tests,
cited as matrix). Neither is summarised here.

### Two tracks (2026-10-08)

A PM sync settled that the **UI rewrite needs PM/UX involvement and therefore roadmap capacity,
which is not available**, so the Vue frontend will not be built for an unspecified time. The epic's
two deliverables (§1) share only the contract, so this parks one track without stalling the other:

- **Backend track — live.** Phase 2 (contract) and Phase 3 (core swap; Phase 1's analysis is already
  absorbed into it). The core swap — the `DiscoveryState` decomposition and the 208 → 10 transition
  collapse — is the epic's single largest structural simplification and needs no frontend. It leaves
  a clean backend under an _unchanged_ legacy page (kept behind a now-permanent `DiscoveryState`
  facade; see Phase 3), so it carries the bulk of the payoff — but not the read-path/job decoupling,
  which can only complete once the legacy page is deleted.
- **UI track — parked.** Phase 4 (the Vue app) is blocked on PM/UX + roadmap; Phase 5 (cutover and
  deletion) depends on the new page existing, so it parks with it, and with it everything the
  deletion alone delivers (§3 Phase 5).

**Sequencing.** Phase 3 is the priority and can start before Phase 2 (its gate is the Phase 0 matrix,
not the contract); only its _completion_ — real enums, the D11 concurrency mechanism, Phase 1's
collision guard — depends on Phase 2, which is otherwise driven solely by its standalone automation
value. This supersedes D2's "contract first, then backend". The §1 end state — _"No frontend code in
Python; the old GUI is deleted"_ — is unreachable until the UI track resumes; stopping after Phase 3
is a deliberate, defensible resting state (R6, R7).

---

## 1. Framing

The epic's ask is developer-facing: _"the workflow and implementation of the frontend and
backend for service discovery is pretty complex; also, it requires a lot of data being sent
back and forth"_. Two deliverables follow: a **maintainable backend** and a **new UI**.
They are separate goals sharing one dependency — a contract.

The end state, stated plainly:

> **No frontend code in Python.** A VueJS frontend talks to the REST API. The old GUI code
> is deleted.

That last clause drives a structural rule for this plan: **don't refactor what you're about
to delete.** The legacy page, its AJAX handler and its server-side renderer get touched as
little as possible — one mount point — and are then removed wholesale. Only the shared core
that survives gets cleaned up.

> **Parking note (2026-10-08):** with the UI track parked, the legacy page is no longer "about to
> be deleted" on a known horizon — but the rule holds unchanged, now for a different reason. We still
> do not improve it (D10): the Phase 3 swap cleans up the shared _core_ beneath it, not the page
> itself. `DiscoveryPageRenderer` stays ~1380 lines and reads `DiscoveryState` directly in ~99 places
> (including CSS classes built from the raw state strings), and the swap keeps a `DiscoveryState`
> facade precisely so it does not have to be rewritten (D10). So what persists is a clean backend
> under an _unchanged_ legacy page, not a thin shell — investing in that page would be wasted either
> way. "Deleted in Phase 5" below should be read as "deleted when the UI track resumes".

Concretely, which files survive matters:

| Path                                                                                                    | Fate                                                 |
| ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `cmk/gui/watolib/services.py`                                                                           | **Survives.** The shared core; cleaned up in Phase 3 |
| `cmk/gui/openapi/api_endpoints/service_discovery/`                                                      | **Survives.** Extended in Phase 2                    |
| `cmk/gui/wato/pages/services.py` (`ModeDiscovery`, `ModeAjaxServiceDiscovery`, `DiscoveryPageRenderer`) | **Deleted** in Phase 5. Minimal touch before that    |
| `packages/cmk-frontend/src/js/modules/service_discovery.ts`                                             | **Deleted** in Phase 5                               |

### Why the hackathon material can't be followed as-is

The kickoff document (`SERVICE_DISCOVERY_V2.md`, Gerrit 139402 — abandoned) is useful for UX
intent and as a map of the current implementation. It cannot serve as the plan:

1. **Its principle 4 is "backend unchanged below the GUI layer."** It keeps
   `watolib/services.py` intact and adds two endpoints on top — the opposite of this epic,
   and a net increase in total complexity.
2. **Its REST API analysis is stale.** It describes
   `cmk/gui/openapi/endpoints/service_discovery/__init__.py`. That directory is now empty; the
   family has been migrated to `cmk/gui/openapi/api_endpoints/service_discovery/`
   (VersionedEndpoint + Pydantic v2). Every path, gap and verdict in that section needs
   re-deriving.
3. **The PoC (Gerrit 140009) demonstrated the failure mode, not the design.** Of the real
   defects found in review, four are one bug repeated: _the new endpoint re-implemented a
   slice of `services.py` semantics and got it subtly wrong_ — apply path unconditionally
   local, so remote-site hosts get garbage written into the central cache; the second-pass
   `UPDATE_SERVICE_LABELS` call a silent no-op; `SINGLE_UPDATE` not adopting
   `new_discovered_parameters`, so Apply silently downgrades versus legacy Fix-all;
   permissions tightened to `wato.see_all_folders`, locking out users the legacy page admits.

**The PoC's backend is not salvageable** — wrong framework, wrong strategy. Its value is the
UX exploration. Mine it for interaction decisions; write the backend fresh.

### What CMK-37497 changes

CMK-37497 was scoped independently of this epic, as a small refactor of the REST call stack.
Its hand-off analysis turns out to identify the epic's keystone: `ServiceDiscoveryBackgroundJob`
currently owns _both_ async orchestration _and_ is the only way to obtain a preview
(`get_result` → `local_discovery_preview`). Breaking that weld reduces both front-ends to
three primitives:

```
compute_discovery_preview()   # synchronous — but not a pure cache read; see Phase 1
start_scan()                  # async, contacts the host
poll status                   # job status only
```

Once those exist, a Vue page over the REST API is a thin client. So CMK-37497 is absorbed into
Phase 3 (see correction), where the epic builds on its analysis.

**Correction (2026-09-17): CMK-37497 moves to Phase 3, it is not a standalone Phase 1.** A does not
reduce complexity on its own. Baseline `get_check_table` is already a _single_ read path; because the
GUI still consumes `job_status`, a behaviour-preserving change can only _add_ a job-free read beside
it or restate the fork more explicitly — the job-coupled read cannot go until the legacy page is
deleted (Phase 5). The three primitives above are the _target_, not something A delivers in isolation.
The A→C→B analysis (D is dead — D11 supersedes it) is the read-side seam of the Phase 3 core swap;
land it there, where the new core is written job-free and the old read is deleted in Phase 5.

---

## 2. Decisions taken

| #   | Decision                                                                                                                                                          | Consequence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | CMK-37497 is absorbed into Phase 3 (overlaps the core swap substantially); not a standalone Phase 1                                                               | Its A→C→B analysis is the read-side seam of the swap (D is dead — D11 supersedes it). Premise corrections and reasoning live in the hand-off; cold-cache "empty" behaviour stays 1:1                                                                                                                                                                                                                                                                                                                                                         |
| D2  | Then the contract; then backend and frontend proceed independently                                                                                                | The contract is the only synchronisation point                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| D3  | UI is a **column board**: services move between columns, decisions are revisable, submitted in bulk                                                               | Confirms the PoC's interaction principle                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| D4  | **Attention-first**: board defaults to undecided / changed / vanished; Monitored is a collapsed count, virtualized on expand                                      | Addresses clutter-at-scale without hiding data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| D5  | End state is the **public versioned REST API**. Development may start on internal endpoints and promote them once validated — decided in the implementation phase | Avoids premature public commitments while keeping one eventual surface                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| D6  | Read contract carries **scan lifecycle + per-source outcomes as first-class fields from day one**                                                                 | CMK-35050 fills placeholders; no contract change later                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| D7  | **Automation wire format is frozen** for this project                                                                                                             | New read models assembled above the automation boundary; zero mixed-version risk                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| D8  | The core stays in `cmk/gui/watolib`                                                                                                                               | No shared package needed within this scope. It is not one boundary, though: a single operation spans two sites' stores (DM §9.1, §9.2)                                                                                                                                                                                                                                                                                                                                                                                                       |
| D9  | CMK-37187 (CLI entrypoint divergence) is **out of scope**                                                                                                         | Sits below the watolib convergence line; neither blocks nor simplifies the GUI path                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| D10 | Old GUI code is touched minimally and deleted in Phase 5, not refactored                                                                                          | No effort spent improving code with a known end date                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| D11 | Concurrency token is the **table version already in the read model**, made a precondition of every write                                                          | Supersedes an earlier hash-based choice: the client already holds it and it is `0` during a scan, so one mechanism covers a stale page, an intervening scan and a concurrent admin — and it _replaces_ the job-active probe rather than adding to it (DM §9.4, matrix §11.4 item 6). How strict it is at the boundary is an API-ownership call: DM §12.7                                                                                                                                                                                     |
| D12 | Accepting host labels does **not** attempt to recompute which services are discovered                                                                             | Label-based rule matching can change discovery; requiring an explicit rescan is acceptable, as today                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| D13 | PM/UX are **not yet involved but must not be excluded**                                                                                                           | See Phase 4 and risk R3                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D14 | Feature-flag toggles are used during implementation — **frontend only**                                                                                           | Enables incremental landing and a controlled cutover of the page. The backend gets none: D16                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| D15 | **CMK-38599 (§10.5) is fixed before Phase 1 starts**                                                                                                              | The only confirmed divergence that changes data on every use and has no guardrail in any tier                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| D16 | The backend is **replaced by a module swap, not gated by a runtime flag**                                                                                         | A central-site toggle cannot reach the remote site's automations (D7's skew envelope), and an activated write is not undone by flipping it back. If a parallel implementation is wanted, the seam is D5's internal endpoints — versioned and opt-in per caller — not site config. See Phase 3                                                                                                                                                                                                                                                |
| D17 | **UI track is parked** (2026-10-08 PM sync): the Vue rewrite needs PM/UX + roadmap capacity, which is unavailable. Phases 4–5 are blocked until it resumes        | Supersedes the implied Phase 2→4 synchronisation urgency and D2's ordering (see "Sequencing" in Two tracks). Backend track (Phases 2–3) proceeds; Phase 3 becomes the priority (no frontend to unblock). D5's validation step (the UI exercising the endpoints before they are made public) has no validator while the UI track is parked. So Phase 2 stays on internal/experimental endpoints and no public contract is committed (R2). This resolves §6 open question 2 for the parked period: internal-first. See "Two tracks", R1 and R2 |

### Compatibility envelope (D7)

One minor version of skew in either direction: a site can talk to the previous minor version,
central and remote alike. For 3.0.0 that means the discovery automations must keep working
against the preceding minor. Since D7 freezes the wire format, this is satisfied by
construction — and it is why all new read shaping happens above the automation boundary.

### Known seam from D6 + D7

CMK-35050 wants per-source **state + summary + details + source type**, persisted on every
scan including failures. Today's `DiscoveryResult.sources` is `name → (state, output)`, so
state and summary are already available above the automation boundary and can be honest
immediately. **`details` and `source_type` cannot** be produced without a payload change, and
failures aren't persisted at all today. The contract should therefore carry those fields as
explicitly nullable and documented as "not yet populated"; CMK-35050 reopens D7 when it lands.
Deliberate, not an oversight.

### Cold cache: three claimants, now separated

- **CMK-31896** (fixed, 2.5.0p10 / 3.0.0) clears the cache on error so stale successes aren't
  served as current. Correct — and it makes the cold-cache hole _deeper_.
- **CMK-37497** preserves "empty on cold cache" 1:1 and explicitly does not fix it.
- **CMK-35050** fixes it.

Resolution: split one concept into two — cached **data** used to compute the table (cleared on
error, per CMK-31896) versus the last scan **outcome** used for display (always persisted, per
CMK-35050). Until CMK-35050 lands, the board treats a cold cache as a first-class _never
scanned_ state and offers a Scan action. It must **not** invent a preview cache to paper over
this; that is exactly what produced the PoC's first-scan `AttributeError`. One correction: **a
preview cache already exists** — the stored last preview, a second layer on top of the agent-data
cache (matrix §6.0). The rule is not to add a third.

---

## 3. Phases

### Phase 0 — Guardrails ✅ delivered

Exists because every PoC defect was semantic drift, and because nobody can currently state
today's behaviour precisely.

- **Characterization tests of the semantics that must survive** — the state × action → outcome
  matrix (~15 `DiscoveryState` values × ~11 `DiscoveryAction` values) — pinned at the
  `watolib/services.py` level. Deliberately _not_ at the AJAX transport level: that code is
  scheduled for deletion, so pinning it is wasted work. Existing ticket: **CMK-34150** —
  promote it from follow-up to prerequisite.
- **Remote-site coverage.** The single highest-value item in this plan. The PoC's tests
  monkeypatched `local_discovery_preview` and never exercised the remote branch; that is
  precisely how its worst bug survived review. `tests/run_tests.sh test-system-multisite` is
  the right home for the parity checks.
- **Deliverable: a written state × action → outcome matrix.** A document, not a test artifact.
  It is the input to both the contract and the UI, and it is what makes Phase 3's transition
  table reviewable.

**Delivered** on branch `cmk-34150`: two documents rather than one — the diff is only meaningful
against a stated target, so the matrix records today's behaviour and DM records the target — and
four test tiers, 539 cases plus 12 in the check-engine suite, 40 of them strict-xfail quarantine
tests carrying a ticket each (matrix §7).

**Exit criteria: met.** One qualification worth carrying forward: tier 4 first ran 2026-09-03 and
corrected a §10 severity claim that had been derived by reading — §10.17's `ignored` cell is a
silent no-op, not a cluster outage, because the write path restores what the transition drops. See
R5.

### Phase 1 — CMK-37497 (absorbed into Phase 3)

> **Revised (2026-09-17): CMK-37497 is absorbed into Phase 3** — see the §1 correction. Its analysis
> (A→C→B; D is dead) is the read-side seam of the core swap, not a standalone phase; the read is
> written job-free there and the old job-coupled read is deleted in Phase 5 with the legacy page.
> The material below is retained as that analysis.

Follow its hand-off: **A → C → B → D**.

- **A (keystone):** extract synchronous `compute_discovery_preview()`; stop routing
  `new`/`remove`/`fix_all`/`only_*_labels` through `ServiceDiscoveryBackgroundJob`.
- **C:** REST path returns `ServiceDiscoveryPreviewResult` directly; stop building the
  GUI-shaped `DiscoveryResult`. Verified schema-neutral.
- **B:** make the pre/post-write reads two explicit `compute_discovery_preview()` calls.
- **D:** scope the `job_snapshot` 409-guard to actions that can actually collide.

No behaviour change, including "empty on cold cache". The OpenAPI tests for this endpoint run under
bazel (`bazel test //tests/openapi:repo_community`) — they are the guard for the schema-unchanged
claim.

**Two premises need correcting first, both from Phase 0.**

1. **`get_result` is not a pure cache read.** A scan stores its own preview, the next read prefers
   that file over recomputing, and loading it unlinks it — so the first read after any scan is
   answered from the scan's table and only later ones recompute (matrix §6.0, §6.2). A must decide
   explicitly whether to keep that; extracting a "cache read" silently is a behaviour change.
2. **Idea D is superseded before it is written.** D11 replaces the job-active probe rather than
   narrowing it (matrix §11.4 item 6), so D as scoped implements a guard Phase 2 deletes. Reduce it
   to _removing_ the guard where it cannot collide, and leave the mechanism to Phase 2.

**Exit criteria:** the three primitives exist; `ServiceDiscoveryBackgroundJob` is reduced to
"run the scan, expose status" — the _scan's_ status, not discovery's (matrix §6.3); Phase 0 tests
green on local and remote. (With the UI parked the job-free read is only _added_ beside the
job-coupled one; the job's full reduction to scan-only lands at cutover — see "Two tracks".)

### Phase 2 — The contract

While the UI track is parked (D17) Phase 2 is driven only by its **standalone automation value** —
CMK-32562 canonical identity, the batch-apply endpoint, and the audit-log settling (F1) — and stays
on **internal/experimental endpoints** (no UI validates a public contract; R2). The
`openapi-typescript` generation step and the "frontend builds against a mock" exit criterion are
frontend-driven and defer with the UI track.

The linchpin. If this is wrong, Phases 3 and 4 diverge independently and the project fails the
way the PoC did. The Phase 0 matrix is the reference document for its review — and since the target
semantics are now written down too (DM §5, §6.2, §6.3, with the divergences to dispose of indexed in
matrix §11.5), much of this phase is ratification rather than design. **DM §12's open decisions are
the gate**; take §12.5 (exclusion identity) first, as the one that may need a config-format change.

**Canonical service identity.** Pull **CMK-32562** (support ServiceID) in here — critical path,
not adjacent. Batch apply needs a collision-free key; the kickoff doc already noted that
`{plugin_name}-{item}` collides when the item contains `-` and breaks when the item is `None`.

**Rich read endpoint.** Side-effect-free — today's GET can start a background job, which must
not survive. Carries: check table (incl. parameters, discovered labels, service labels,
found-on-nodes), host labels (current/new/vanished/changed), per-source outcomes, scan
lifecycle (never-scanned / running / succeeded / failed), config warnings, cluster node
tables, and the concurrency token.

**Batch apply endpoint.** New. Takes a set of `service_id → target disposition`, an
`update_host_labels` flag, and the token. Must define explicitly — these are exactly the
semantics the PoC got wrong:

- whether accepting a _changed_ service adopts `new_discovered_parameters` (the PoC silently
  did not — a functional downgrade versus legacy Fix-all);
- partial-failure behaviour: all-or-nothing, or per-item results;
- an identifier naming no service: today it is answered `204` with nothing written, so a whole
  batch of typos would report success. Matrix §10.19 prescribes `404`, and says why the lookup
  belongs at the endpoint rather than inside the transition;
- per-target-disposition permission checks (`wato.service_discovery_to_*`), matching the
  legacy page's model rather than tightening it;
- audit-log granularity — this is **story F1** from the epic comments, and the right place to
  settle it once for both actions;
- `409` on a stale token.

**Optimistic concurrency (D11).** Required by "discover once, act many". The client echoes the
table version it decided against; the server rejects if it has moved. Covers a concurrent admin, an
intervening scan and a stale browser tab in one mechanism, and replaces Phase 1's Idea-D guard.

**Deprecations.** `update_service_phase` (single service, re-runs discovery on every call) is
superseded by batch apply — mark deprecated, don't delete in 3.0.0. Note the collision: CMK-38598's
fix adds a required field to that same endpoint, and DM §12.7's optional-when-present-in-v1 is what
reconciles deprecating it with changing it.

**Compiler-enforced contract (UI track, deferred with it — D17).** `openapi-fetch` is already a
dependency, but there is no generation step — `quick-setup/rest-api/` hand-writes its
request/response schemas. Add `openapi-typescript` generation so schema drift is a build failure
rather than a runtime surprise. Cheap, and it is what makes D5 real rather than aspirational.

Documenting these endpoints properly also retires part of **CMK-29094**.

**Exit criteria, backend track:** the read and batch-apply endpoints are merged as
internal/experimental endpoints (D17, R2). The batch-apply semantics listed above are decided and
tested. Every write requires the D11 table version.

**Exit criteria, UI track (when it resumes):** TS types are generated from the schema. The frontend
builds against a mock that satisfies it.

### Phase 3 — Backend replacement (the priority; UI track parked)

Scoped to the code that survives. **No old GUI code is touched here** (D10).

The transition core is **replaced, not refactored** (D16). `compute_discovery_transition` is
already a fold producing a `DiscoveryTransition` value — pure once `_verify_permissions` and
`_get_table_target` are lifted to parameters — so it is swapped as one module in one commit, with
the Phase 0 matrix as the acceptance gate. The 208 → 10 collapse below cannot be reached in
behaviour-preserving steps, which is why there is no incremental path here and no flag.

**How "no GUI code touched" is honoured (D10).** The legacy renderer reads `DiscoveryState` directly
in ~99 places (`DiscoveryPageRenderer`, pages/services.py), including CSS classes built from the raw
state strings. The swap does not adapt that code; its new core keeps emitting `DiscoveryState`-shaped
output — a **facade in the core** (`watolib/services.py`) that maps the new internal axes back to
today's state strings — and the page consumes it unchanged. In the original plan that facade was a
short-lived bridge to be deleted in Phase 5. **With the UI parked it is permanent** — the price of
leaving the page untouched. It is one of the two serialization boundaries the "Real enums" bullet
below describes; the other, the D7-frozen automation wire format, is permanent regardless.

- **Decompose `DiscoveryState`.** Its 15 declared values (13 reachable) conflate four orthogonal
  axes — lifecycle (new/unchanged/changed/vanished), disposition
  (monitored/ignored/undecided/removed), origin (discovered/enforced/active/custom) and clustering.
  That conflation is why the `_case_*` handlers are unreadable. Replace with orthogonal axes plus
  one explicit, **total** transition table, exhaustively unit-tested against the Phase 0 matrix —
  **generated** from DM §6.2 rather than transcribed (matrix §11.4 item 5). The target is five
  states × three commands — 15 cells, 10 of them meaningful, against the 208 pairs reachable
  through `update_service_phase` today — plus two row-level gates. That ratio is why this is the
  single largest simplification available.
- **Real enums — internally only, and bounded by two serialization boundaries that outlive the
  page.** The decomposed model can use real enums _inside_ the core, but it must still serialize to
  strings at two boundaries: the `DiscoveryState` facade for the legacy page (until cutover) and, more
  fundamentally, `DiscoveryResult.serialize`/`deserialize`
  (`repr()`/`ast.literal_eval()`, watolib/services.py) — the **central↔remote automation wire format,
  frozen by D7 and therefore permanent**. The browser hop is only a second user of that format, so
  deleting the legacy page does _not_ retire it. The code comment "must be strings … exported to
  javascript" (watolib/services.py) captures only the JS half; the automation half is the binding one.
  So "real enums everywhere" is **not** a Phase 5 deliverable — it is reachable only above the
  automation boundary, where new read shaping already lives (D7). Treat the string representation as a
  permanent serialization detail, not something the UI track's return would remove.
- **Story F2:** `TABULA_RASA` becomes _invalidate cache + `start_scan` + fix-all_ instead of a
  second implementation path. Nearly free once Phase 1's primitives exist; matrix §6.3 lists what
  it deletes in one move.
- **Story F3 (backend half):** update the user-visible background-job title; the internal
  `DiscoveryAction.TABULA_RASA` constant stays for API and change-log compatibility. The new
  wording ships with the new page in Phase 4.
- **Remove the mypy suppressions** at the top of `watolib/services.py` — a concrete, verifiable
  success criterion for "less error-prone". A second one: **T1b.12 must XPASS**, because §10.11
  disappears by construction in this model rather than by fix (matrix §11.4 item 7).

`bulk_discovery.py`, DCD and periodic discovery consume `check_mk_automations` directly and never
import `watolib.services`, so the swap does not reach them. Only three call sites do: the legacy
page, the REST endpoints and Quick Setup.

### Phase 4 — Frontend 🚧 BLOCKED (UI track parked — D17)

Blocked on PM/UX capacity (see "Two tracks"). The scope below is the spec to resume from; only
D13's first step — engineering drafting the interaction spec — can proceed without capacity.

New Vue app under `packages/cmk-frontend-vue/src/`. Written fresh; the PoC informs UX only.
Behind a feature-flag toggle (D14), so it lands incrementally alongside the legacy page.

**Interaction model.** Columns are **target dispositions**; cards are services; moving a card
stages a transition; current state is a badge on the card; nothing reaches the server until an
explicit bulk submit. Attention-first per D4.

**Involve PM/UX (D13).** They have not been involved yet and should not be bypassed. The
practical sequence: engineering drafts a short interaction spec (columns, transitions, empty
states, error states, keyboard map), PM/UX review it _before_ the model is locked in code, and
validate against a large-host fixture.

**Keyboard-first, not drag-first.** With WCAG 2.1 AA as the stated bar, drag-and-drop must be
an _enhancement_ over a primary "select → move to" action. That primary path is also what makes
bulk operations and screen readers work. Do not ship a drag-only board.

**Component discipline.** The PoC reproduced the god-object problem in TypeScript —
`ServiceCard.vue` at 1233 lines, `ServiceDiscoveryApp.vue` at 950, and ~1900 lines of
orphaned-but-bundled components after it pivoted from tables to a board. Set a hard budget (no
component beyond roughly 250 lines; state in composables, not components) and treat
unreferenced components as a review blocker.

**Also in scope:** i18n from the start; honest empty states for _never scanned_ / _scan
running_ / _scan failed_; Vitest component and composable tests; GUI coverage via
`tests/run_tests.sh test-system-gui`.

**Validate at scale early.** Build a fixture host with several hundred services and test the
board against it before the interaction model is locked. A column board degrades worse than a
table here; D4 is the mitigation — confirm it actually works.

**Minimal legacy touch:** one mount point in `ModeDiscovery.page()`, flag-gated. Nothing else.

### Phase 5 — Cutover and deletion 🚧 BLOCKED (depends on Phase 4)

Blocked: there is nothing to cut over _to_ until the Vue page exists (see "Two tracks"). The
`DiscoveryState` facade and the job-coupled read park here too — they cannot go until the legacy
page does.

The payoff phase. Flip the flag, then delete:

- `cmk/gui/wato/pages/services.py` — `ModeAjaxServiceDiscovery`, `DiscoveryPageRenderer`, the
  legacy `ModeDiscovery` rendering path;
- the `DiscoveryState` facade in `watolib/services.py` that the swap kept for that page — now unused,
  so the core can shape its output above the automation boundary instead;
- `packages/cmk-frontend/src/js/modules/service_discovery.ts`;
- the **browser-hop use** of the `repr()` / `ast.literal_eval()` DTO serialization (the call sites in
  pages/services.py). The `DiscoveryResult` serializer itself stays — it is also the D7-frozen
  central↔remote automation wire format — as does the sibling `repr()` format the preview store uses
  for `ServiceDiscoveryPreviewResult` (in `cmk/automations/results/discovery.py`); both survive the
  deletion.

Removing HTML-over-the-wire closes **CMK-19765** (the OWASP `)(!` false positive) as a side
effect.

Write the deletion commit up front so it cannot be quietly deferred, and keep the toggle window
bounded to one release cycle. Werks for the UI change and the deprecations.

Then, as separate work: **CMK-35050** (faithful source failures — reopens D7), **CMK-32560**
(parallel fetching), **CMK-37187** (CLI convergence).

---

## 4. Ticket disposition

| Ticket                            | Role                                                                                                                                          |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| CMK-37497                         | Phase 3. Absorbed into the core swap; A→C→B read-side seam, D dead                                                                            |
| CMK-34150                         | Phase 0. Promoted to prerequisite. **Done**                                                                                                   |
| CMK-38599 (§10.5)                 | **Before Phase 1** (D15). Ships a slice of DM §6.1 Gate 0 — clustered rows stop being retargeted — so the Gate 0 werk must not re-announce it |
| CMK-38587 … CMK-38598             | The other 12 divergence tickets — indexed below                                                                                               |
| CMK-38679                         | **Not this epic.** Matcher-owned, spun out of the tier-2/4 review                                                                             |
| CMK-32562                         | Phase 2. Critical path — batch apply needs a canonical key                                                                                    |
| Story F1 (audit log)              | Phase 2. Settled once, in the batch-apply design                                                                                              |
| Story F2 (TABULA_RASA dedup)      | Phase 3. Nearly free after Phase 1                                                                                                            |
| Story F3 (rename)                 | Phase 3 backend half; new wording ships in Phase 4                                                                                            |
| CMK-29094 (ReDoc descriptions)    | Phase 2, partially                                                                                                                            |
| CMK-19765 (OWASP false positive)  | Phase 5. Closed by deleting HTML-over-the-wire                                                                                                |
| CMK-35050                         | Follow-on. Contract reserves its fields (D6); may reopen D7                                                                                   |
| CMK-32560                         | Follow-on. Independent performance change                                                                                                     |
| CMK-37187                         | Out of scope (D9)                                                                                                                             |
| CMK-28034 (no progress indicator) | **Not planned.** Probably a transient issue left open; keep in mind while building the new page                                               |
| CMK-31896                         | Already fixed; informs the cold-cache split                                                                                                   |

### The divergence tickets from Phase 0

All thirteen are linked to CMK-32255 and filed against Check and Discovery Engine. The `swap`
column says what Phase 3's replacement does to each: **✅** five disappear by construction; **◐**
two lose the transition-level defect but keep a second one in another layer; **—** six sit in a layer
the swap never touches — Phase 2's contract, a caller, or below the automation boundary — and must be
fixed on their own.

| ticket    | §            | swap | ticket    | §     | swap |
| --------- | ------------ | ---- | --------- | ----- | ---- |
| CMK-38587 | 10.1         | ✅   | CMK-38594 | 10.4  | —    |
| CMK-38588 | 10.3 + 10.14 | —    | CMK-38595 | 10.9  | ◐    |
| CMK-38589 | 10.8         | ✅   | CMK-38596 | 10.10 | —    |
| CMK-38590 | 10.11        | ✅   | CMK-38597 | 10.15 | —    |
| CMK-38591 | 10.13        | —    | CMK-38598 | 10.18 | —    |
| CMK-38592 | 10.16 + 11.3 | ✅   | CMK-38599 | 10.5  | ✅   |
| CMK-38593 | 10.17        | ◐    |           |       |      |

Off the critical path except CMK-38599 (D15), with one caveat: the swap is master-only, so **a
backport un-subsumes**. Any **✅** ticket a customer needs in a released branch is fixed twice — on
the branch, and preserved through the swap. CMK-38599 is the live case and the template. Land the
**—** rows before the swap so its verification is not confounded; CMK-38591 and CMK-38596 are cheap
and sit in files it never touches. CMK-38597 (§10.15) belongs to the Nagios config writer and should
be re-parented off this epic.

Ten own a strict-xfail guardrail, deleted with the fix when a ticket is fixed on its own — the
conformance test beside it already pins the result. **When one change clears several at once, flip
instead of delete**: drop the `xfail` mark, delete the paired `test_current_outcome`, keep
`test_intended_outcome` as a plain assertion. Both halves of a pair go red on the swap, so the
quarantine file changes in that commit either way; flipping makes it gain guardrails instead of
shedding ten. The Jira label `discovery-quarantine` finds the ones that forgot, and is the only part
of that mechanism living outside the repo, the guardrails themselves being self-enforcing. One
literal is shared by CMK-38589 and CMK-38593, so it clears only once both land.

Five **✅** tickets are five separately observable behaviour changes, and werks are searched by
symptom — so the swap needs five werks, not one.

**The §10 items that own no ticket.** §10.2 is resolved as not-a-defect. §10.19 is left unticketed
as low priority — Phase 2 disposes of it. §10.6, §10.7, §10.12 and §10.14 step 3 are requirements of
this epic rather than tickets; §10.12 is Phase 3's first bullet, §10.14 step 3 is an API-ownership
call for Phase 2, and §10.6 and §10.7 are settled by the contract's permission model and the new
board. §10.7 is a defect of the legacy page, which D10 leaves unfixed, so it waits with the UI
track.

---

## 5. Risks

| #   | Risk                                                                                                                                                                                                                                                                                     | Mitigation                                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | **The contract is a single point of failure.** Wrong in Phase 2 → its consumers diverge, exactly as the PoC did. **Reduced while the UI track is parked (D17):** no Vue consumer is built, so the central divergence risk is dormant, and Phase 2 is scoped to internal/automation value | Phase 0 matrix as the review reference; keeping Phase 2 on internal endpoints (D17) so mistakes stay cheap. The generated-TS-types mitigation is deferred with the UI track — not a gap while there is no TS consumer, but it must land before the frontend builds against the schema                                                                                                                               |
| R2  | **Public API permanence.** A batch-apply endpoint shipped in 3.0.0 cannot be quietly reshaped. **Sharpened by the parking:** D5's validator — the UI exercising the endpoint — no longer exists, so shipping it public now would commit an unvalidated contract                          | D17's resolution: keep Phase 2 on internal/experimental endpoints for the parked period (resolves §6 open question 2 internal-first); do **not** promote to public until a real consumer — the resumed UI, or a committed automation consumer — has validated it                                                                                                                                                    |
| R3  | **UX decided without PM/UX**, on a genuinely new interaction model                                                                                                                                                                                                                       | D13: interaction spec reviewed by PM/UX before the model is locked in code; validate on a large host with real admins before cutover                                                                                                                                                                                                                                                                                |
| R4  | **Column board degrades at scale** worse than a table                                                                                                                                                                                                                                    | D4 plus the Phase 4 large-host fixture, exercised before the model is locked                                                                                                                                                                                                                                                                                                                                        |
| R5  | **Remote-site behaviour is the historical blind spot** — where the PoC broke and where the tests weren't                                                                                                                                                                                 | Phase 0's tier 4 via `test-system-multisite`, at every phase exit rather than at the end. But a parity assertion is **blind to any defect symmetric across sites** — of the 19 §10 items only §10.10 is asymmetric — so "parity" must mean pinning **absolute per-site outcomes**, not comparing the two sites                                                                                                      |
| R6  | **Deletion never happens.** Was: Phase 5 slips and _both_ implementations live on. **Inverted by the UI parking (D17):** no second implementation is built, so the risk is now that the _legacy_ page lives on indefinitely as code we keep but never retire                             | Softened, not removed. The Phase 3 core swap cleans up the shared backend beneath the page; the page itself stays (~1380-line renderer, kept behind a `DiscoveryState` facade — D10), so it is not "thin", but it is left _untouched_ and cheap to carry — a better resting state than today's. Deletion still happens when the UI track resumes; the up-front deletion commit and bounded toggle window apply then |
| R7  | **Not a roadmap priority** — the plan stalls mid-way and leaves things half-migrated                                                                                                                                                                                                     | Realised at the UI boundary (D17), and handled by design: the backend track is independently shippable and **stopping after Phase 3 is a deliberate, defensible resting state**, not a half-migration. CMK-37497 standalone only adds a seam (§1 correction, 2026-09-17), so it is absorbed into Phase 3 rather than left as a loose end                                                                            |

---

## 6. Open questions

1. **Is a write to a host on a remote site read-your-write?** Config sync reaches the remote with
   activation suppressed and the automation helper picks the change up at its next reload, with no
   happens-before edge (matrix §6.1) — so a read issued straight after an apply can legitimately
   answer with the pre-write table. The contract must either return the new table from the apply or
   tell the client to poll.
2. ~~Whether to start on internal endpoints and promote, or go public immediately (D5).~~
   **Resolved by D17 for the parked period: internal-first**, since there is no UI consumer to
   validate a public contract (R2). Revisit if a committed automation consumer appears before the UI
   track resumes.
3. How wide the flag-gated coexistence window should be, and whether the toggle is per-site or
   per-user during development. _(Deferred with the UI track — moot until Phase 4 resumes.)_

### Recorded intent, out of scope

- **`bulk_discovery` should eventually move onto the same primitives.** Not in this epic, but
  the intended direction.
- **Autodiscovery may benefit similarly.** Worth evaluating once the primitives are settled.
- **CMK-37187** (CLI convergence) remains the natural third consumer if the transition layer
  ever moves out of `cmk/gui`.
