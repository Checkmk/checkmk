# Service Discovery — Target Domain Model

**Status:** proposal, for review. **Normative / desired state**, not the status quo.

Companion to `SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md`, which is _descriptive_ (§1–§6:
what the code does today; §7 the test plan; §10 the ticket drafts) with two
prescriptive sections (§11: which operations are meaningful per state, and §11.2a its
four validation rules; §6.3: what follows for the rewrite from the host/job
mechanics). This document is the level above §11: the entities, their
boundaries, and which of today's types dissolve into which. **§6.3a below maps the two
documents onto each other** — same specification, different rule counts, for a
reason that matters.

Scope notes:

- Everything already identified as obsolete is ignored here: `legacy`,
  `legacy_ignored`, the `clustered_ignored` regression, `DiscoveryOptions.show_*`
  (pure view state), the AJAX transport.
- The immediately reusable outcome is **§6**: the eligibility gate and the 5×3
  transition table. Cells marked ✗ there are _specification_: reject them at the
  edge. They need no **conformance** tests — but until the rejections are actually
  implemented, the behaviour matrix's Tier 1b quarantines each one (a strict-xfail
  test asserting the intended outcome, paired with a characterization test asserting
  today's), so nothing wrong is asserted as correct and the scaffolding deletes
  itself when the ticket lands.
- No code changes are proposed here. This is the shape to refactor _towards_.

---

## 1. The five conflations to undo

Every naming smell in the current code traces back to one of these. They are
listed in the order in which fixing them unlocks the next.

| #   | What is conflated                                                                                                     | Where it shows                                                                                                                                                          |
| --- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Observation** (what the data source yields) with **configuration** (what we decided to monitor) with **their join** | `CheckPreviewEntry.check_source: str` is the join, collapsed to one of 15 strings                                                                                       |
| 2   | **A join-state** with **a command**                                                                                   | `DiscoveryState` is both `check_source` (observed) and `table_target` (requested). `removed` exists only as a command; `new`/`vanished` only make sense as observations |
| 3   | **What to do** with **which services to do it to**                                                                    | `FIX_ALL`, `UPDATE_SERVICES`, `UPDATE_SERVICE_LABELS`, `SINGLE_UPDATE` differ in _scope_, not in _operation_                                                            |
| 4   | **Domain operations** with **job control**                                                                            | `DiscoveryAction` holds `NONE`, `STOP`, `REFRESH`, `TABULA_RASA` next to `SINGLE_UPDATE` and `BULK_UPDATE`                                                              |
| 5   | **Read model** with **job status**                                                                                    | `DiscoveryResult.job_status: dict` + `is_active()` next to `check_table` and the label sets                                                                             |

Conflation 2 is the expensive one. It is _not_ wrong for one type to describe both
a current and a desired state — that is what a state type is for. It is wrong for
an **observation** to be usable as a **command**. "This service vanished" is a fact
about the world; it cannot be an instruction. Because `DiscoveryState` is used in
both positions, the declared pair space is 15 × 15 = 225, of which **206** are
reachable today via `update_service_phase` (13 reachable sources × 17 accepted
target phases, less the 15 diagonals) — against 10 that mean anything.

---

## 2. Bounded contexts

Five boxes. The only mutable, user-owned one is **B**.

```
   ┌─────────────────────────────┐        ┌──────────────────────────────────┐
   │ A. DISCOVERY OBSERVATION    │        │ B. MONITORING CONFIGURATION      │
   │                             │        │                                  │
   │ what the data source        │        │ what we have decided             │
   │ currently yields            │        │                                  │
   │  · found services + props   │        │  · autochecks entries (per site) │
   │  · found host labels        │        │  · service exclusions (central)  │
   │  · fetch diagnostics        │        │  · non-discovered definitions    │
   │                             │        │    (enforced / active / custom)  │
   │ read-only · cacheable       │        │                                  │
   │ has a timestamp             │        │ mutable · activation-pending     │
   └──────────────┬──────────────┘        └───────────────┬──────────────────┘
                  │                                       │
                  └───────────────┬───────────────────────┘
                                  │ join on ServiceKey
                                  v
                  ┌──────────────────────────────────┐
                  │ C. SERVICE TABLE                 │
                  │ derived · never persisted        │
                  │ rows carry the 4 facts of §3.4   │
                  │ + a table version                │
                  └───────────────┬──────────────────┘
                                  │ user picks rows + a target state
                                  v
                  ┌──────────────────────────────────┐        ┌───────────────────────┐
                  │ D. CHANGE PLAN                   │        │ E. SCAN               │
                  │ (selector, intent) pairs         │        │ produces a fresh A    │
                  │ validated against a C version    │        │  · start(FetchPolicy) │
                  │  → ChangeSet → applied to B      │        │  · stop / status      │
                  └──────────────────────────────────┘        └───────────────────────┘
```

