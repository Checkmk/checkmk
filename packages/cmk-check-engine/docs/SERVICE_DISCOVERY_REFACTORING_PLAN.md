# Service Discovery Refactoring — Plan

**Epic:** CMK-32255 _Simplify/Rewrite Service Discovery_
**Target release:** 3.0.0 — not a roadmap priority; correctness over speed.
**Component ownership:** Check and Discovery Engine only. No cross-component sign-off needed.
**Status:** planning. No code written against this yet.

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
compute_discovery_preview()   # synchronous, pure cache read (prevent_fetching=True)
start_scan()                  # async, contacts the host
poll status                   # job status only
```

Once those exist, a Vue page over the REST API is a thin client. So CMK-37497 ships first,
scope unchanged, and the epic builds on its output.

---

## 2. Decisions taken

| #   | Decision                                                                                                                                                          | Consequence                                                                                          |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| D1  | CMK-37497 ships first, as scoped (A→C→B→D), strictly behaviour-preserving                                                                                         | Cold-cache "empty" behaviour stays 1:1; not fixed there                                              |
| D2  | Then the contract; then backend and frontend proceed independently                                                                                                | The contract is the only synchronisation point                                                       |
| D3  | UI is a **column board**: services move between columns, decisions are revisable, submitted in bulk                                                               | Confirms the PoC's interaction principle                                                             |
| D4  | **Attention-first**: board defaults to undecided / changed / vanished; Monitored is a collapsed count, virtualized on expand                                      | Addresses clutter-at-scale without hiding data                                                       |
| D5  | End state is the **public versioned REST API**. Development may start on internal endpoints and promote them once validated — decided in the implementation phase | Avoids premature public commitments while keeping one eventual surface                               |
| D6  | Read contract carries **scan lifecycle + per-source outcomes as first-class fields from day one**                                                                 | CMK-35050 fills placeholders; no contract change later                                               |
| D7  | **Automation wire format is frozen** for this project                                                                                                             | New read models assembled above the automation boundary; zero mixed-version risk                     |
| D8  | The core stays in `cmk/gui/watolib`                                                                                                                               | No shared package needed within this scope                                                           |
| D9  | CMK-37187 (CLI entrypoint divergence) is **out of scope**                                                                                                         | Sits below the watolib convergence line; neither blocks nor simplifies the GUI path                  |
| D10 | Old GUI code is touched minimally and deleted in Phase 5, not refactored                                                                                          | No effort spent improving code with a known end date                                                 |
| D11 | Concurrency token is **hash-based** rather than a timestamp                                                                                                       | More robust than `check_table_created`; exact shape in Phase 2                                       |
| D12 | Accepting host labels does **not** attempt to recompute which services are discovered                                                                             | Label-based rule matching can change discovery; requiring an explicit rescan is acceptable, as today |
| D13 | PM/UX are **not yet involved but must not be excluded**                                                                                                           | See Phase 4 and risk R3                                                                              |
| D14 | Feature-flag toggles are used during implementation                                                                                                               | Enables incremental landing and a controlled cutover                                                 |

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
this; that is exactly what produced the PoC's first-scan `AttributeError`.

---

## 3. Phases

### Phase 0 — Guardrails

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

**Exit criteria:** current semantics documented and pinned by tests that fail if they change,
on both local and remote hosts.

### Phase 1 — CMK-37497, as scoped

Follow its hand-off: **A → C → B → D**.

- **A (keystone):** extract synchronous `compute_discovery_preview()`; stop routing
  `new`/`remove`/`fix_all`/`only_*_labels` through `ServiceDiscoveryBackgroundJob`.
- **C:** REST path returns `ServiceDiscoveryPreviewResult` directly; stop building the
  GUI-shaped `DiscoveryResult`. Verified schema-neutral.
- **B:** make the pre/post-write reads two explicit `compute_discovery_preview()` calls.
- **D:** scope the `job_snapshot` 409-guard to actions that can actually collide.

No behaviour change, including "empty on cold cache". Note the ticket's own warning that the
OpenAPI tests for this endpoint run via `tests/run_tests.sh`, **not** bazel — they are the
guard for the schema-unchanged claim.

**Exit criteria:** the three primitives exist; `ServiceDiscoveryBackgroundJob` is reduced to
"run the scan, expose status"; Phase 0 tests green on local and remote.

### Phase 2 — The contract

The linchpin. If this is wrong, Phases 3 and 4 diverge independently and the project fails the
way the PoC did. The Phase 0 matrix is the reference document for its review.

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
- per-target-disposition permission checks (`wato.service_discovery_to_*`), matching the
  legacy page's model rather than tightening it;
- audit-log granularity — this is **story F1** from the epic comments, and the right place to
  settle it once for both actions;
- `409` on a stale token.

**Optimistic concurrency (D11).** Required by "discover once, act many". The client echoes a
content hash; the server rejects if the underlying preview changed. Covers a concurrent admin,
an intervening scan, and a stale browser tab in one mechanism, and subsumes Phase 1's Idea-D
guard.

**Deprecations.** `update_service_phase` (single service, re-runs discovery on every call) is
superseded by batch apply — mark deprecated, don't delete in 3.0.0.

**Compiler-enforced contract.** `openapi-fetch` is already a dependency, but there is no
generation step — `quick-setup/rest-api/` hand-writes its request/response schemas. Add
`openapi-typescript` generation so schema drift is a build failure rather than a runtime
surprise. Cheap, and it is what makes D5 real rather than aspirational.

Documenting these endpoints properly also retires part of **CMK-29094**.

**Exit criteria:** schema merged; TS types generated from it; the frontend can build against a
mock that satisfies the schema.

### Phase 3 — Backend cleanup (parallel with Phase 4)

Scoped to the code that survives. **No old GUI code is touched here** (D10).

- **Decompose `DiscoveryState`.** Its ~15 values conflate four orthogonal axes — lifecycle
  (new/unchanged/changed/vanished), disposition (monitored/ignored/undecided/removed), origin
  (discovered/enforced/active/custom) and clustering. That conflation is why the `_case_*`
  handlers are unreadable. Replace with orthogonal axes plus one explicit, **total** transition
  table, exhaustively unit-tested against the Phase 0 matrix. The single largest simplification
  available.
- **Real enums.** The "must be strings for JS serialization" constraint dies once the boundary
  is a Pydantic schema.
- **Story F2:** `TABULA_RASA` becomes _invalidate cache + `start_scan` + fix-all_ instead of a
  second implementation path. Nearly free once Phase 1's primitives exist.
- **Story F3 (backend half):** update the user-visible background-job title; the internal
  `DiscoveryAction.TABULA_RASA` constant stays for API and change-log compatibility. The new
  wording ships with the new page in Phase 4.
- **Remove the mypy suppressions** at the top of `watolib/services.py` — a concrete, verifiable
  success criterion for "less error-prone".

Verify that `bulk_discovery.py`, DCD and periodic discovery still behave once the primitives
are extracted. They are not being migrated here, but they are consumers.

### Phase 4 — Frontend (parallel with Phase 3)

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

### Phase 5 — Cutover and deletion

The payoff phase. Flip the flag, then delete:

- `cmk/gui/wato/pages/services.py` — `ModeAjaxServiceDiscovery`, `DiscoveryPageRenderer`, the
  legacy `ModeDiscovery` rendering path;
- `packages/cmk-frontend/src/js/modules/service_discovery.ts`;
- the `repr()` / `ast.literal_eval()` DTO serialization on the browser hop, which dies with the
  code that used it.

Removing HTML-over-the-wire closes **CMK-19765** (the OWASP `)(!` false positive) as a side
effect.

Write the deletion commit up front so it cannot be quietly deferred, and keep the toggle window
bounded to one release cycle. Werks for the UI change and the deprecations.

Then, as separate work: **CMK-35050** (faithful source failures — reopens D7), **CMK-32560**
(parallel fetching), **CMK-37187** (CLI convergence).

---

## 4. Ticket disposition

| Ticket                            | Role                                                                                            |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| CMK-37497                         | Phase 1. Ships first, scope unchanged                                                           |
| CMK-34150                         | Phase 0. Promoted to prerequisite                                                               |
| CMK-32562                         | Phase 2. Critical path — batch apply needs a canonical key                                      |
| Story F1 (audit log)              | Phase 2. Settled once, in the batch-apply design                                                |
| Story F2 (TABULA_RASA dedup)      | Phase 3. Nearly free after Phase 1                                                              |
| Story F3 (rename)                 | Phase 3 backend half; new wording ships in Phase 4                                              |
| CMK-29094 (ReDoc descriptions)    | Phase 2, partially                                                                              |
| CMK-19765 (OWASP false positive)  | Phase 5. Closed by deleting HTML-over-the-wire                                                  |
| CMK-35050                         | Follow-on. Contract reserves its fields (D6); may reopen D7                                     |
| CMK-32560                         | Follow-on. Independent performance change                                                       |
| CMK-37187                         | Out of scope (D9)                                                                               |
| CMK-28034 (no progress indicator) | **Not planned.** Probably a transient issue left open; keep in mind while building the new page |
| CMK-31896                         | Already fixed; informs the cold-cache split                                                     |

---

## 5. Risks

| #   | Risk                                                                                                                           | Mitigation                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | **The contract is a single point of failure.** Wrong in Phase 2 → Phases 3 and 4 diverge independently, exactly as the PoC did | Phase 0 matrix as the review reference; generated TS types so drift breaks the build; D5's internal-first option keeps early mistakes cheap               |
| R2  | **Public API permanence.** A batch-apply endpoint shipped in 3.0.0 cannot be quietly reshaped                                  | Largely resolved by D5: build on internal endpoints, promote to public once the UI has actually validated them                                            |
| R3  | **UX decided without PM/UX**, on a genuinely new interaction model                                                             | D13: interaction spec reviewed by PM/UX before the model is locked in code; validate on a large host with real admins before cutover                      |
| R4  | **Column board degrades at scale** worse than a table                                                                          | D4 plus the Phase 4 large-host fixture, exercised before the model is locked                                                                              |
| R5  | **Remote-site behaviour is the historical blind spot** — where the PoC broke and where the tests weren't                       | Phase 0 remote coverage via `test-system-multisite`; remote parity required at every phase exit, not at the end                                           |
| R6  | **Deletion never happens.** Phase 5 slips and both implementations live on — the very complexity this epic exists to remove    | Deletion commit written up front; toggle window bounded to one release cycle; D10 means the legacy code was never improved, so keeping it is unattractive |
| R7  | **Not a roadmap priority** — the plan stalls mid-way and leaves things half-migrated                                           | Every phase is independently shippable and leaves the tree defensible. Phase 1 alone is a net win even if nothing follows                                 |

---

## 6. Open questions

1. Exact shape of the concurrency hash (D11): what goes into it, and is it stable across
   equivalent previews?
2. Whether to start on internal endpoints and promote, or go public immediately (D5) — an
   implementation-phase call.
3. How wide the flag-gated coexistence window should be, and whether the toggle is per-site or
   per-user during development.

### Recorded intent, out of scope

- **`bulk_discovery` should eventually move onto the same primitives.** Not in this epic, but
  the intended direction.
- **Autodiscovery may benefit similarly.** Worth evaluating once the primitives are settled.
- **CMK-37187** (CLI convergence) remains the natural third consumer if the transition layer
  ever moves out of `cmk/gui`.