**A** and **E** never touch **B**. **D** is the only writer of **B**. **C** is a
projection and must never be stored — today's `check_table_created` is the honest
admission that it _is_ a snapshot, and §9.4 turns that into a precondition rather
than a decoration.

---

## 3. Entities and value objects

### 3.1 Identity

```
ServiceKey = (CheckPluginName, Item)
```

Identity is the key, nothing else. `description` is **derived** from the key plus
configuration and can change without the service changing. Today the disabled-services
ruleset is keyed by description while autochecks are keyed by `ServiceKey`; that
mismatch is the reason `add_disabled_rule`/`remove_disabled_rule` are `set[str]`
while `autochecks_to_save` is keyed by `ServiceKey`. The model keeps the key as
identity and treats the description-keyed exclusion as a _rendering_ of an
exclusion on a key (§12, open decision 5).

### 3.2 Context A — observation

```
ObservedProperties   = { discovered_parameters, service_labels }
ObservedService      = { key, properties, found_on_nodes }
DiscoveryObservation = { host, services: {ServiceKey: ObservedService},
                         host_labels, source_results, observed_at }
```

`ObservedProperties` has exactly two facets, and they are adopted **independently**
— that is the whole reason `update_changed_service_labels` and
`update_changed_service_parameters` exist as separate flags in the automatic path,
and why `UPDATE_SERVICE_LABELS` and `UPDATE_DISCOVERY_PARAMETERS` exist in the
interactive one. Property adoption is a first-class part of intent (§3.5), not an
action variant.

### 3.3 Context B — configuration

```
ServiceOrigin    = Discovered | Enforced | Active | Custom
StoredService    = { key, properties }          # one autochecks entry
ServiceExclusion = { matches: ServiceKey }      # a "Disabled services" rule match
```

Only `Discovered` services are subject to discovery operations. `Enforced`,
`Active` and `Custom` appear in the table for completeness — so a user can see why
a service name is taken — and accept **no** operations at all. That single sentence
retires **5** of today's 15 `DiscoveryState` values as row states (`manual`,
`active`, `custom`, `ignored_active`, `ignored_custom`); the `effective_host` rule
below retires a further 4 (the `clustered_*` family), leaving 5 states plus
`removed`, which was never a state at all.

`DiscoveryState.is_discovered()` already computes exactly this predicate. It has
one production caller, `cmk/gui/wato/pages/services.py:725`, and it is used there
to pick a status message. Had it been the gate on operations instead, A1-F1 and the
`manual`/`active`/`custom` target-phase cells of the current matrix would not exist.

### 3.4 Context C — the join: four facts, two projections

A row is not a string. It carries four independent boolean facts plus two
qualifiers:

```
ServiceTableRow = {
    key, origin, effective_host,          # qualifiers
    found_now:      bool,                 # from A
    stored:         bool,                 # from B (autochecks)
    properties_match: bool,               # A vs B, per facet
    excluded:       bool,                 # from B (exclusion rules)
    observed_properties, stored_properties,
}
```

Two orthogonal projections are read off those facts:

```
DiscoveryStatus  = New | Unchanged | Changed | Vanished | Disabled     # A vs B
MonitoringState  = Monitored | Disabled | Unmonitored                  # B alone
```

`effective_host` replaces the four `clustered_*` names: a row whose effective host
is not the host being viewed is _someone else's_ row (§6.1). `origin` replaces
`manual` / `active` / `custom` / `ignored_active` / `ignored_custom`.

The enumeration of valid fact combinations is short:

| found | stored | props= | excluded | `DiscoveryStatus`                       | `MonitoringState` | today                  |
| :---: | :----: | :----: | :------: | --------------------------------------- | ----------------- | ---------------------- |
|   ✓   |   –    |   ·    |    –     | **New**                                 | Unmonitored       | `new`                  |
|   ✓   |   –    |   ·    |    ✓     | **Disabled**                            | Disabled          | `ignored`              |
|   ✓   |   ✓    |   ✓    |    –     | **Unchanged**                           | Monitored         | `unchanged`            |
|   ✓   |   ✓    |   ✗    |    –     | **Changed**                             | Monitored         | `changed`              |
|   ✗   |   ✓    |   ·    |    –     | **Vanished**                            | Monitored         | `vanished`             |
|   ·   |   ✓    |   ·    |    ✓     | _(invariant violation — §4)_            | —                 | `ignored` / `vanished` |
|   ✗   |   –    |   ·    |    ✓     | _(not a row — a rule matching nothing)_ | —                 | —                      |

**Five row states.** `removed` does not appear: it was never an observation.

### 3.5 Context D — intent, selector, plan

```
PropertyFacets = subset of { parameters, labels }

ServiceIntent  = Monitor(adopt: PropertyFacets)     # → MonitoringState.Monitored
               | Disable                            # → MonitoringState.Disabled
               | Unmonitor                          # → MonitoringState.Unmonitored

ServiceSelector = Explicit(set[ServiceKey])
                | ByStatus(set[DiscoveryStatus])

ChangePlan     = { host, against_table_version, rules: [(ServiceSelector, ServiceIntent)] }
```

`ServiceIntent` names a **target `MonitoringState`**, not a target observation.
Three values — and the number is derived, not chosen: the two facts discovery can
write (`stored`, `excluded`) have four combinations, one of which §4's invariant
forbids. `Unmonitor` therefore covers both of today's `new` and `removed` targets;
they write the same thing and differ only in an observation the user cannot change,
so which word the UI shows ("Remove service" when `found_now` is false, "Move to
undecided" otherwise) is a labelling decision, not a fourth intent. `adopt` only has meaning for a `Changed` row — for `New` and
`Disabled` there is no stored value to keep, and for `Unchanged` there is nothing
to adopt.

A plan yields a reviewable delta before anything is written:

```
ChangeSet = { autochecks:  {ServiceKey: properties},   # desired full content, per site
              exclusions_added:   set[ServiceKey],     # central config
              exclusions_removed: set[ServiceKey] }
```

`ChangeSet` being the desired _full_ autochecks content preserves today's
rebuild-from-scratch semantics — the property that makes every uncovered cell a
deletion — but makes it explicit and diffable instead of emergent. "Did anything
change" is then `ChangeSet != current`, replacing the host-global `apply_changes`
flag that is currently set by a `check_source != table_target` string comparison.

### 3.6 Context E — the scan

```
FetchPolicy = UseCached | Fetch
ScanRequest = { host, fetch: FetchPolicy }
ScanStatus  = { state, is_active, started_at, duration, log }
```

That is the whole job vocabulary. `ScanStatus` lives beside the table, never inside
it (undoing conflation 5). `STOP` is job lifecycle. `NONE` disappears — it is a UI
state, not a domain concept.

Crucially, a scan **produces an observation and nothing else**. It does not write
configuration. Today `TABULA_RASA` violates this: the job body calls
`local_discovery(...)` and mutates autochecks (`services.py:1396-1412`), which is
why it needs its own pending-changes entry added _before_ the job starts
(`services.py:1196`) and why the code carries the TODO about adding a change on the
wrong site.

**This context keeps a background job, and it is the only one that needs one.** A
`Fetch` scan contacts the host and outlives any request timeout, so it must be
asynchronous; and the job is already published as REST surface — the
`service_discovery_run` domain type, with `wait-for-completion`'s self-redirect and
the `303` that `refresh`/`tabula_rasa` answer with. Both facts are constraints, not
choices (behaviour matrix §6.0, mechanic 1).

What changes is that nothing _else_ depends on it. Today every read of the table is
routed through the job object, so a caller who starts no job still receives a
`ScanStatus` — of a job that never ran, or, worse, of the previous one (behaviour
matrix §6.2). In this model `FetchPolicy` is a field of `ScanRequest` rather than
something derived from an action name, which is the whole of what makes `REFRESH`
look special today; reading the table is a query on context C and involves no job at
all.

---

## 4. The invariant

> **A stored service is never excluded.**
> `stored ⇒ ¬excluded`

One line, checked in one place, and the whole A2-F2 class of defects becomes
unrepresentable:

- `Disable` means _remove the autochecks entry and add the exclusion_ — never
  "add the rule and keep the entry", which is what `_case_vanished` and
  `_case_monitored` do today.
- A vanished service that is excluded cannot be written back, because writing back
  would violate the invariant. This is werk 19801's contract expressed as a type
  constraint instead of as a code path.
- The current transient "stored ∧ excluded" state (the 19801 residue) is
  representable only as an **input** to be repaired, never as an output. Repair is
  a plan rule: `ByStatus({Disabled-with-residue}) → Unmonitor`.

---

## 5. Read vocabulary: 15 names → 5 states + 2 fields

| today's `DiscoveryState`               | becomes                                                         |
| -------------------------------------- | --------------------------------------------------------------- |
| `new`                                  | `DiscoveryStatus.New`                                           |
| `unchanged`                            | `DiscoveryStatus.Unchanged`                                     |
| `changed`                              | `DiscoveryStatus.Changed`                                       |
| `vanished`                             | `DiscoveryStatus.Vanished`                                      |
| `ignored`                              | `DiscoveryStatus.Disabled`                                      |
| `removed`                              | _gone_ — command only, and it collapses into `Unmonitor` (§6.2) |
| `manual`                               | `origin = Enforced`                                             |
| `active`, `ignored_active`             | `origin = Active` (+ `excluded`)                                |
| `custom`, `ignored_custom`             | `origin = Custom` (+ `excluded`)                                |
| `clustered_old` / `_new` / `_vanished` | `effective_host ≠ self`, + the row state                        |
| `clustered_ignored`                    | same; the value itself is a regression and is dropped           |
| `legacy`, `legacy_ignored`             | _gone_ (already dead)                                           |

The 15-name enum was a flattening of `DiscoveryStatus × origin × excluded ×
effective_host`. Flattening a product type into names is exactly why the value set
is both incomplete (no `clustered_changed`) and over-large (206 reachable pairs).

---

## 6. Which transitions are meaningful — the reusable outcome

### 6.1 Gate 0: eligibility, before any state is consulted

Two rejections that need no per-state reasoning:

| condition               | response                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `origin ≠ Discovered`   | **reject** — not discovery-managed. Enforced/active/custom services are changed by editing their definition.                                                                                                                                                                                                                                                                         |
| `effective_host ≠ host` | **reject, with a redirect** to the effective host. Not because the operation is dangerous, but because the node has nothing to decide: the cluster owns the service and the responsibility for discovering it. Nothing needs migrating if the clustering rule is later withdrawn — the entry never left the node's autochecks, so the service simply reappears as `Unchanged` there. |

Gate 0 is about the **row**, not the target: it retires 8 of the 13 reachable
source states (5 non-discovered origins + 3 reachable `clustered_*`), which is 8
whole rows of the behaviour matrix's §4 grid. The 9 _target_ phases that name those
same states are eliminated separately, by the rule that a target must be one of the
three writable states — see the reconciliation in §6.3a.

### 6.2 The table

For `origin = Discovered` and `effective_host = host`:

| `DiscoveryStatus`                       | → `Monitor`                              | → `Disable`                  | → `Unmonitor`                    |
| --------------------------------------- | ---------------------------------------- | ---------------------------- | -------------------------------- |
| **New** (found, ¬stored)                | ✓ write entry                            | ✓ add exclusion              | – no-op                          |
| **Disabled** (found, ¬stored, excluded) | ✓ drop exclusion + write entry           | – no-op                      | ✓ drop exclusion → becomes `New` |
| **Unchanged** (found, stored, props=)   | – no-op                                  | ✓ drop entry + add exclusion | ✓ drop entry → returns as `New`  |
| **Changed** (found, stored, props≠)     | ✓ rewrite entry, adopting `adopt` facets | ✓ drop entry + add exclusion | ✓ drop entry → returns as `New`  |
| **Vanished** (¬found, stored)           | ✗ **reject**                             | ✗ **reject**                 | ✓ drop entry → gone              |

✓ meaningful · – accepted as a no-op · ✗ rejected

**10 meaningful (state, intent) pairs.** Against 206 reachable today. The count
matches §11 of the behaviour matrix, reached from a different decomposition.

`Changed → Monitor` with `adopt = ∅` is the deliberate "keep monitoring, keep the
old properties" no-op. That is the only place the adoption set changes the outcome,
and it is what preserves the distinction recorded as intended in the behaviour
matrix (§9.1, A3-F1/A3-F2): `FIX_ALL`
adopts nothing for changed services, a full refresh adopts both facets.

### 6.3 Rejection list — a validation spec

Reject with 400 (a malformed request, not a permission problem):

1. any intent on `origin ≠ Discovered`
2. any intent on a row whose `effective_host` is not the host addressed
3. `Vanished → Monitor` — the service is not there. Writing it back produces a
   service that goes stale immediately and re-vanishes on the next scan. If the
   user wants it monitored anyway, that is an _enforced_ service, a different
   ruleset. Together with item 4 this is one rule, not two: **`Vanished` admits
   `Unmonitor` and nothing else.**
4. `Vanished → Disable` — three independent reasons, the first decisive: **the
   target state is unreachable for this source.** A vanished service is stored but
   not found, and the classifier never assigns it `Disabled` —
   `_node_service_source` skips the exclusion filter when the transition is
   `vanished` (`_autodiscovery.py:764`), `_make_cluster_table` likewise, and two
   tests pin the rule (`test__autodiscovery.py:127`, `:214`). No implementation of
   the pair can be correct, because the next observation contradicts whatever it
   wrote. Beyond that, it would violate the §4 invariant, and excluding a service
   that no longer exists is a plain ruleset edit rather than a discovery operation.
5. `Monitor(adopt ≠ ∅)` on a row that is not `Changed` — there is nothing to adopt,
   so the request is malformed rather than merely redundant. (This is _not_ the
   cause of A1-F2: that finding's cause is the unapplied `update_source` filter,
   not the adoption set. Making the adoption set explicit is a separate guard, and
   it is what stops a caller from believing a facet was adopted when the row had no
   divergence.)
6. a plan whose `against_table_version` no longer matches (§9.4) — 409.

No-ops (the `–` cells) are **accepted** and reported as "no change", not rejected.
That keeps the write path idempotent, which the REST `PUT` semantics require.

### 6.3a Reconciliation with the behaviour matrix

The behaviour matrix states the same specification as **four** rules (§11.2a) where
this document states **five** classes. The counts differ for one reason worth
understanding, because it is the point of the model:

| behaviour matrix §11.2a                               | here                                                      | note                                                                                                                                                                                                                                                                                                                                                      |
| ----------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. the target is not one of the three commands        | _(absent)_                                                | **Enforced by the type, not by a check.** The matrix needs this rule because `table_target` is a `str` holding any of 17 phase names. Here `ServiceIntent` has three values, so a non-command cannot be constructed. This is the single largest reduction — it removes 169 of the 221 pairs — and in the target model it is not a validation rule at all. |
| 2. `origin ≠ discovered`                              | §6.3 item 1 (Gate 0)                                      | same rule                                                                                                                                                                                                                                                                                                                                                 |
| 3. `effective_host_is_self = no`                      | §6.3 item 2 (Gate 0)                                      | same rule                                                                                                                                                                                                                                                                                                                                                 |
| 4. source is `vanished` and the command is not `drop` | §6.3 items 3 + 4                                          | one rule, stated as two rejections because the matrix records two distinct current behaviours                                                                                                                                                                                                                                                             |
| _(absent)_                                            | §6.3 item 5 — `Monitor(adopt ≠ ∅)` on a non-`Changed` row | no counterpart: the matrix has no explicit adoption set to validate                                                                                                                                                                                                                                                                                       |
| _(absent)_                                            | §6.3 item 6 — stale `against_table_version` (409)         | no counterpart: the matrix has no table-version precondition                                                                                                                                                                                                                                                                                              |

**Vocabulary mapping.** The two documents name the third command differently; they
are the same operation:

| behaviour matrix §11.1           | here             | today's target strings |
| -------------------------------- | ---------------- | ---------------------- |
| `monitor` (with an adoption set) | `Monitor(adopt)` | `unchanged`            |
| `disable`                        | `Disable`        | `ignored`              |
| `drop`                           | `Unmonitor`      | `new` _and_ `removed`  |

State names likewise: the matrix keeps today's strings (`new`, `unchanged`,
`changed`, `ignored`, `vanished`) because it is describing existing code; this
document uses `DiscoveryStatus.New / Unchanged / Changed / Disabled / Vanished`,
with `Disabled` for the matrix's `ignored`. The five states, the ten meaningful
pairs, the three no-ops and the two rejections are identical in both.

### 6.4 Consequence for the test matrix

- **10** cells need behavioural tests, plus 3 no-op cells asserting idempotency.
- **5** rejection classes need one negative test each — not one per cell (items 3
  and 4 of §6.3 are one rule: `Vanished` admits `Unmonitor` and nothing else).
- Everything Gate 0 rejects needs **no** cell test at all — it retires 8 of the 13
  reachable source states, so 8 whole rows collapse to two assertions.
- The 13 non-command target phases need no tests either; in the target model they
  are unrepresentable rather than rejected (§6.3a).
- The `(source, target)` grid disappears as a concept. What remains is
  `(five row states) × (three intents)` = 15 cells: 10 meaningful, 3 no-op, 2 rejections.
  Compare `test_do_discovery.py`'s 225-cell nominal grid (of which it covers 120
  through `combinations_with_replacement`).

That is the concrete payoff: the guardrail suite for CMK-34150 still has to pin
today's behaviour — see the behaviour matrix's Tier 1a (conformance) and Tier 1b
(quarantine) split — but the _post-refactoring_ suite is 15 cells and 5 negative
tests instead of a 15 × 15 table half of whose entries are unreachable or dead
expected-data.

---

## 7. Today's `DiscoveryAction` expressed in the model

`DiscoveryAction` dissolves entirely. It is a mixture of three different things:

| today                              | becomes                                                                                                                     | box      |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------- |
| `NONE`                             | _nothing_ — UI state                                                                                                        | —        |
| `STOP`                             | `Scan.stop()`                                                                                                               | E        |
| `REFRESH`                          | `Scan.start(Fetch)`                                                                                                         | E        |
| `TABULA_RASA`                      | `Scan.start(Fetch)` **▸** `ChangePlan[ ByStatus{New, Unchanged, Changed} → Monitor(both), ByStatus{Vanished} → Unmonitor ]` | E then D |
| `FIX_ALL`                          | `ChangePlan[ ByStatus{New} → Monitor(∅), ByStatus{Vanished} → Unmonitor ]`                                                  | D        |
| `UPDATE_SERVICES`                  | `ChangePlan[ Explicit(sel) → <intent from the button> ]`                                                                    | D        |
| `BULK_UPDATE`                      | `ChangePlan[ ByStatus{s} → <intent> ]`                                                                                      | D        |
| `SINGLE_UPDATE`                    | `ChangePlan[ Explicit({key}) → <intent> ]`                                                                                  | D        |
| `SINGLE_UPDATE_SERVICE_PROPERTIES` | `ChangePlan[ Explicit({key}) → Monitor(adopt=both) ]`                                                                       | D        |
| `UPDATE_SERVICE_LABELS`            | `ChangePlan[ ByStatus{Changed} → Monitor(adopt={labels}) ]`                                                                 | D        |
| `UPDATE_DISCOVERY_PARAMETERS`      | `ChangePlan[ ByStatus{Changed} → Monitor(adopt={parameters}) ]`                                                             | D        |
| `UPDATE_HOST_LABELS`               | host-label aggregate, `accept` (§8.2)                                                                                       | separate |

The table expresses each action's **documented intent**, not its current
implementation. Several diverge — `FIX_ALL` additionally retargets 11 of 13 sources
to `monitored` (behaviour matrix A1-F1), and the two `UPDATE_*` actions do not apply
the `Changed` selector they transmit (A1-F2). Those divergences are exactly the
behaviour matrix's findings; the plans above are what the actions should compile to.

Three things fall out:

- **`TABULA_RASA` is superfluous as a concept.** It is a scan followed by a plan,
  both of which the model already has. Whether it survives as a _UI shortcut label_
  is a separate question, worth answering after the epic rather than before.
- **The six `UPDATE_*`/`*_UPDATE` actions differ only in their selector.** They are
  not different operations. `UPDATE_SERVICE_LABELS` currently reaches rows outside
  `Changed` because the selector is implicit and unchecked (A1-F2); making the
  selector an explicit value makes that class of bug unrepresentable.
- **There is no `All` selector** — §3.5 deliberately offers only `ByStatus` and
  `Explicit`. A `(selector, intent)` rule
  is only well-formed if _every_ row the selector matches admits that intent. No
  intent satisfies that for all five states — `Vanished` admits only `Unmonitor`, and
  `New` does not meaningfully admit it — so `All` can only be paired with an intent
  by silently skipping the rows that reject, which is the failure mode §6.3 exists to
  remove. Every real plan is `ByStatus` or `Explicit`. Note that
  `DiscoverySettings` reached the same conclusion by construction: it has five
  per-status flags and no "all" flag (§8.1).

---

## 8. Convergence with the automatic-discovery model

### 8.1 `DiscoverySettings` is already this model

`packages/cmk-check-engine/cmk/checkengine/discovery/types.py:32` —

```python
@dataclass(frozen=True)
class DiscoverySettings:
    update_host_labels: bool
    add_new_services: bool
    remove_vanished_services: bool
    update_changed_service_labels: bool
    update_changed_service_parameters: bool
```

Read it as a `ChangePlan`:

| flag                                | plan rule                                   |
| ----------------------------------- | ------------------------------------------- |
| `add_new_services`                  | `ByStatus{New} → Monitor(∅)`                |
| `remove_vanished_services`          | `ByStatus{Vanished} → Unmonitor`            |
| `update_changed_service_labels`     | `ByStatus{Changed} → Monitor({labels})`     |
| `update_changed_service_parameters` | `ByStatus{Changed} → Monitor({parameters})` |
| `update_host_labels`                | host-label aggregate: `accept`              |

It is selector × intent, restricted to `ByStatus` selectors, with the property
facets already separated. **The automatic path already got the domain model right.**
The interactive path re-invented the same domain as 15 target strings and 12 actions.

The convergence is not hypothetical: `TABULA_RASA`'s job body _already_ builds a
`DiscoverySettings` with all five flags true and routes through the engine path
(`services.py:1396-1412`). One of the twelve interactive actions is already
expressed in the target model.

So the target architecture is: **one plan type, two front ends.** The interactive
path adds the `Explicit` selector (and, eventually, the exclusion-rule writes,
which the automatic path does not do at all). Nothing else differs.

### 8.2 Labels are separate aggregates

- **Host labels** belong to the host, not to any service. They have their own
  three-way status (`new` / `vanished` / `changed`) and exactly one operation:
  `accept`. They do not belong in a service-transition table, and
  `UPDATE_HOST_LABELS` does not belong in the same enum as service operations.
- **Service labels** are a _facet of a service's properties_ (§3.2), reached through
  `Monitor(adopt={labels})`. They are not a separate aggregate and not a separate
  action.

---

## 9. Boundaries: where things live and run

### 9.1 Two persistence layers, one operation

| written thing      | lives                        | written via               |
| ------------------ | ---------------------------- | ------------------------- |
| autochecks entries | the **host's site**          | automation to that site   |
| service exclusions | **central** config (ruleset) | local config write + sync |
| host labels        | the host's site              | automation                |

`Disable` and `Unmonitor`-from-`Disabled` therefore touch **both** layers with
different transactionality. That asymmetry is real and must be named in the model
rather than discovered at runtime — it is what `need_sync` is for. The model's
requirement: a `ChangeSet` is applied in an order that never leaves the §4
invariant violated if the second write fails, and a partial application is
reported, not swallowed.

(For the record: `need_sync` is currently computed _before_ `add_disabled_rule` is
narrowed by subtraction, so it can be `True` for an empty rule delta. Harmless
today, but it is the kind of thing an explicit `ChangeSet` makes impossible.)

### 9.2 Site resolution happens once, at the edge

The automation target is a property of the **host**, resolved at the entry point
and passed down. No function below the edge may construct one. Today
`local_discovery` / `local_discovery_preview` hard-code `LocalAutomationConfig()`,
and quick setup passes a hard-coded `LocalAutomationConfig()` into
`perform_fix_all` (`cmk/gui/quick_setup/v0_unstable/predefined/_complete.py:540`)
while using the correct config for its reads — writing a remote host's autochecks
to the central site. A model where the transport is a parameter of the boundary,
not a default, removes that failure mode structurally.

### 9.3 The scan always runs on the host's site

Non-negotiable and already true. Worth stating because it is the reason the job is
not part of the plan: the plan is computed centrally, the observation is produced
remotely.

### 9.4 Optimistic concurrency

`ChangePlan.against_table_version` is a **precondition**, not metadata. A plan
computed against a table version that no longer matches must be rejected (409),
because the row the user clicked is not necessarily the row that would be changed.
Today `check_table_created` exists and is never used this way.

The concrete case, in case the requirement reads as merely prudential: while a
discovery job is running, `update_service_phase` is handed an empty table and
answers `204` having discarded the change (behaviour matrix B-F3, §10.18). Today's
only concurrency control is a probe for _is a job active_, implemented in one of the
two write entry points. A table-version precondition subsumes it — an active job
yields version `0` — and additionally covers the case no job probe can see, a client
or page acting on a table it read minutes ago.

### 9.5 Validation is single-sourced; affordances are derived from it

Gate 0 and the §6.2 table are evaluated in context D, once, for every caller. This is
worth stating as a boundary rule because today the same knowledge exists in two
places with different content:

| rule                                            | front end                                                            | backend                                                                                            |
| ----------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| clustered and non-discovered rows admit nothing | GUI renders no affordance — correct                                  | accepts and acts (behaviour matrix A2-F7)                                                          |
| the target must be one of the three commands    | GUI is type-constrained to four `UpdateType` values — nearly correct | takes `update_target: str \| None`; REST maps 17 phase names to raw strings (matrix §10.3, §10.12) |
| a `Vanished` row admits only `Unmonitor`        | GUI **offers** `ignored` — wrong (matrix A2-F6)                      | falls through and keeps the service                                                                |

Two consequences for the refactor. First, the front end's version of these rules is
not a specification that can be relocated: for the clustered case it consists of
absent buttons, and for the vanished case it is wrong. It has to be authored in the
domain layer, not copied inward. Second, the flow inverts: rather than each front end
deciding what to offer and the backend accepting what arrives, the `ServiceTableRow`
carries the set of intents that row admits, computed by the same gate that rejects
violations, and the front end renders that set. A rejection is then unreachable
through the UI by construction, and reachable through the API only by ignoring the
read model — which is exactly when a 400 is the right answer.

What remains front-end-only is presentation: the two labels for the single
`Unmonitor` command (§5; behaviour matrix §11.3), grouping and collapsing, and where a rejection's redirect
points.

---

## 10. Permissions

Gate on **intent**, evaluated for the whole plan **before** any write:

| intent                          | permission                            |
| ------------------------------- | ------------------------------------- |
| `Monitor`                       | `wato.service_discovery_to_monitored` |
| `Disable`                       | `wato.service_discovery_to_ignored`   |
| `Unmonitor` on a `Vanished` row | `wato.service_discovery_to_removed`   |
| `Unmonitor` on any other row    | `wato.service_discovery_to_undecided` |

This is the one place where the gate keys off `(state, intent)` rather than intent
alone, and it is deliberate — see §12.1.

Three properties the current code lacks:

1. **Checked once, per plan, before writing.** Today `_verify_permissions` runs
   inside the per-service loop, so a partially-permitted bulk action can fail
   mid-rebuild.
2. **Total.** Three `match` statements over bare `str` currently have no default
   arm, so an unknown target silently means "no permission required".
3. **One authority.** The GUI and the REST endpoints derive their gates from the
   same `intent → permission` function; there is no second list. Today
   `update_service_phase.py` demands all four discovery permissions unconditionally
   and separately requires only host `setup_read`.

---

## 11. What this deletes

| removed                                                                                                                                 | replaced by                                                                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DiscoveryState` (15 values, plain class, `str`-valued)                                                                                 | `DiscoveryStatus` (5) + `origin` + `excluded` + `effective_host`                                                                                                                                                                                                            |
| `table_target: str`                                                                                                                     | `ServiceIntent` (3)                                                                                                                                                                                                                                                         |
| `DiscoveryAction` (12 values)                                                                                                           | `ScanRequest` + `ChangePlan` (§7)                                                                                                                                                                                                                                           |
| `UpdateType` (4 values)                                                                                                                 | `ServiceIntent` (3) — `UpdateType` is the right idea already: a target-only type. It has one value too many, because `UNDECIDED` and `REMOVED` are two labels for one command, and it is not the type the transition machinery actually uses (`update_target: str \| None`) |
| `update_source` / `update_target` / `selected_services` as three loose parameters                                                       | `(ServiceSelector, ServiceIntent)`                                                                                                                                                                                                                                          |
| `apply_changes` (host-global, string-comparison-derived)                                                                                | `ChangeSet != current`                                                                                                                                                                                                                                                      |
| `Transition` literal in `_autodiscovery.py` (never includes `removed`)                                                                  | — no transition type; the plan is the input                                                                                                                                                                                                                                 |
| `DiscoveryResult.job_status`, `.is_active()`                                                                                            | `ScanStatus`, beside the table                                                                                                                                                                                                                                              |
| `check_table.mk`, the job's read-once-then-`unlink` preview store, and the `_cleaned_up_status` laundering that a job-less caller needs | nothing — a read of the table is a query; the fetcher cache is the only cache                                                                                                                                                                                               |
| the `job_snapshot(...).is_active` probe as concurrency control                                                                          | `ChangePlan.against_table_version` (§9.4)                                                                                                                                                                                                                                   |
| 17 REST `target_phase` values                                                                                                           | 3 intents + Gate 0                                                                                                                                                                                                                                                          |
| `DiscoveryOptions.show_*`                                                                                                               | view state, out of the domain                                                                                                                                                                                                                                               |

---

## 12. Open decisions

These change the model and are yours to make.

**12.1 `Unmonitor` and the two existing permissions.** `to_undecided` ("forget")
and `to_removed` ("delete") both map to `Unmonitor`, because whether the service
comes back as `New` is decided by the _observation_, not by the command — the two
produce byte-identical transitions for `Unchanged` and `Changed` today. That looked
like pure redundancy, and the obvious move was to collapse them.

**It is not redundancy, once `removed` is legal only on a `Vanished` row.** Under
that rule the two permissions partition the `Unmonitor` cells exactly: `to_removed`
gates `Vanished → Unmonitor` and nothing else; `to_undecided` gates the other three.
No overlap, no ambiguity, no deprecation. The cost is that `Unmonitor`'s permission
depends on the row rather than on the intent alone — three intents, four permissions
— which is less tidy than a 3-for-3 mapping but is honest about the fact that
deleting a service that is gone and forgetting one that is still there are different
privileges.

**Recommendation:** keep both, and make the mapping `(state, intent) → permission`
rather than `intent → permission`. This reverses the earlier recommendation in this
document and is the cheaper option: it needs no API version break.

**12.2 `Monitor` on a `Changed` row: default adoption.** §3.5 models
`adopt` as explicit, with no default. The alternative is `Monitor` always adopting
both facets, which makes `FIX_ALL` and a full refresh identical and removes the
`adopt` parameter entirely — simpler, but it discards the `FIX_ALL`-vs-refresh
distinction recorded as intended in the behaviour matrix (§9.1). **Recommendation:**
keep `adopt` explicit; require it at the API boundary so no caller gets it by
accident.

**12.3 `New → Disable`.** §6.2 marks it meaningful: "I have seen this service
and never want it monitored" is a real intent, and it correctly writes only the
exclusion. Confirm — it is the one cell where the exclusion is created for a
service that was never in autochecks.

**12.4 Clustered rows: reject or redirect.** §6.1 says reject _with a redirect_.
The alternative is to accept the operation and transparently apply it to the
effective host, which is friendlier and considerably more surprising.
**Recommendation:** reject with a redirect; the page that owns the autochecks
should be the page that changes them.

**12.5 Exclusion identity.** The disabled-services ruleset matches on service
_description_; autochecks are keyed by `ServiceKey`. The model treats an exclusion
as being on a key and the description as a rendering, which is a lie the ruleset
does not support — a description-matching rule can catch services the plan never
selected. Either the model admits `ServiceExclusion` is a _predicate_ rather than a
set of keys (honest, and means `Disable`'s effect is not fully knowable at plan
time), or the ruleset grows key-based matching. This is the one place where I do
not think the clean model is reachable without a config-format decision.

**12.6 Naming.** `Disabled` (matches the GUI's "Disabled services" and the werks)
vs `Excluded` (avoids collision with `MonitoringState.Disabled` being both a status
and an intent target). This document uses `Disabled` for the user-facing status and
`exclusion` for the config object, which is a compromise; a single word would be
better if one exists that reads correctly in both positions.

**12.7 How strict the table-version precondition is at the API boundary.** §9.4 makes
`against_table_version` required. For the GUI that is free — it already holds the
value. For REST it is a new mandatory request field, so making it mandatory is an
incompatible change and belongs in a version bump; making it optional but enforced
when present keeps v1 clients working and leaves them with today's failure mode
(behaviour matrix B-F3). A third option is to derive it server-side from the host's
autochecks mtime, which needs no client cooperation but rejects fewer real conflicts.
**Recommendation:** optional-when-present in v1, required in the next version. This
is an API-ownership call, not a modelling one.
