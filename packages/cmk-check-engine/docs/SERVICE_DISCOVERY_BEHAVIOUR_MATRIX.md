# Service Discovery — Behaviour Matrix (CMK-34150)

**Purpose:** written statement of _today's_ behaviour of `cmk/gui/watolib/services.py`, so that
"no behaviour change" during CMK-32255 / CMK-37497 is verifiable rather than assumed.

**Status:** derived from the code at `68bd2fd4651` (branch `cmk-34150`). Not yet pinned by tests —
the test list in §7 is the proposal. §1–§6 are descriptive (current behaviour, verified) with two
exceptions: §6.3 and §11 are **prescriptive** — §6.3 states what follows for the rewrite from §6's
mechanics, §11 states the intended per-state semantics. Both are for review.

**Scope:** `cmk/gui/watolib/services.py` + the automation boundary in
`cmk/gui/watolib/check_mk_automations.py`. The AJAX transport (`ModeAjaxServiceDiscovery`,
`DiscoveryPageRenderer`) is **deliberately excluded** — it is scheduled for deletion.

> This document describes behaviour, including behaviour that looks wrong. Two markers distinguish how
> wrong:
>
> **⚠️** means characterized but **not** endorsed — it becomes a deliberate decision in the Phase 2
> contract or gets its own ticket.
>
> **✗** means the cell is an _invalid transition_ under §11's normative
> semantics: it must be rejected rather than corrected, and §7's Tier 1b quarantines it (strict-xfail on
> the intended outcome, paired with a characterization test) instead of pinning it as expected. Nothing
> here should be "fixed" as part of CMK-34150.
>
> The companion `SERVICE_DISCOVERY_DOMAIN_MODEL.md` holds the target model; its §6.3a reconciles that
> document's rejection classes with §11.2a's four rules and maps the vocabularies.

---

## 1. The one rule that explains most surprising cells

`Discovery.compute_discovery_transition` **rebuilds the autochecks table from scratch** on every
save. `new_autochecks` contains _only_ what the `_case_*` handler for a given `check_source` chose
to write. Consequently:

> **Any service whose `(source, target)` cell does not explicitly write it is deleted from
> autochecks when the save happens.**

The second-order rule:

> A save happens if and only if **at least one** entry in the table has
> `check_source != table_target`. That flag (`apply_changes`) is global to the host, not per
> service. If no entry differs, `compute_discovery_transition` returns `None` and nothing at all is
> written — no autochecks, no rules, no pending change.

---

## 2. Axes

### 2.1 `DiscoveryState` as a _source_ (rows) — 15 declared, 13 reachable

`check_source` is produced by `get_check_preview`
(`packages/cmk-check-engine/.../discovery/_entrypoints/preview.py`) from the `Transition` literal,
plus `"manual"` for enforced services, plus `active`/`ignored_active`
(`_active_check_preview_rows`) and `custom`/`ignored_custom`
(`ConfigCache.custom_check_preview_rows`).

| #   | `DiscoveryState`     | wire value           | reachable as source? | produced by                                        |
| --- | -------------------- | -------------------- | -------------------- | -------------------------------------------------- |
| 1   | `UNDECIDED`          | `new`                | yes                  | `Transition`                                       |
| 2   | `MONITORED`          | `unchanged`          | yes                  | `Transition`                                       |
| 3   | `CHANGED`            | `changed`            | yes                  | `Transition`                                       |
| 4   | `VANISHED`           | `vanished`           | yes                  | `Transition`                                       |
| 5   | `IGNORED`            | `ignored`            | yes                  | `Transition` (host or cluster disabled-rule match) |
| 6   | `REMOVED`            | `removed`            | **no — target only** | not in `Transition`                                |
| 7   | `MANUAL`             | `manual`             | yes                  | `enforced_services` in `preview.py`                |
| 8   | `ACTIVE`             | `active`             | yes                  | `_active_check_preview_rows`                       |
| 9   | `CUSTOM`             | `custom`             | yes                  | `custom_check_preview_rows`                        |
| 10  | `ACTIVE_IGNORED`     | `ignored_active`     | yes                  | ditto, description in `IgnoredActiveServices`      |
| 11  | `CUSTOM_IGNORED`     | `ignored_custom`     | yes                  | ditto                                              |
| 12  | `CLUSTERED_OLD`      | `clustered_old`      | yes                  | `_node_service_source`, node table                 |
| 13  | `CLUSTERED_NEW`      | `clustered_new`      | yes                  | ditto                                              |
| 14  | `CLUSTERED_VANISHED` | `clustered_vanished` | yes                  | ditto                                              |
| 15  | `CLUSTERED_IGNORED`  | `clustered_ignored`  | **no — unreachable** | see below                                          |

**Not reachable as a source — but read the two cases differently:**

- **`removed` is alive and required — just target-only.** `Transition` (`_autodiscovery.py:106`) is
  `changed|unchanged|new|vanished|ignored|clustered_old|clustered_new|clustered_vanished|clustered_ignored`;
  no producer emits `removed`, so no service is ever _in_ the `removed` state. It is a **verb, not a
  noun**: as a `table_target` it means "drop this from autochecks", and it is used throughout —
  `UpdateType.REMOVED`, the `wato.service_discovery_to_removed` permission, the GUI's
  `_icon_button_removed`, the `VANISHED → REMOVED` bulk entry, and the REST `remove` mode and
  `target_phase: "removed"`. **Nothing to delete here.** The only actionable point is that
  `DiscoveryState` mixes a verb in with 14 nouns, which is evidence for splitting source from target
  in Phase 3 (see A1-F1) — not a defect in itself.
- **`clustered_ignored` is dead by accident — a datable 2021 regression. DO NOT DELETE IT; restore
  its producer.** ✅ _verified against the commits_

  Before February 2021 the node classifier **mutated** `check_source` and _then_ prefixed it:

  ```python
  if config.service_ignored(clustername, ...):
      check_source = "ignored"
  services[service.id()] = ("clustered_" + check_source, service, found_on_nodes)   # -> clustered_ignored
  ```

  That ordering was deliberate — commit `dd74ccb1bab` (2019-03-21), **werk 7128** _"Display vanished
  and disabled clustered services on discovery page of the nodes"_, which also added the GUI table
  group. Commit **`692c918bf86`** (2021-02-05, _"discovery: towards `QualifiedDiscovery` 1"_) extracted
  `_node_service_source` and turned that branch into an **early return**, bypassing the prefix:

  ```python
  if config.service_ignored(cluster_name, ...):
      return "ignored"          # <- prefix never applied
  return "clustered_" + check_source
  ```

  The commit message shows no behavioural intent. The `# TODO: this does not make much sense...` now
  sitting above that line was added later (`52fc5d43be2`, 2024) — it is the trace of the regression,
  not a design note. Everything downstream still expects the value: the GUI group _"Disabled clustered
  services - located on cluster host"_ with `show_bulk_actions=False`
  (`wato/pages/services.py:2168-2178`, translated in 8 locales), the `Transition` literal, the
  `DiscoveryReport.clustered_ignored` counter, `_case_clustered`'s match arm — and werk **19806.md:22**
  still asserts the transition's behaviour _"is unchanged"_, describing something that cannot occur.

  It is a **user-visible misclassification**, not just dead code: a disabled clustered service is
  filed on the node under the generic "Disabled services" group **with bulk actions enabled**, and is
  shown on the cluster as `vanished` or (after werks 19800/19806) not at all. Ticket in §10.13.

**A third instance of the same failure mode — already fixed, and worth citing as precedent.**
✅ _verified against the commits and the werk_

`ACTIVE_IGNORED` and `CUSTOM_IGNORED` were **dead values for four years**, by the same mechanism as
`clustered_ignored` and in the same 2021 refactoring wave. The GUI constants read `"active_ignored"` /
`"custom_ignored"`; the producer emitted `"ignored_active"` / `"ignored_custom"`. They originally agreed —
`_preview_check_source` returned `"%s_ignored" % check_source` (present at
`aecd8007105:cmk/base/discovery.py:1371-1372`, June 2020, and earlier) — until **`35b96ecaeb9`**
(2021-11-11, _"dissolve `_preview_check_source`"_) inlined the function and wrote the two halves in the
other order. The GUI side was corrected only by werk **18136** / SUP-25574 (`72629e907d3`, 2025-10-09,
2.5.0b1), whose entire diff is those two string literals.

**Consequence while broken: the rows were dropped, not misfiled.** `_show_check_table` renders groups by
looking up `by_group.get(entry.table_group, [])` over `_ordered_table_groups()`
(`cmk/gui/wato/pages/services.py:1159-1160`), so a `check_source` with no matching `TableGroupEntry` is
silently discarded. Across 2.1–2.4, disabling an active or custom check made its row disappear from
service discovery entirely — werk 18136's own wording: _"causing these disabled services to be missing
from the page"_.

**Why this belongs in the document rather than only in a changelog.** It is the _third_ value in this
family whose producer and consumer disagreed for years with nothing failing — `clustered_ignored`
(2021 → open), `ignored_active` / `ignored_custom` (2021 → 2025), and the `legacy` pair below. Three
instances is a pattern, and it is the strongest available argument for §10.12: the agreement is a bare
string comparison across a component boundary, invisible to mypy because both sides are `str`, and
untested because no test constructs a disabled active or custom check. It is also the reason §10.15 went
unreported for six years. Recorded as C-F2 in §8; no ticket, it is fixed.

**Two phantom values exist outside `DiscoveryState` entirely:** `SERVICE_DISCOVERY_PHASES`
(`api_endpoints/service_discovery/_utils.py:95-96`) maps `"legacy"` and `"legacy_ignored"` to
themselves. They are not `DiscoveryState` members and are never produced — but they _are_ accepted
as `target_phase` by the `update_service_phase` REST endpoint (§5.2). ⚠️

**Origin and removal history, fully established.** ✅ _verified_

They were the display phases for the `legacy_checks` variable in `main.mk` — the deleted GUI help text
read _"These services have been configured by the deprecated variable `legacy_checks` in `main.mk`"_.
That feature was removed by **werk 7342** (_"Removed legacy_checks configuration variable"_, 1.6.0b1,
2019-04-24), which is why `custom` / `ignored_custom` are the surviving siblings. The phases were
dropped from `DiscoveryState` by **`e7d3d548913`** (2023-02-19, _"kick out 1.6 support"_, no werk),
whose deleted lines carried their own expiry note:

```python
-    # TODO: Were removed in 1.6 from base. Keeping this for
-    # compatibility with older remote sites. Remove with 1.7.
-    LEGACY = "legacy"
-    LEGACY_IGNORED = "legacy_ignored"
```

The REST mapping was never cleaned up and the recent framework migration (`990c069f2bd`, 2026-05-28)
re-published them as members of the new Pydantic `Literal`. They cannot be produced by any preview, and
no remote can supply them either — version skew allows at most the previous major, i.e. 2.5, three
majors newer than the last version that had them. Removal path in §10.14.

**One piece of good news while checking this:** `_lookup_phase_name`'s reverse lookup over
`SERVICE_DISCOVERY_PHASES` is **total** over all 13 reachable `check_source` values — including the two
whose key differs from their value (`clustered_monitored → clustered_old`,
`clustered_undecided → clustered_new`) — and all 17 values are pairwise distinct. So
`serialize_discovery_result` cannot raise, and there is **no 500-on-GET**. Totality is incidental rather
than enforced, though: the function takes a bare `str` over an untyped dict, so a new `check_source` in
the check engine would produce a 500 with no compile-time warning.

### 2.2 `DiscoveryAction` (columns) — 12 values, 7 of which reach the state machine

| `DiscoveryAction`                  | entry point                                                     | reaches `Discovery`? |
| ---------------------------------- | --------------------------------------------------------------- | -------------------- |
| `NONE` (`""`)                      | `initial_discovery_result` → `get_check_table`                  | no                   |
| `STOP`                             | `get_check_table` → `execute_discovery_job`                     | no                   |
| `REFRESH`                          | `get_check_table` → starts job                                  | no                   |
| `TABULA_RASA`                      | `get_check_table` → starts job                                  | no                   |
| `UPDATE_HOST_LABELS`               | `perform_host_label_discovery`                                  | no                   |
| `FIX_ALL`                          | `perform_fix_all`                                               | **yes**              |
| `UPDATE_SERVICES`                  | `perform_service_discovery`                                     | **yes**              |
| `BULK_UPDATE`                      | `perform_service_discovery`                                     | **yes**              |
| `SINGLE_UPDATE`                    | `perform_service_discovery`, and `Discovery` directly from REST | **yes**              |
| `SINGLE_UPDATE_SERVICE_PROPERTIES` | `perform_service_discovery`                                     | **yes**              |
| `UPDATE_SERVICE_LABELS`            | `perform_service_discovery`                                     | **yes**              |
| `UPDATE_DISCOVERY_PARAMETERS`      | `perform_service_discovery`                                     | **yes**              |

The 5 non-`Discovery` actions have **uniform** columns: no per-service state changes at all. Their
behaviour is host/job-level and is characterized in §6, not per cell. That collapses the literal
15 × 12 = 180-cell grid to **13 × 7 = 91 live cells**, plus 24 unreachable-row cells and 65
uniform-column cells.

### 2.3 The target axis is not a free choice

`table_target` is _computed_ (`_get_table_target`), not supplied per service. Two very different
target vocabularies feed it:

| Caller                                                 | `update_target` vocabulary                                                                               |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| GUI (`AjaxDiscoveryRequest.update_target: UpdateType`) | 4 values: `new`, `unchanged`, `ignored`, `removed`                                                       |
| REST `execute_service_discovery`                       | hard-coded per mode: `unchanged` or `removed`                                                            |
| REST `update_service_phase` (`target_phase`)           | **all 17** phase names, incl. `manual`, `active`, `custom`, `legacy`, `legacy_ignored`, `clustered_*` ⚠️ |

### 2.4 What the 15 values actually conflate — the axes, corrected

Useful for Phase 3, and it explains most of §4's inconsistencies. The 15 values are a flattening of
**two multi-valued axes and two booleans**:

1. **`origin` ∈ {discovered, enforced, active, custom}** — always known, fully orthogonal.
2. **`lifecycle` ∈ {new, unchanged, changed, vanished}** — the relation between the autochecks file
   and what discovery just found. Defined **only** for `origin=discovered`.
3. **`disabled_by_rule` ∈ {no, yes}** — a **boolean**, not a 4-valued disposition. Defined for all
   origins; the only axis that exists for `active`/`custom`.
4. **`effective_host_is_self` ∈ {yes, no}** — a boolean (`effective_host(host, entry) == host`),
   defined only for `origin=discovered`.

**Why axis 4 earns a place** (it is the least obvious of the four). It is computed at
`_autodiscovery.py:745` and branched on at `:763`, driven by the _clustered services_ ruleset, and it is
**per service, not per host** — one node can have some services effective on itself and others on the
cluster. Its relevance is that it is the only axis that **decouples where the entry is stored from which
host monitors the service**: the `AutocheckEntry` always lives in the _node's_ autochecks file, while
`effective_host` decides which host owns the resulting service object. Axis 2 is about the file, axis 3
is about monitoring, axis 4 is about _whose_ monitoring.

The sharpest way to see why it must be its own axis rather than part of the state name: axes 3 and 4 are
both booleans derived from rulesets, but **discovery writes axis 3 and only reads axis 4**.
`add_disabled_rule`/`remove_disabled_rule` change `disabled_by_rule`; _no_ discovery action can change
`effective_host_is_self` — only editing the clustered-services ruleset can. The four `clustered_*` values
are therefore read-only qualifiers wearing the costume of states, which is why they are simultaneously
accepted as `table_target`s (§4) and meaningless as such.

Three consequences that are invisible until the axis is named:

- **The same service appears on two pages with two different sources.** On the node it is
  `clustered_old`; on the cluster, via `_make_cluster_table`, it is a plain `unchanged`/`changed`/
  `vanished`. Axis 4 is precisely the flag that says which of the two pages is authoritative.
  `_case_clustered` states this in prose — _"we do not allow any operation for this clustered service on
  the related node … Ideally, there would be no service discovery on the cluster hosts at all"_ — and is
  the only handler whose **default is to write**, for exactly that reason. Naming the axis turns that
  special case into a precondition evaluated _before_ the transition table instead of a branch inside it.
- **It explains the asymmetric vocabulary.** Axis 2 has four values when axis 4 is `yes`, but only three
  names when it is `no` (`clustered_old` collapses `unchanged` and `changed`), so a _changed_ clustered
  service is invisible on the node page.
- **It is the only axis that cannot be exercised without a two-host fixture.** 3 of the 13 reachable
  sources (`clustered_old`, `clustered_new`, `clustered_vanished`) require a cluster plus a node, and the
  `# TODO: this does not make much sense` branch adds a _second_ producer of plain `ignored` that also
  needs one. This partitions the Tier-1 plan (§7) and is the practical reason the axis is worth listing
  in a test-planning document at all.

**There is no fifth axis for "disposition".** The words the GUI uses for one —
`monitored`/`ignored`/`undecided`/`removed` — decompose into the four axes above plus one non-state:
`monitored` vs `ignored` is axis 3; `undecided` is not a disposition but `lifecycle=new` ("not in the
autochecks file"); and **`removed` is not a state at all but an operation** — which is exactly why it
has no producer (§2.1).

**The space is 22 cells, covered by 13 of the 14 candidate names** (`clustered_ignored` is the
fourteenth and reaches no cell at all — §2.1):

| origin                                               |  cells |                                                      names |
| ---------------------------------------------------- | -----: | ---------------------------------------------------------: |
| `discovered`, effective=self, not disabled           |      4 |              4 (`new`, `unchanged`, `changed`, `vanished`) |
| `discovered`, disabled (either effective-host value) |      8 |                                              1 (`ignored`) |
| `discovered`, effective=cluster, not disabled        |      4 | 3 (`clustered_new`, `clustered_old`, `clustered_vanished`) |
| `enforced` (± disabled)                              |      2 |                                               1 (`manual`) |
| `active` (± disabled)                                |      2 |                             2 (`active`, `ignored_active`) |
| `custom` (± disabled)                                |      2 |                             2 (`custom`, `ignored_custom`) |
| **total**                                            | **22** |                                                     **13** |

Nine cells are therefore lost to **collapses**, and each collapse causes a specific §4 inconsistency:

| collapse                                        | where                                                                              | causes                                                                                                                                                                                     |
| ----------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ignored` erases `lifecycle`                    | `_autodiscovery.py:766-769, 773-776`                                               | **A2-F2, A2-F3** — the code cannot tell whether an `ignored` service is currently in autochecks, so `ignored → *` has to guess. Also why CMK-33299 needed the `saved_services` workaround. |
| `ignored` erases `effective_host`               | `_autodiscovery.py:772-776`, under its own `# TODO: this does not make much sense` | **`clustered_ignored` unreachable** (§2.1)                                                                                                                                                 |
| `clustered_old` erases `unchanged` vs `changed` | `_autodiscovery.py:780-781`                                                        | a _changed_ clustered service is invisible on the node page — structural sibling of A3-F1                                                                                                  |
| `vanished` wins over `disabled`                 | the `check_source != "vanished"` guard                                             | the `vanished`-row asymmetries, and A2-F2's late symptom                                                                                                                                   |
| no `ignored_manual` name exists                 | `preview.py:216-229` adds `manual` unconditionally                                 | a disabled enforced service is indistinguishable from an enabled one                                                                                                                       |

**The target vocabulary is not a subset of the source vocabulary.** It is a **3**-element _command_ set,
and the size is derivable rather than a judgement call: discovery can write only the autochecks entry and
the disabled-services rule, so the reachable target states are the three legal combinations of those two
booleans — `monitor`, `disable`, `drop` (§11.1). `new` and `removed` are two _labels_ for `drop`,
distinguished by an observation the user cannot change, which is why "only `vanished` may target
`removed`, and `vanished` may target nothing else" holds without anyone enforcing it. Only **4 of 15**
values are honest members of both
vocabularies; 8 are source-only, 1 (`removed`) is target-only, 1 is dead, and 3
(`changed`, `clustered_old`, `clustered_new`) are _half-wired_: `_verify_permissions` and
`_get_autochecks_values` accept them as targets while `_apply_state_change` silently drops the
service. Typing the target as its own enum makes all three `match` statements exhaustive. Ticket in
§10.12.

### 2.4a Per-cell record

Each live cell records:

- **resulting state**
- **autochecks written?**
- **`new_discovered_parameters` adopted?**
- **`new_labels` adopted?**
- **disabled-rule delta**
- **gating permission**
- **local/remote difference**

---

## 3. Matrix A1 — `action` → `table_target` (`_get_table_target`)

Verified by transcribing the function and re-deriving the mapping.

| source ↓ / action →  | `FIX_ALL`           | `UPDATE_SERVICES` (selected) | `UPDATE_SERVICE_LABELS` | `UPDATE_DISCOVERY_PARAMETERS` | `BULK_UPDATE`                                       | `SINGLE_UPDATE`              | `SINGLE_UPDATE_SERVICE_PROPERTIES` |
| -------------------- | ------------------- | ---------------------------- | ----------------------- | ----------------------------- | --------------------------------------------------- | ---------------------------- | ---------------------------------- |
| `new`                | `unchanged`         | `unchanged`                  | `update_target`         | `update_target`               | `update_target` iff `src==update_source` ∧ selected | `update_target` iff selected | `update_target` iff selected       |
| `unchanged`          | `unchanged` (no-op) | no-op                        | `update_target`         | `update_target`               | ditto                                               | ditto                        | ditto                              |
| `changed`            | `unchanged`         | `unchanged`                  | `update_target`         | `update_target`               | ditto, **and matches `update_source=unchanged`**    | ditto                        | ditto                              |
| `vanished`           | `removed`           | `removed`                    | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `ignored`            | `ignored` (no-op)   | no-op                        | `ignored` (no-op)       | `ignored` (no-op)             | ditto                                               | ditto                        | ditto                              |
| `manual`             | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `active`             | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `custom`             | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `ignored_active`     | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `ignored_custom`     | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `clustered_old`      | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `clustered_new`      | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |
| `clustered_vanished` | `unchanged` ⚠️      | `unchanged` ⚠️               | `update_target` ⚠️      | `update_target` ⚠️            | ditto                                               | ditto                        | ditto                              |

### Findings from A1

**A1-F1 — `FIX_ALL` retargets 11 of 13 sources to `unchanged`; the comment claiming otherwise is
false and never was true.** ✅ _verified against the code and the commit history_

`_get_table_target` carries `# entry.check_source in [DiscoveryState.MONITORED,
DiscoveryState.UNDECIDED]` above its `return DiscoveryState.MONITORED`. **11 of 13 reachable
sources** fall through to it — `FIX_ALL` peels off only `vanished` and `ignored`. The table above
lists all 11.

**No upstream filter narrows the sources to the two the comment names.** There is no source-based
filter anywhere between the preview and `Discovery`:

- `_get_effective_check_tables` returns the target host's table _verbatim_ and filters node tables
  only by `found_on_nodes` (`services.py:595-631`); `check_source` is never inspected.
- All four entry points pass the unfiltered `DiscoveryResult` — GUI
  (`wato/pages/services.py:588-598`), REST `execute_service_discovery` (`:106-115`), REST
  `update_service_phase` (`:106-116`), quick setup (`_complete.py:527-546`).
- The `DiscoveryState.is_discovered` filter at `wato/pages/services.py:724-726` is **not** the
  transition table. It lives inside `_get_status_message`, its only consumer is the `if not
cmk_check_entries:` two lines below, and it runs _after_ the action has already executed.
  `cmk_check_entries` appears at exactly lines 724 and 731; `is_discovered` has one call site in the
  whole product tree.
- The producers demonstrably emit the "impossible" sources: `manual` from `enforced_services`
  (`preview.py:216-229`), `active`/`custom` and their ignored variants appended per host in
  `check_mk.py:968-985`, and `clustered_*` from `_node_service_source` on **every node's own
  discovery page** (`_autodiscovery.py:778-782`).
- The repo's own test is the A1-F1 scenario, passing today:
  `tests/unit/cmk/gui/watolib/test_services.py:296-312` hands `perform_fix_all` an `active`/`cmk_inv`
  row, and `:425-433` asserts `set_autochecks_v2` is called.

And it is not comment drift: at `aecd8007105` (June 2020), the commit that created this file,
`DiscoveryState` already carried `MANUAL`/`ACTIVE`/`CUSTOM`/`CLUSTERED_*`/`ACTIVE_IGNORED`/
`CUSTOM_IGNORED` — plus `LEGACY`/`LEGACY_IGNORED` — and `_get_table_target` already had this exact
three-line shape.

**How common?** Not on a bare test host: a fresh site ships no `static_checks` and no `custom_checks`
rules. It fires on the **Checkmk server host itself** — `SHIPPED_RULES["active_checks"]["cmk_inv"]`
is a factory default conditioned on the `cmk/check_mk_server:yes` label
(`sample_config/_constants.py:313-350`) — and on any host with any active or custom check, any
enforced service, and on **every node of every cluster**. A very large fraction of real hosts.

**Quantified cost per click**, for a host `[unchanged × N, active × 1]` with nothing to accept: one
`set-autochecks` pending change **whose diff is empty** (`_make_host_audit_log_object` reduces both
sides to the set of descriptions, and `PendingChanges.add` has no diff-based dedup), one audit-log
entry, one `set-autochecks-v2` automation round trip, one autochecks file rewrite. `need_sync` is
`False`, so no rule work. Note that `FIX_ALL` is not change-free even without this finding:
`_perform_update_host_labels` runs unconditionally and adds an `update-host-labels` change. A1-F1's
_incremental_ damage is therefore the extra `set-autochecks` change, the extra automation round trip
and the extra permission demand — not the existence of a pending change as such.

**The permission over-demand is redundant for `FIX_ALL`** (pre-gated on `to_monitored ∧ to_removed`)
but genuinely observable for `UPDATE_SERVICES`, `UPDATE_SERVICE_LABELS` and
`UPDATE_DISCOVERY_PARAMETERS`, whose pre-gate is only `wato.services` — and quick setup applies **no
pre-gate at all**.

**One genuine state change, not just cost.** `get_host_services_by_host_name` drops
enforced-shadowed entries from the transition table (`_autodiscovery.py:699-703`) and `preview.py`
re-adds them as `manual`, which has no `_apply_state_change` case. So on a host where an "Enforced
services" rule shadows a previously discovered service, a nothing-to-do `FIX_ALL` **silently deletes
that autochecks entry** — and A1-F1 is what makes the save happen at all. Possibly desirable pruning,
but undocumented and untested. Ticket in §10.8.

**A1-F2 — `UPDATE_SERVICE_LABELS` and `UPDATE_DISCOVERY_PARAMETERS` retarget every row on the host,
because the `update_source` filter their callers transmit is never applied.** ✅ _verified against the
code, the werks and the commit history_

Neither branch consults `selected_services` (`services.py:558-566`), so both actions retarget **every
entry in the table** to `update_target`. Both callers pass `unchanged` (GUI
`wato/pages/services.py:2667, 2685`; REST `only_service_labels`). The `update_source="changed"` that
both callers transmit is read **only** inside the `BULK_UPDATE` branch (`:574`), so the "changed
services only" intent is silently dropped.

- **`new` → `unchanged` — this is where the damage is.** `_case_undecided(MONITORED)`
  (`:992-994`) writes the service to autochecks. **"Update service labels" accepts every undecided
  service on the host.** Ticket in §10.5.
- **`vanished` → `unchanged` — reachable, but harmless to the data.** A vanished service is _already_
  in autochecks (that is what makes it vanished: preexisting but not current), and for a vanished row
  `DiscoveredItem(previous=v, new=None)` sets `older = newer = v` (`types.py:130-136`), so
  `old_discovered_parameters == new_discovered_parameters` and the write is **byte-identical**.
  Nothing is corrupted and nothing is resurrected. The only effect is that the service is not cleaned
  up — which it would not have been anyway without an explicit removal.
- **`manual`/`active`/`custom`/`ignored_*`/`clustered_*` → `unchanged` — noise, with two teeth.**
  It forces the host-global `apply_changes`, producing an autochecks rewrite and a
  `set-autochecks` pending change on a host where nothing changed, and it demands
  `wato.service_discovery_to_monitored` — which the pre-gate for these actions does **not** require
  (it asks only for `wato.services`), so the action can raise `MKAuthException` from inside the
  handler for a user the pre-gate admitted. `compute_discovery_transition` is pure and raises before
  any write, so no partial state persists.

**The missing check is `update_source`, not `selected_services` — and that distinction decides the
fix.** The host-wide _scope_ is deliberate: the branch never had a selection check
(`89d6c5d92c9`, CMK-15505, 2024-01-16, and `249d6863937` copying it for the parameters action), the
same author built the selection-gated sibling `SINGLE_UPDATE_SERVICE_PROPERTIES` on purpose, the
frontend never sends a selection for these actions (`service_discovery.ts:145`), and the bulk /
periodic equivalents are plain host-level booleans. What is missing is the **source** filter:

- Werk **16466** (2.4.0b1): _"Service labels can be manually updated with dedicated actions targeting
  **all changed services** or a specific service."_
- Werk **17710** (2.5.0b1): same promise for discovery parameters.
- Both callers already transmit `update_source="changed"`, and the GUI even gates button enablement
  on `has_changed_services` (`wato/pages/services.py:1361-1363`). The backend ignores both.

**Werk 17711 / CMK-22272 settles the intent** (`0f997886c9a0`, same author, classed **fix**):
_"The 'Update service labels' action … used to move disabled services to monitored services. … Now,
this is no longer the case."_ Its entire diff is the `IGNORED` carve-out now sitting in both branches.
So the maintainers **already ruled that retargeting a non-`changed` source under this action is a
bug** — and fixed it for the single source a customer reported, leaving `new`, `vanished`, `manual`,
`active`, `custom`, `ignored_active`, `ignored_custom` and `clustered_*` untouched.
`new → monitored` is the same failure mode as `ignored → monitored`, with worse consequences.

Consequently the fix should key off `update_source`, not `selected_services`:
`tests/unit/cmk/gui/watolib/test_services.py:2201-2235` currently _pins_ the selection-ignoring
behaviour, so a `selected_services`-based fix breaks it while an `update_source`-based fix keeps it
green. Ticket in §10.5.

**Reachability differs by caller:** the GUI button is disabled unless the host has a changed service
(`:1361-1363`, and disabled entries are `pointer-events: none`), so the GUI needs one changed service
present. REST has no such gate — `only_service_labels` on a host with **only** undecided services
accepts them all, making that mode a silent superset of mode `new` with a weaker pre-gate.

**A1-F3 — `FIX_ALL` ≠ `UPDATE_SERVICES`** on two counts, despite identical target mapping:
value adoption (§5) and the disabled-rule subtraction (§4.2).

**A1-F4 — the `changed`-counts-as-`unchanged` alias in `BULK_UPDATE` is correct and disclosed in the
button titles; the defect is in the page-menu wiring beside it.** ✅ _verified against the code_

`BULK_UPDATE` matches an entry when `check_source == update_source`, or when
`check_source == changed and update_source == unchanged` (`services.py:571-581`).

**`changed` genuinely is a subset of `monitored`, so the alias is sound.**
`QualifiedDiscovery.changed` requires the
`ServiceID` to be in _both_ `preexisting` and `current` (`types.py:164-168`), and `preexisting` is
read from `AutochecksStore(...).read()` (`preview.py:179-183`). So a `changed` service **is
physically in the autochecks file and monitored right now**; only its discovered parameters or
service labels differ (`comparator()` is `(parameters, service_labels)`). The code comment is
accurate.

**Only two of the eight bulk buttons are affected**, and both announce it in their own titles:
"Declare monitored, **including changed**, services as undecided" (`unchanged → new`) and "Disable
monitored, **including changed**, services" (`unchanged → ignored`). REST is unaffected — it only
uses `BULK_UPDATE` with `update_source ∈ {new, vanished}`.

**The outcome for a picked-up `changed` service is correct.** `_apply_state_change` dispatches on
`table_source`, not `update_source`, so `_case_changed` runs. For target `new` the service is not in
`[MONITORED, IGNORED, CHANGED]` → dropped from autochecks; the new discovered values are _irrelevant
rather than lost_, since `_get_autochecks_values` does not substitute for target `new` and the value
is never written anyway. The service returns as `new` on the next preview, where the new parameters
are what would be accepted. Behaviour matches the button title.

**The alias is asymmetric** (`update_source=changed` does not match `unchanged`), and that asymmetry
does bite — not in `_get_table_target`, where no caller passes `update_source=changed`, but in the
page-menu wiring. `_toggle_bulk_action_page_menu_entries` handles `MONITORED | CHANGED` in one arm
and enables `f"bulk_{table_source}_{target}"` (`wato/pages/services.py:1379-1383, 1404-1405`), so the
**Changed services** table emits `bulk_changed_new` / `bulk_changed_ignored` — **and no
`PageMenuEntry` with those names exists** (`grep -rn "bulk_changed"` → nothing; the eight real names
are all `bulk_{new,unchanged,ignored,vanished}_*`). `enable_page_menu_entry` resolves a null element
and silently does nothing. On a host where every monitored service is classified `changed` and no
`unchanged` table is rendered, both "including changed" buttons stay permanently greyed out. Ticket
in §10.7.

**One more trap for the rewrite:** `_perform_discovery_action` lists `UPDATE_SERVICES` in the
combined `case` arm at `wato/pages/services.py:626-633`, which makes the dedicated
`case DiscoveryAction.UPDATE_SERVICES:` at `:649-664` — the one that deliberately forces
`update_source=None, update_target=None` — **unreachable**. Inert today, but anyone deleting the
"redundant" first arm during the rewrite changes behaviour.

---

## 4. Matrix A2 — `(source, target)` → outcome (`_apply_state_change`)

| source ↓ / target →                                                                                                                                | `new`                         | `unchanged`                             | `changed`                          | `vanished`                 | `ignored`                                 | `removed`                                 | `clustered_new` / `clustered_old` | other                    |
| -------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------- | ---------------------------------- | -------------------------- | ----------------------------------------- | ----------------------------------------- | --------------------------------- | ------------------------ |
| **`new`** (`_case_undecided`)                                                                                                                      | no-op                         | **AC**, SV · `to_monitored`             | ✗ — · `to_monitored`               | ✗ — · _none_ ⚠️            | **+D** · `to_ignored`                     | ✗ — · `to_removed`                        | — · `to_monitored`                | — · _none_ ⚠️            |
| **`unchanged`** (`_case_monitored`)                                                                                                                | **drop**, SV · `to_undecided` | AC, SV (no-op)                          | ✗ **drop**, SV · `to_monitored` ⚠️ | ✗ **drop**, SV · _none_ ⚠️ | **AC** + **+D** ⚠️ · `to_ignored`         | ✗ **drop**, SV · `to_removed`             | **drop**, SV · `to_monitored` ⚠️  | **drop**, SV · _none_ ⚠️ |
| **`changed`** (`_case_changed`)                                                                                                                    | **drop**, SV · `to_undecided` | **AC**, SV · `to_monitored`             | AC, SV (no-op)                     | ✗ **drop**, SV · _none_ ⚠️ | **AC** + **+D** · `to_ignored`            | ✗ **drop**, SV · `to_removed`             | **drop**, SV · `to_monitored` ⚠️  | **drop**, SV · _none_ ⚠️ |
| **`vanished`** (`_case_vanished`) — ✗ **every target but `removed` is an invalid transition (A2-F6)**                                              | ✗ **AC**, SV · `to_undecided` | ✗ **AC**, SV · `to_monitored`           | ✗ **AC**, SV · `to_monitored`      | ✗ AC, SV                   | ✗ **AC** + **+D** · `to_ignored`          | **drop** (early return) · `to_removed`    | ✗ **AC**, SV · `to_monitored`     | ✗ **AC**, SV · _none_ ⚠️ |
| **`ignored`** (`_case_ignored`)                                                                                                                    | **−D**, drop · `to_undecided` | **AC** + **−D**, SV · `to_monitored` ⚠️ | ✗ **drop** · `to_monitored`        | ✗ **−D**, drop · _none_ ⚠️ | **+D**, SV, **not AC** (no-op, CMK-33299) | ✗ **drop**, no rule change · `to_removed` | **drop** · `to_monitored`         | **drop** · _none_ ⚠️     |
| **`manual`**, **`active`**, **`custom`**, **`ignored_active`**, **`ignored_custom`** (no `case` matches)                                           | nothing · `to_undecided`      | nothing · `to_monitored`                | nothing · `to_monitored`           | nothing · _none_           | nothing · `to_ignored` ⚠️                 | nothing · `to_removed`                    | nothing · `to_monitored`          | nothing · _none_         |
| **`clustered_old`**, **`clustered_new`**, **`clustered_vanished`** (`_case_clustered`) — ✗ **no target is a valid transition on the node (A2-F7)** | ✗ **AC**, SV · `to_undecided` | ✗ **AC**, SV · `to_monitored`           | ✗ **AC**, SV · `to_monitored`      | ✗ **AC**, SV · _none_      | ✗ **drop**, **no +D** ⚠️ · `to_ignored`   | ✗ **AC**, SV · `to_removed`               | ✗ **AC**, SV · `to_monitored`     | ✗ **AC**, SV · _none_    |

### Legend

**AC**: written to `new_autochecks`.

**+D** / **−D**: added to `add_disabled_rule` / `remove_disabled_rule`.

**SV**: added to `saved_services` (feeds the §4.2 subtraction).

**Perm**: demanded via `user_need_permission`, only when `source != target`.

**✗**: the cell is an **invalid transition** — the recorded outcome characterises a bug, not a behaviour
to preserve. Four distinct reasons, corresponding to the four rules of §11.2a:

- the target is not one of the three commands — the whole `changed`, `vanished`, `manual`/`active`/
  `custom`/`ignored_*` and `clustered_*` **columns**, because each names a fact discovery cannot write;
- the `removed` column on any still-discovered source, because `removed` and `new` are one command
  (`drop`) and `removed` is the label reserved for `vanished` rows (§11.3);
- the `vanished` row apart from `removed`, because the target names a state the classifier cannot produce
  for a service that is no longer discovered (**A2-F6**);
- every cell of the `clustered_*` and non-discovered-origin **rows**, because the row is not this page's
  to change (**A2-F7**, §11.2a).

The table still records what the code does today, because the guardrail tests have to pin it before it
is removed — see the Tier 1a / 1b split in §7.

**"other"** = every target name not otherwise listed: `manual`, `active`, `custom`,
`ignored_active`, `ignored_custom`, `clustered_vanished`, `legacy`, `legacy_ignored`
(reachable only via REST `update_service_phase`). All behave identically, and **none demands a
permission**.

### Findings from A2

**A2-F1 — "drop" is the default cell: an unrecognised target silently deletes the service. The data
loss is real; the accompanying permission hole is latent rather than exploitable today.**
✅ _verified against the code_

Every `—`/`drop` cell deletes the service from autochecks, because `set_autochecks_v2` is a full
replace for the effective host (`_autochecks.py:202-222`: _"Set all services of an effective host,
and leave all other services alone"_).

**Permission half — not a privilege escalation today.** `Discovery` is constructed in exactly three
places, and only `update_service_phase` can supply an exotic target. That handler demands **all
four** `wato.service_discovery_to_*` unconditionally (`update_service_phase.py:61-64`), which is
strictly more than `_verify_permissions` would ever ask. No caller can reach an exotic target while
holding fewer permissions, so there is no escalation today. The missing default arm is a **latent**
hole, not a live one — and because `table_target` is typed `str`, mypy cannot flag a regression. It
becomes live the moment a second caller is added, which is exactly what the planned batch-apply
endpoint does.

**Data-loss half — real.** 13 of the 17 accepted `target_phase` values delete a monitored service and
return `204 No Content`. **10** of the 17 demand no permission at all, because they appear in none of
`_verify_permissions`' match arms — note that `clustered_ignored` belongs in this group, as it is
absent from the `MONITORED | CHANGED | CLUSTERED_NEW | CLUSTERED_OLD` arm that catches the other three
`clustered_*` values:

| demands          | target phases                                                                                                                                       |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `to_undecided`   | `undecided`                                                                                                                                         |
| `to_monitored`   | `monitored`, `changed`, `clustered_monitored`, `clustered_undecided`                                                                                |
| `to_ignored`     | `ignored`                                                                                                                                           |
| `to_removed`     | `removed`                                                                                                                                           |
| **nothing (10)** | `vanished`, `manual`, `active`, `ignored_active`, `custom`, `ignored_custom`, `clustered_vanished`, `clustered_ignored`, `legacy`, `legacy_ignored` |

Outcome depends on the _source_, not only the target: for source `unchanged` all 13 delete the
service (byte-identical in effect to `removed`); for `changed`, 12 delete; for `vanished` and
`clustered_*` all 13 **keep** it; for `manual`/`active`/`custom`/`ignored_*`/`new` nothing is
recorded but `apply_changes` still forces a full identity rewrite plus a spurious pending change.
Ticket in §10.3. Note the deletion _is_ auditable — `_make_host_audit_log_object` diffs old against
new autochecks — it is silent to the caller, not to an auditor.

**A2-F2 — DEFECT: werk 19800 closed the "disabled service is never written to autochecks" hole for two
of the four sources that can legitimately be disabled.** ✅ _verified against the code, the commit and
the werk_

Scope. `ignored` is a valid target for four sources: `ignored` (a no-op), `clustered_*`, `unchanged` and
`changed`. The werk fixed the first two; `unchanged` and `changed` still write, and those two cells are
this finding. A fifth handler, `_case_vanished`, also writes — but there `ignored` is not a state the
service can occupy at all, so it is a different defect with a different fix (withdraw the transition,
not correct it): see **A2-F6**.

Werk 19801 states the contract plainly: _"services matched by 'Disabled services' are no longer
written into autochecks"_. Werk 19800 / CMK-33299 (`3b05a138153`) implemented it — but its
`services.py` diff touched **only** `_case_ignored` and `_case_clustered`:

```diff
 def _case_ignored(...):
-    if table_target in [DiscoveryState.MONITORED, DiscoveryState.IGNORED]:
+    if table_target == DiscoveryState.MONITORED:
         autochecks_to_save[key] = value
```

The three sibling handlers still carry their January-2024 code (`git blame` → `89d6c5d92c9`) and
still write the service when the target is `ignored`:

| transition              | handler           | line                    | writes autochecks?                                 |
| ----------------------- | ----------------- | ----------------------- | -------------------------------------------------- |
| `ignored → ignored`     | `_case_ignored`   | `services.py:1077-1078` | no — **fixed**                                     |
| `clustered_* → ignored` | `_case_clustered` | `services.py:1106-1108` | no — **fixed**                                     |
| `unchanged → ignored`   | `_case_monitored` | `services.py:1027-1031` | **yes — gap**                                      |
| `changed → ignored`     | `_case_changed`   | `services.py:1048-1053` | **yes — gap**                                      |
| `vanished → ignored`    | `_case_vanished`  | `services.py:1010-1012` | **yes** — but an invalid transition, see **A2-F6** |

Nothing downstream filters it out: `_save_services` → `set_autochecks_v2` →
`_automation_set_autochecks_v2` → `set_autochecks_for_effective_host`
(`_autochecks.py:202-222`) never consults `ignore_service` / `ignore_plugin`.

So the fix covers the **rule-driven** case (a service that was _already_ classified `ignored`
because a rule matched it) but not the **user-action** case — clicking "disable" on a currently
monitored service, which is the ordinary way a disabled service comes into being.

**Why it matters — and what the symptom is _not_.** A disabled service reappearing as `vanished` is
easily mistaken for the bug. It is not: werk 19801 designates that reappearance as the **intended
cleanup signal**.

> _"Previously accumulated entries for such services will now appear as vanished during service
> discovery. To clean up existing autochecks, run a re-discovery on the affected hosts to remove these
> services."_

Appearing as `vanished` is the remediation path. The defect is the **residue**: an autochecks entry for
a service that a "Disabled services" rule matches. It accumulates without bound on hosts with volatile
services, and every subsequent preview has to classify it — as `ignored` while the rule matches, as
`vanished` once the service also disappears from the agent output.

Stated as the rule the implementation violates:

> **A service matched by a "Disabled services" rule must never be written to the autochecks file.**

**A2-F3 — there is no `undecided` inconsistency: `unchanged` is the only source for which the target is
valid at all.** ✅ _verified against the code_

The three sources that appear to disagree about what "declare as undecided" means do not in fact
disagree, because only one of them may be asked:

| transition          | outcome today               | verdict                                                                                                               |
| ------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `unchanged → new`   | **removes** from autochecks | the only valid one — "forget it", and the service returns as `new` on the next preview because it is still discovered |
| `vanished → new`    | **keeps** it                | invalid: `new` presupposes discovery, which a vanished service lacks (**A2-F6**)                                      |
| `clustered_* → new` | **keeps** it                | invalid: no operation on a clustered row is valid on the node (**A2-F7**)                                             |

The two "keeps" are therefore not an inconsistency to reconcile but the handlers declining to act on a
request that should never have reached them — correctly, in the clustered case. What remains of this
finding is a note for the rewrite: the appearance of inconsistency in a transition table is a reliable
symptom that the table contains cells that should be rejections.

**A2-F7 — DEFECT: no operation on a `clustered_*` row is valid on the node, but the backend accepts all
of them, and one of them mutates the cluster's monitoring.** ✅ _verified against the code_

A `clustered_*` row means a "Clustered services" rule assigns the service to a cluster. The autocheck
entry lives in the **node's** file, but the service is **owned by the cluster** — and so is the
responsibility for discovering it. `_case_clustered`'s own comment states the rule:

> _"If a service is mapped to a cluster then there are already operations for adding, removing, etc. of
> this service on the cluster. Therefore we do not allow any operation for this clustered service on the
> related node. We just display the clustered service state (OLD, NEW, VANISHED). … Ideally, there would
> be no service discovery on the cluster hosts at all."_

**No transition is needed on the node, because the node has nothing to decide.** If the clustering rule
is later removed, `_node_service_source`'s `host_name == cluster_name` branch returns the plain basic
transition, so the service simply reappears as `unchanged` on the node — the entry was never removed
from the node's autochecks, so nothing has to be migrated. The `clustered_*` display states are
informational, and the correct response to any operation on them is a rejection pointing at the cluster.

**The GUI already implements this; the backend does not.**

| layer                               | behaviour                                                                                                                                                                                |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GUI table groups                    | all four clustered groups pass `show_bulk_actions=False` (`wato/pages/services.py:2068, 2141, 2154, 2169`), and three render collapsed by default (`isopen` excludes them, `:1181-1187`) |
| GUI row buttons                     | `_show_check_row`'s `match entry.check_source` has **no** `clustered_*` arm, so no per-row icon is emitted                                                                               |
| `_verify_permissions`               | accepts `clustered_new` / `clustered_old` as targets (`to_monitored` arm)                                                                                                                |
| `_apply_state_change`               | dispatches to `_case_clustered`, which **acts** rather than rejecting                                                                                                                    |
| REST `update_service_phase`         | accepts any of the 17 `target_phase` values on a clustered row                                                                                                                           |
| `FIX_ALL` / `UPDATE_SERVICE_LABELS` | retarget clustered rows along with everything else (A1-F1, A1-F2)                                                                                                                        |

**What `_case_clustered` does** (`services.py:1091-1108`) — its default is to preserve, which is the
right instinct, but it is preservation-by-rewrite rather than rejection, and it has one exception:

- every target except `ignored`: rewrites the same entry and adds to `saved_services`. Harmless to the
  data, but it forces the host-global `apply_changes`, so a `set-autochecks` pending change and an
  automation round trip are produced for a host where nothing changed — the A1-F1 noise pattern.
- target `ignored`: **drops the entry from the node's autochecks and adds no disabled rule at all**,
  despite the comment's carve-out _"But if the user wants to disable the service on the host, this is
  what we do."_ Since cluster services are gathered from the nodes' autochecks filtered by
  `effective_host`, dropping the node's entry **silently un-monitors the service on the cluster**, with
  no rule recording why and nothing on the cluster's own page to explain it. The next discovery on the
  node re-adds it as `clustered_new`, so the effect is a transient outage of a cluster service triggered
  from a page that is not supposed to allow any action. This is the one clustered cell with real harm.

Ticket in §10.17.

**A2-F4 — `vanished`'s catch-all `else` keeps the service.** `_case_vanished` only drops on
`removed` and special-cases `ignored`; every other target falls into `else: keep`. So `removed` is the
_only_ target that cleans up a vanished service — every other one, including the `unchanged` that
A1-F2 assigns to every row, silently preserves it. The preserved write is value-identical (see A1-F2:
`older is newer` for vanished rows), so nothing is corrupted or resurrected; the effect is a failure to
clean up, plus a spurious autochecks rewrite.

**A2-F5 — writing an `ignored_services` rule without a `may_edit_ruleset` check is harmless on the GUI
paths; the equivalent gap in the REST endpoint is not.** ✅ _verified against the code_

`BULK_UPDATE → ignored` writes an `ignored_services` rule without the `may_edit_ruleset` check that
`has_modification_specific_permissions` performs. On GUI paths that omission is **vacuous**, because of
how the predicate is defined (`rulesets.py:2204-2206`):

```python
def may_edit_ruleset(varname: str) -> bool:
    if varname == "ignored_services":
        return user.may("wato.services") or user.may("wato.rulesets")
```

`ignored_services` is not a restricted ruleset — `wato.services` alone satisfies it. And every
`perform_*` path runs inside `_service_discovery_context`, whose first statement is
`user.need_permission("wato.services")`. So on every GUI path the predicate is **already true by
construction**; adding it to `_verify_permissions` would change nothing. There is no locked-ruleset
mechanism for `ignored_services` to exploit.

The check _is_ bypassable — but only via `update_service_phase`, which never enters
`_service_discovery_context` at all. That is P-F1, not a separate finding, and it is confirmed:
see §5.1 and the ticket in §10.4.

Two further defects sit in the same area, both independent of the ruleset question:

- **The GUI bulk pre-gate disagrees with the inner gate.** `has_discovery_action_specific_permissions`
  for `BULK_UPDATE` (`services.py:811-815`) returns `may_all("to_monitored", "to_removed")` and
  ignores `update_target` entirely, while `_toggle_bulk_action_page_menu_entries` enables each button
  on its own target's permission (`wato/pages/services.py:1379-1383`). A user holding only
  `to_undecided` sees "Declare monitored services as undecided" **enabled**, and clicking it is
  rewritten to `DiscoveryAction.NONE` — the page refreshes and nothing happens, with no message.
  Fails closed, so not a security issue, but a silent dead end. Ticket in §10.6.
- **`EnabledDisabledServicesEditor` performs no permission check of its own**, and neither does the
  generic ruleset-save path (`RulesetCollection._save_folder`). `may_edit_ruleset` is exclusively a
  UI-rendering and pre-gate predicate. Any new caller of the editor is unguarded by default.

**A2-F6 — DEFECT: `removed` is the only valid target for a `vanished` service, yet the GUI and REST
offer three others.** ✅ _verified against the code and the existing test pins_

A vanished service is present in the autochecks file and **no longer discovered**. Every other target
names a state that such a service cannot occupy, so no implementation of those transitions can be
correct — the next preview contradicts whatever was written:

| target                  | why it is invalid                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ignored`               | The classifier never assigns `ignored` to a not-discovered service. `_node_service_source` skips the ignore filter whenever the basic transition is `vanished` (the `check_source != "vanished"` guard, `_autodiscovery.py:764`), and `_make_cluster_table` carries the same guard. So a vanished service matching a "Disabled services" rule still shows as **`vanished`**. |
| `new` (undecided)       | `new` means _discovered but not in autochecks_. A vanished service is not discovered, so dropping its entry does not make it undecided — it makes it disappear. `new` is therefore unreachable, and the operation is indistinguishable from `removed` (§11.3).                                                                                                               |
| `unchanged` (monitored) | Monitoring a service that is not there yields an immediate stale/UNKNOWN check, and the next preview re-classifies it `vanished`.                                                                                                                                                                                                                                            |

The first is pinned by two tests whose docstring states the rule outright:

> `test_vanished_service_matching_disabled_rule_is_discovered_as_vanished`
> (`packages/cmk-check-engine/tests/cmk/checkengine/discovery/test__autodiscovery.py:127`, cluster
> variant at `:214`) — _"A service absent from the agent output must be classified as 'vanished' even
> when a disabled-services rule matches it. Previously the ignore rule won and the service was hidden as
> 'ignored', masking the fact that it had disappeared from the host."_

**What each invalid target does today.** `_case_vanished` drops the service only on `removed`; `ignored`
additionally creates a rule, and everything else falls into the catch-all `else` (A2-F4):

```python
if table_target == DiscoveryState.REMOVED:
    return                                   # the only correct outcome
if table_target == DiscoveryState.IGNORED:
    add_disabled_rule.add(descr)
    autochecks_to_save[key] = value          # entry + rule = werk 19801 residue
else:
    autochecks_to_save[key] = value          # entry kept, no rule
    saved_services.add(descr)
```

`vanished → ignored` is the damaging one: it produces an autochecks entry _for a service a disabled
rule matches_, which is exactly the residue werk 19801's vanished-classification exists to eliminate
(A2-F2). And it cannot be escaped by repeating the action — the service is preexisting and not current
on every subsequent preview, so it stays `vanished` indefinitely, now carrying a rule that changes
nothing. Only "Remove vanished services" resolves it. `vanished → new` and `vanished → unchanged` keep
the entry without a rule, so they are a failure to clean up rather than residue (A2-F4: the write is
value-identical, so nothing is corrupted).

**Where the invalid transitions are offered.** Not a REST-only over-permissiveness — the GUI offers
`ignored` in two places:

| offered by                                       | code                                                                                                                    | gate                                                                                                                                                                                                          |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GUI bulk action **"Disable vanished services"**  | `BulkEntry(VANISHED, IGNORED, …)` at `wato/pages/services.py:2630-2637` → `PageMenuEntry(name="bulk_vanished_ignored")` | enabled by `_toggle_bulk_action_page_menu_entries`, `case DiscoveryState.VANISHED` (`:1392-1397`), for any user holding `to_ignored`. `is_shortcut=False, is_show_more=True`, so it renders under "Show more" |
| GUI per-row **"Move to disabled services"** icon | `case DiscoveryState.VANISHED` → `_icon_button(VANISHED, …, IGNORED, "disabled", …)` (`:1815-1827`, helper at `:1889`)  | `has_modification_specific_permissions(UpdateType.IGNORED)`                                                                                                                                                   |
| REST `update_service_phase`                      | `target_phase` ∈ `{ignored, undecided, monitored, …}` — 13 of 17 values (§10.3)                                         | the four blanket `to_*` permissions (P-F1)                                                                                                                                                                    |
| indirectly, `UPDATE_SERVICE_LABELS`              | assigns `update_target=unchanged` to _every_ row including vanished (A1-F2)                                             | `wato.services`                                                                                                                                                                                               |

The GUI does **not** offer `vanished → new` per row; `_icon_button`'s VANISHED arm emits only `removed`
and `ignored`. That target is reachable through REST, which the endpoint's own HATEOAS links advertise
on vanished rows (§5.2).

**Why the fix is a rejection, not a repair.** Making `_case_vanished` drop the entry on `ignored` would
turn "Disable vanished services" into a duplicate of "Remove vanished services" that additionally writes
a disabled-services rule for a service that no longer exists — a confusing near-synonym, not a
correction. The transition has to be withdrawn at the edges: remove both GUI affordances, and have REST
answer `400` for the pair. Ticket in §10.16.

### 4.2 Cross-cell arithmetic (not derivable per cell)

```python
need_sync = bool(remove_disabled_rule or add_disabled_rule)          # computed BEFORE subtraction
add_disabled_rule = add_disabled_rule - remove_disabled_rule - (saved_services - selected_services)
```

- `need_sync` is computed from the **pre-subtraction** sets — hence the code's
  `# Watch out! Can't be derived from the next two!`. `need_sync=True` with a final
  `add_disabled_rule == ∅` is reachable, and it sets `force_sync=True` on the pending change while
  the rule editor no-ops.
- `selected_services` here is the set of _descriptions_ of `self._selected_services`
  (`_get_selected_descriptions`). For `FIX_ALL` it is `()` → **empty**, so the subtraction is
  `− saved_services`. For `UPDATE_SERVICES` invoked from the GUI without checkboxes it is
  `EVERYTHING` → **all descriptions**, so the subtraction term collapses to `∅`.
  **`FIX_ALL` and `UPDATE_SERVICES` therefore compute different disabled-rule sets** on hosts with
  duplicate service descriptions. (A1-F3.)
- `old_autochecks` (audit diff only) is built from sources
  `{unchanged, changed, ignored, vanished}` using **old** values — so an `ignored` service appears
  in the "before" side of the diff even though it is not in autochecks.

---

## 5. Matrix A3 — value adoption

```
new_discovered_parameters adopted  ⟺  action ∈ {FIX_ALL, UPDATE_DISCOVERY_PARAMETERS,
                                                SINGLE_UPDATE_SERVICE_PROPERTIES}
new_labels               adopted  ⟺  action ∈ {FIX_ALL, UPDATE_SERVICE_LABELS,
                                                SINGLE_UPDATE_SERVICE_PROPERTIES}
                          … AND  source != target
                          … AND  target ∈ {unchanged, changed, clustered_new, clustered_old}
```

| action                                                         | params adopted | labels adopted |
| -------------------------------------------------------------- | -------------- | -------------- |
| `FIX_ALL`                                                      | ✅             | ✅             |
| `SINGLE_UPDATE_SERVICE_PROPERTIES`                             | ✅             | ✅             |
| `UPDATE_DISCOVERY_PARAMETERS`                                  | ✅             | ❌             |
| `UPDATE_SERVICE_LABELS`                                        | ❌             | ✅             |
| `UPDATE_SERVICES`                                              | ❌ ⚠️          | ❌ ⚠️          |
| `BULK_UPDATE`                                                  | ❌ ⚠️          | ❌ ⚠️          |
| `SINGLE_UPDATE`                                                | ❌ ⚠️          | ❌ ⚠️          |
| `NONE`, `STOP`, `REFRESH`, `TABULA_RASA`, `UPDATE_HOST_LABELS` | n/a            | n/a            |

**A3-F1 — non-adoption is deliberate, and it is the trap for batch apply.**
`SINGLE_UPDATE` (the GUI "move to monitored" arrow) and `BULK_UPDATE` (GUI bulk buttons, REST
`new`/`remove`) reclassify a `changed` service to `unchanged` while writing its **old** parameters
and labels, so it re-appears as `changed` on the next preview. Only `FIX_ALL`,
`SINGLE_UPDATE_SERVICE_PROPERTIES` and the two dedicated `UPDATE_*` actions adopt.

> **Reviewer disposition: intended behaviour.** This separation is the reason
> `UPDATE_SERVICE_LABELS` and `UPDATE_DISCOVERY_PARAMETERS` exist as distinct actions — moving a
> service between phases and adopting its newly discovered properties are two different operations,
> and the narrow actions let a user do the second without the first.

Recorded here not as a defect but because it is the exact semantic the hackathon PoC's apply path
lost: it behaved like `SINGLE_UPDATE` while being presented as "Fix all". A batch-apply endpoint
must state, per disposition, which side of this line it is on — and if it wants both behaviours it
needs an explicit flag, not an implicit default.

**Scope:** adoption is observable **only for source `changed`**. `DiscoveredItem` sets
`older = newer` whenever either side is `None` (`types.py:130-136`), so for `new`, `vanished`,
`clustered_new` and `clustered_vanished` the old and new parameters and labels are identical and
"adoption" is a no-op. `changed` is by definition the only transition where both sides are set and
differ. The formula above is correct; its _impact_ is confined to `changed` (and to `clustered_old`
derived from a `changed` node transition).

**A3-F2 — `TABULA_RASA` accepts everything by a second, independent mechanism.** It does not go
through `Discovery` at all; `_perform_automatic_refresh` calls `local_discovery` with
`DiscoverySettings(update_host_labels=True, add_new_services=True, remove_vanished_services=True,
update_changed_service_labels=True, update_changed_service_parameters=True)`.

> **Reviewer disposition: the difference is intentional.** `FIX_ALL` accepts everything;
> `TABULA_RASA` _forgets_ everything and then accepts everything. A meaningful distinction, not a
> duplication — the two are not interchangeable today.
>
> **Open question for after the epic:** once Phase 1's primitives exist
> (`invalidate cache` + `start_scan` + `fix_all`), is `TABULA_RASA` still needed as its own action,
> or does it become a composition of them? That is Story F2's real question, and it is worth asking
> _after_ the rewrite rather than before.

### 5.1 Permission table

| gate                 | where                                                 | what it demands                                                                                                                                                                                                                                                                                                                                               |
| -------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pre-gate, per action | `has_discovery_action_specific_permissions`           | `NONE`/`STOP`/`REFRESH`/`UPDATE_HOST_LABELS`/`UPDATE_SERVICE_LABELS`/`UPDATE_DISCOVERY_PARAMETERS`/`UPDATE_SERVICES` → `wato.services`; `FIX_ALL`/`BULK_UPDATE` → `to_monitored` ∧ `to_removed`; `TABULA_RASA` → `to_undecided` ∧ `to_monitored` ∧ `to_removed`; `SINGLE_UPDATE*` → `has_modification_specific_permissions(update_target)` (`None` → `False`) |
| context gate         | `_service_discovery_context`                          | `wato.services`, for all three `perform_*` functions                                                                                                                                                                                                                                                                                                          |
| per-cell gate        | `Discovery._verify_permissions`                       | see §4 `Perm` column; **no default arm**                                                                                                                                                                                                                                                                                                                      |
| ruleset gate         | `has_modification_specific_permissions(IGNORED)` only | `may_edit_ruleset("ignored_services")`                                                                                                                                                                                                                                                                                                                        |

**P-F1 — AUTHORIZATION GAP: `update_service_phase` bypasses `wato.services` _and_ `wato.edit`, and
requires only host _read_ on a mutating `PUT`.** ✅ _verified against the code_

`update_service_phase_v1` constructs `Discovery(...).do_discovery(...)` directly
(`update_service_phase.py:99-123`), bypassing `_service_discovery_context` — whose sole purpose is
`user.need_permission("wato.services")`. Its complete authorization surface is:

1. authentication only, at the WSGI layer — no role or permission gate;
2. host **read**, via `HostConverter(permission_type="setup_read")` (`:52`) — satisfied by
   `wato.see_all_folders` _or_ contact-group membership. **Not write. On a `PUT` that mutates
   configuration.**
3. the four `wato.service_discovery_to_*` (`:61-64`).

`wato.services`, `wato.rulesets` and `wato.edit` are never checked. Every sibling endpoint in the
same family requires `wato.edit` (`execute_service_discovery.py:58`; `DISCOVERY_PERMISSIONS` and
`RO_PERMISSIONS` in `_utils.py:49-77`); `UPDATE_PHASE_PERMISSIONS` declares neither.

Note that `EndpointPermissions(required=...)` is **not** an authorization gate — the framework
validates it only _after_ the handler has run and written to disk, and only to check that declared
permissions were used. Authorization is exclusively the explicit `need_permission` calls.

**Consequence.** A custom role granted the four discovery-target permissions but deliberately denied
"Manage services" and "Rule sets" is correctly locked out of the entire GUI discovery page — every
control checks `user.may("wato.services")` — yet can still `PUT target_phase: "ignored"` and have
`EnabledDisabledServicesEditor` create an `ignored_services` rule, or delete services outright. A
confused-deputy / policy-bypass issue rather than an escalation: the user does hold
`to_ignored`, whose stated purpose is disabling services. But an administrator revoking "Manage
services" reasonably expects discovery to be off-limits, and both the GUI and
`has_modification_specific_permissions` encode that reading. Ticket in §10.4.

**P-F2 — GUI degrades, REST rejects.** On pre-gate failure the GUI rewrites the action to
`DiscoveryAction.NONE` and still returns a result (`wato/pages/services.py:411-416`) — the code even
says so: _"If the user has the wrong permissions, then we still return a discovery result which is
different from the REST API behavior."_ `execute_service_discovery` raises `403`.

> **Reviewer disposition: closed, no action.** The REST behaviour (`403`) is the correct one, and the
> GUI that degrades is deleted at the end of the epic. The new frontend inherits the `403`; there is
> nothing to reconcile.

**P-F3 — `clear_discovery_failed` costs almost nothing (the write is guarded), but it can raise after
the discovery has already been written, and one endpoint never clears the flag at all.**
✅ _verified against the code_

First, what the flag is, since it is obscure: `discovery_failed` is the host attribute stored under
the legacy name **`inventory_failed`**. It is set by **bulk discovery only** — the single producer in
the product is `bulk_discovery.py:569-573` — and it is purely cosmetic: a warning icon plus tooltip in
the folder host list (`wato/pages/folders.py:1368-1372`), a CSS class for JS bulk-select, and bulk
discovery's _"Only include hosts that failed on previous discovery"_ filter. It is never read by
`cmk/base` and has nothing to do with the "Check_MK Discovery" service.

**The write is guarded, so the cost is near zero.** `set_discovery_failed(False)` is guarded
(`hosts_and_folders.py:4033-4047`):

```python
elif self.attributes.get("inventory_failed"):
    del self.attributes["inventory_failed"]
    self.folder().save_hosts(...)
```

The `hosts.mk` write happens **only when the attribute is actually set**. For a user clicking around a
discovery page the number of writes is **zero**; for a previously-flagged host it is exactly **one**,
on the first `perform_*`, after which the attribute is gone. That write produces no pending change and
no audit entry. The accurate characterization is therefore _a conditional write, guarded on the flag
being set; a no-op on virtually every call_ — so T2.8 must assert the **guard**, not "called on every
`perform_*`".

**The `# no try/finally here.` comment is deliberate and correct.** The flag means "the last discovery
of this host failed"; if the body raised, the discovery did not succeed, so leaving it set is right. A
`try/finally` would clear it on failure — the wrong direction. Provenance: `bc53d30cfc6` converted a
decorator with the same skip-on-exception behaviour, and the comment exists to stop someone
"tidying" it.

**Two real defects remain:**

1. **`clear_discovery_failed` can raise _after_ the discovery has been written.** Its own comment says
   _"We do not check permissions. They are checked during the discovery."_ — but when the flag is set
   it reaches `Folder.save_hosts`, which does `self.permissions.need_permission("write", ...)`
   (`hosts_and_folders.py:1652`). Folder `write` needs `wato.all_folders` or contact-group membership;
   the discovery page needs only host `read` plus `wato.services`. So a user with
   `wato.services` + `wato.see_all_folders` who is not a folder contact gets a
   "no permissions to the folder" error **after** `set_autochecks_v2` has run and the change is
   recorded. Ticket in §10.9.
2. **The asymmetry is confirmed and does bite.** `update_service_phase` never enters the context
   manager, so it never clears the flag — even though it runs a full `get_check_table` preview and
   succeeds. A host flagged by a failed bulk discovery stays flagged **indefinitely** for a client
   that only uses that endpoint, so bulk discovery's "only failed hosts" set never converges. Ticket
   in §10.9.

Structural note for the rewrite: `_service_discovery_context` is not really a context manager —
nothing is acquired or released, the `yield` is unguarded, and the exit does an unrelated side effect.
Two statements in a `@contextmanager` costume, which is precisely why `update_service_phase` misses
both of them (P-F1 and this).

### 5.2 REST `update_service_phase` accepts 17 target phases

`UpdateDiscoveryPhaseModel.target_phase` is a `Literal` of all 17 `SERVICE_DISCOVERY_PHASES` keys.
Only 4 (`monitored`, `undecided`, `ignored`, `removed`) correspond to the GUI's `UpdateType`. The
other 13 route into the `other` column of §4 — mostly "drop the service, demand nothing". The
endpoint's four blanket `need_permission` calls mean a caller must hold all four
`wato.service_discovery_to_*` permissions, which masks A2-F1 for this endpoint specifically, but the
`Discovery` class itself provides no protection. ⚠️

**The honest target count is 3, and narrowing the enum is necessary but not sufficient.** `undecided`
and `removed` are two labels for one command (`drop`, §11.1), so the vocabulary is
`monitored` / `ignored` / `drop`. And validity is a property of the `(source, target)` **pair**, not of
the target alone: all three are invalid for a `vanished` service except `drop` (A2-F6), and all three are
invalid for a `manual`/`active`/`custom` row or for a row whose effective host is a cluster (A2-F7). The
endpoint has the source available — it already fetches the check table — so it can validate the pair and
answer `400`. §11.2 plus §11.2a's four rules is what to validate against.

---

## 6. Matrix B — host/job level (the 5 uniform columns, plus what `perform_*` does around the cells)

### 6.0 What this section is for, and the mechanics it depends on

§3–§5 characterize what happens to an _individual service_. But 5 of the 12 actions (`NONE`,
`STOP`, `REFRESH`, `TABULA_RASA`, `UPDATE_HOST_LABELS`) never touch a service's state at all, so a
per-cell grid for them would be 75 identical "nothing happens" cells. What they _do_ affect is the
host: whether a scan is started, whether the agent is contacted, whether host labels are written,
and which pending changes appear. That is what this section pins. It also records the wrapper
behaviour that the `perform_*` functions add _around_ the per-service cells.

Four mechanics are needed to read the table. All four are things the rewrite has to preserve or
deliberately change, which is why they are here rather than left implicit:

**1. There is a background job, it always runs on the site that owns the host, and it is public REST
surface.** `ServiceDiscoveryBackgroundJob` (`services.py:1312`) is the only thing that calls
`local_discovery_preview`. Its docstring says it plainly: _"The background job is always executed on
the site where the host is located on."_ Only two actions start it — `REFRESH` and `TABULA_RASA`
(`execute_discovery_job`, `services.py:1275-1281`). Every other action reads whatever the job left
behind.

It is not merely a GUI mechanism. The job is exposed as its own REST domain type,
`service_discovery_run`, with three published behaviours:

| endpoint                                | behaviour                                                                                                                                                                                                                                               |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `show_service_discovery_run`            | returns the job's status and log for a host                                                                                                                                                                                                             |
| `wait_for_service_discovery_completion` | `302` redirect **to itself** while `snapshot.is_active`, `204` when finished, `404` when no job exists                                                                                                                                                  |
| `execute_service_discovery`             | modes `refresh` / `tabula_rasa` raise `RedirectException` → **`303`** to `cmk/wait-for-completion` instead of returning a result body (`execute_service_discovery.py:164`); every other mode is refused with **`409`** while a job is active (`:95-97`) |

Consequence for the rewrite: the job cannot simply be deleted, because those three are versioned API
promises. What _can_ change is everything that depends on the job without needing one — see §6.3.

**2. `prevent_fetching` decides whether the host is contacted.**
`local_discovery_preview(..., prevent_fetching=True)` computes the check table from Checkmk's
_cached_ agent output — fast, no network. `prevent_fetching=False` actually contacts the host.
`ServiceDiscoveryBackgroundJob.discover` passes `prevent_fetching=False` only for `REFRESH` and
`TABULA_RASA` (`services.py:1367-1370`); everything else gets `True`. This is why the docs say the
non-job REST modes "only work with scanned data, so you may need to run `refresh` first" — and why
a never-scanned host yields an empty table (the cold-cache hole that CMK-35050 owns).

**3. Two independent write paths exist.** Most actions write services through
`set_autochecks_v2` (the `Discovery` path, §4). `TABULA_RASA` instead calls `local_discovery`, a
completely different automation that does its own add/remove/update inside `cmk/base`. So "accept
everything" is implemented twice, by different code, with different semantics (A3-F2).

**4. Central vs remote.** In a distributed setup, configuration lives on the **central** site and
monitoring runs on **remote** sites. The GUI the user clicks is central; the host's agent output,
autochecks file and background job are remote. `automation_config` is the object that decides which
side a given automation executes on: `LocalAutomationConfig` means "run here",
`RemoteAutomationConfig` means "HTTP to that site". Every row's last column says what that split
means for the action.

**5. Every read goes through the job object, whether or not a job runs.** There is no way to ask for
the check table without constructing a `ServiceDiscoveryBackgroundJob` and calling `get_result`
(`services.py:1309`, `:1419`) — including from REST, where `update_service_phase` and all five
synchronous `execute_service_discovery` modes reach it via `get_check_table`. `get_result` has three
branches:

| condition               | table returned                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------ |
| job active              | `self._pre_discovery_preview`                                                                                      |
| a stored preview exists | `check_table.mk`, **read once and then deleted** (`_load_last_preview` unlinks in a `finally`, `services.py:1362`) |
| otherwise               | a fresh `prevent_fetching=True` preview                                                                            |

Two properties of that arrangement matter later. The stored preview is a _second_ cache layer on top
of Checkmk's own fetcher cache, and a destructive one — yet it is not load-bearing, because
`_perform_service_scan`'s docstring records that the scan also warms the internal cache, which is what
makes the third branch fresh. And `_pre_discovery_preview` is only ever assigned inside `discover()`
(`services.py:1367`), which runs in the _job_ process; in the requesting process the attribute keeps
the empty value built by `__init__` (`services.py:1332`, `check_table=[]`). So the first branch
returns an empty table to whoever asked. That is B-F3.

| action                                                                                                                                        | job started                | `local_discovery_preview` calls                                    | `local_discovery`                         | host labels written                                        | pending changes added                                                 | local vs remote                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------ | ----------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `NONE`                                                                                                                                        | no                         | 1 × `prevent_fetching=True`                                        | no                                        | no                                                         | none                                                                  | **branch** (see B-F1)                                                           |
| `STOP`                                                                                                                                        | no; `job.stop()` if active | 1 × `prevent_fetching=True`                                        | no                                        | no                                                         | none                                                                  | branch; `stop()` targets the job on the host's site                             |
| `REFRESH`                                                                                                                                     | **yes**                    | job: 1 × `prevent_fetching=False`, result stored; then 1 × on read | no                                        | no                                                         | none                                                                  | job runs on host's site                                                         |
| `TABULA_RASA`                                                                                                                                 | **yes**                    | job: 1 × `prevent_fetching=False` pre-read                         | **yes**, all settings `True`, `scan=True` | yes (via `local_discovery`)                                | **`refresh-autochecks`, added on the central site before the branch** | ⚠️ B-F2                                                                         |
| `UPDATE_HOST_LABELS`                                                                                                                          | no                         | 1 × on final read                                                  | no                                        | **yes**, `update_host_labels` per host in `labels_by_host` | `update-host-labels` per host                                         | `update_host_labels(automation_config, …)` dispatches                           |
| `FIX_ALL`                                                                                                                                     | no                         | 1 × on final read (+1 if no previous result)                       | no                                        | **yes**, before `do_discovery`                             | `update-host-labels` per host; `set-autochecks` iff transition        | `set_autochecks_v2` / `update_host_labels` / `get_services_labels` all dispatch |
| `UPDATE_SERVICES`, `BULK_UPDATE`, `SINGLE_UPDATE`, `SINGLE_UPDATE_SERVICE_PROPERTIES`, `UPDATE_SERVICE_LABELS`, `UPDATE_DISCOVERY_PARAMETERS` | no                         | 1 × on final read (+1 if no previous result)                       | no                                        | no                                                         | `set-autochecks` iff transition                                       | ditto                                                                           |

### 6.1 Local / remote

#### Where the branch is

There is exactly **one** explicit local/remote branch in `services.py`, in `get_check_table`
(`services.py:1209-1241`):

```
LocalAutomationConfig  → execute_discovery_job(host_name, action, …)   # run the job in-process
otherwise              → sync_changes_before_remote_automation(site)   # ⚠️ activates pending changes
                         do_remote_automation(cfg, "service-discovery-job", …)
                         DiscoveryResult.deserialize(...)              # ⚠️ lossy, see B-F2.3
```

On the remote side that HTTP call lands in `AutomationServiceDiscoveryJob.execute`
(`wato/pages/services.py:369-378`), which calls the _same_ `execute_discovery_job` — so the remote
path is the local path with a serialization hop and a second permission check in front of it.

All the **write** paths dispatch differently: they take `automation_config` as a parameter and pass
it straight to `_automation_serialized`, which does the `isinstance` check
(`check_mk_automations.py:60`). That covers `set_autochecks_v2`, `update_host_labels` and
`get_services_labels`.

#### B-F1 — the read path cannot be redirected, and that is a testing trap

`local_discovery` and `local_discovery_preview` **hard-code `LocalAutomationConfig()`**
(`check_mk_automations.py:146` and `:222`). They take no `automation_config` argument at all. That is
correct by construction — they only ever run inside the background job, which is already on the
right site — but it has a consequence for tests:

> Patching `local_discovery_preview` does not merely stub the read. Because the remote branch
> reaches it only _via_ `do_remote_automation` → `AutomationServiceDiscoveryJob` → `execute_discovery_job`,
> a patch installed in the central process makes the remote branch return locally-computed data
> without ever crossing a site boundary. **The remote branch is not skipped; it is silently replaced
> by the local one.**

This is the mechanism behind the AC's rule _"Tests do not monkeypatch `local_discovery_preview` in a
way that bypasses the local/remote dispatch branch"_, and it is how the hackathon PoC shipped an
apply path that was unconditionally local — its tests could not have caught it. Both existing test
suites do exactly this: `tests/unit/cmk/gui/watolib/test_services.py:116-120` and
`tests/openapi/test_openapi_service_discovery.py:1632-1636`.

The fix for new tests is to patch one level lower, at the automation transport
(`check_mk_local_automation_serialized` / `check_mk_remote_automation_serialized`, or
`_automation_serialized`), and to parametrize `automation_config`. Then "which site did this go to"
becomes an assertable fact instead of an assumption. That is what Tier 2 of §7 does.

#### B-F2 — five ways the two paths differ

Each is stated with the user-visible consequence, because "local and remote differ" is only
actionable if you know what breaks.

1. **The remote path activates pending changes first; the local path does not.**
   `sync_changes_before_remote_automation` (`services.py:1218`) runs before the automation.
   _Consequence:_ clicking "Rescan" on a remote host can activate an unrelated, half-finished
   configuration change that the admin had not intended to activate yet. On a local host the same
   click activates nothing.
2. **`TABULA_RASA`'s pending change is recorded centrally, but the work happens remotely.**
   The `refresh-autochecks` change is added before the branch (`services.py:1196-1207`), while
   `_perform_automatic_refresh` runs `local_discovery` on the remote site and records nothing there —
   an acknowledged `TODO` at `services.py:1398`: _"In distributed sites this must not add a change on
   the remote site. We need to build the way back to the central site and show the information
   there."_
   _Consequence:_ the central change list says "Refreshed check configuration", but the audit trail
   for what actually changed on the remote is absent.
3. **The wire format is version-truncated.** `DiscoveryResult.serialize(for_cmk_version)`
   (`services.py:169-198`) sends only the first 10 fields to a peer `< 2.5.0b1` — dropping
   `config_warnings` — and encodes `sources` as an index-keyed dict for a peer `< 3.0.0b1`.
   _Consequence:_ against an older remote, the discovery page silently shows no configuration
   warnings. Within the supported one-minor-version skew this is reachable, not theoretical.
4. **Permissions are checked twice, with different sets.** Centrally:
   `has_discovery_action_specific_permissions` plus `_service_discovery_context`'s `wato.services`.
   Remotely: `AutomationServiceDiscoveryJob._check_permissions` (`wato/pages/services.py:350-365`),
   which requires only `wato.hosts` and host `read`.
   _Consequence:_ the effective permission set for a remote host is the central one; the remote check
   is a weaker backstop, not an equivalent gate. Any new endpoint must not assume the remote
   re-validates what the central checked.
5. **Disabling a service is inherently cross-site.** The `ignored_services` rule is written into the
   **central** WATO config by `EnabledDisabledServicesEditor`, but the `get_services_labels` call it
   uses to decide whether a host-specific rule is still needed (`rulesets.py:1919-1921`) is an
   automation **dispatched to the remote**.
   _Consequence:_ one logical operation spans both sites, and the rule only takes effect on the
   remote after activation. A batch-apply endpoint that reports "done" before activation is
   reporting something different for disable than for the other dispositions.

### 6.2 The job as the read path

#### B-F3 — DEFECT: a write issued while a scan is running is answered `204` and changes nothing

✅ _verified against the code_

The concurrency policy is implemented in exactly one place. `execute_service_discovery` probes
`job_snapshot(host, …).is_active` and answers `409` (`execute_service_discovery.py:95-97`).
`update_service_phase` performs no such check — it goes straight to `get_check_table` and
`Discovery(...).do_discovery(...)`.

By mechanic 5, while a job is active `get_result` returns `self._pre_discovery_preview`, which in the
requesting process is the empty preview from `__init__`. So the write path receives
`check_table=[]`, and the consequences follow mechanically:

1. `compute_discovery_transition` iterates an empty table, so `apply_changes` is never set;
2. `if not apply_changes: return None` (`services.py:393`);
3. `do_discovery` returns without writing anything;
4. the endpoint answers **`204 No Content`**.

The requested change is silently discarded. Nothing is corrupted — the `apply_changes` guard is what
prevents a rebuild-from-scratch against an empty table from deleting every service on the host, which
is the outcome §1's rule would otherwise produce — but the caller is told the operation succeeded.

**Reproduction.** Start `POST .../service_discovery/actions/discover/invoke` with `mode: "refresh"`
on a host slow enough to keep the job alive (or any SNMP host), and while the job runs issue
`PUT /objects/host/<host>/actions/update_discovery_phase/invoke` with a valid service and
`target_phase: "monitored"`. Expected: `409`, or the change applied. Actual: `204`, and
`var/check_mk/autochecks/<host>.mk` is untouched.

**Severity: low.** It needs a concurrent scan, and it loses a request rather than data. It is listed
because the fix is nearly free and because it demonstrates the general problem: _job-active_ is being
used as a proxy for _the table you decided against is still current_, in one entry point out of two.
Probing the job cannot cover the other case at all — a user acting on a page rendered ten minutes ago
gets no error from either endpoint. The mechanism that covers both is a precondition on the table the
decision was made against: `DiscoveryResult.check_table_created` already exists, is already sent to
the client, and is never used this way (§11.4; domain model §9.4). Ticket in §10.18.

### 6.3 Consequences for the rewrite

§6.0–§6.2 characterize mechanics; this subsection states what follows for the rewrite, so that the
conclusions are not left to be re-derived. The question it answers: _can the background job go away,
and if not, do `REFRESH` and `TABULA_RASA` warrant being special-cased?_

**The job stays, but only one of its four current jobs is essential.**

| what the job provides                                                       | needed? | why                                                                                                  |
| --------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| asynchronous execution of a **fetching** scan                               | **yes** | contacting a host outlives any request timeout; an SNMP walk can take minutes                        |
| a published async resource (`service_discovery_run`, `wait-for-completion`) | **yes** | mechanic 1: versioned API promises. It is the _scan's_ status, though, not discovery's               |
| the read path for actions that start no job                                 | no      | mechanic 5. Accidental: the job object is simply the only holder of `local_discovery_preview`        |
| per-host mutual exclusion                                                   | no      | B-F3: the wrong lock, applied in one of two entry points. Superseded by a table-version precondition |

**What is essential is a property of `prevent_fetching`, not of the two action names.** The action
enum decides the boolean in two places (`services.py:1368`, and `discover`'s `if/elif/else` at `:1372-1381`),
which is the whole of "`REFRESH` is special": it is the action for which fetching is on. Make the
fetch policy an explicit parameter of a scan request and the special case has nothing left to attach
to — no per-service operation needs to know the policy exists.

**`TABULA_RASA` is a different kind of special, and it decomposes rather than moving.** It is a scan
_plus_ a full change plan, and the plan half runs inside the job through a second write path
(`local_discovery` in `cmk/base`, not `set_autochecks_v2` — A3-F2). Splitting it into
`Scan(fetch)` **▸** `ChangePlan[…]` (domain model §7) leaves only the scan half needing the job and
deletes, in one move: the second write path, the divergence between the two implementations of
"accept everything", and B-F2.2's central-change/remote-work split — the `refresh-autochecks` change
exists before the branch precisely because the job writes configuration, and a scan that only
observes needs no pending change at all.

**Two things follow for the read model.** `job_status` and `check_table_created` leave
`DiscoveryResult` (they describe a scan, not a table — the conflation named in domain model §1), and
with them goes the laundering in `_cleaned_up_status` (`services.py:1463`), which exists only because
a caller that started no job can otherwise be handed a previous job's exception. `NONE` becomes a
plain read of the table and `STOP` becomes a call on the scan resource, so both leave the action
vocabulary entirely.

**The option that was considered and rejected: no job anywhere.** If the discovery page never fetched,
and freshness came only from the cached agent output the regular check cycle already produces, then
nothing here would need to be asynchronous: no job, no lock, no status in the read model, and
`prevent_fetching` would disappear rather than become a parameter. It is rejected because it removes
"add a host, scan it immediately, accept the services" — the primary onboarding workflow, and the one
case where the user has no cached data to fall back on. Recorded because the reasoning is otherwise
invisible: the job survives on the strength of one workflow, not because discovery is inherently
asynchronous.

---

## 7. Proposed tests

Four tiers. Tiers 1–2 are bazel unit targets under `//tests/unit/cmk/gui/watolib`; tier 3 is
`tests/openapi/` (runs via `tests/run_tests.sh`, **not** bazel); tier 4 is
`tests/run_tests.sh test-system-multisite`.

### 7.0 Existing coverage — and why it did not catch A2-F2

| file                                              | shape                                                                                             | limitation                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `tests/unit/cmk/gui/watolib/test_do_discovery.py` | **an existing `(source, target)` matrix** over `_apply_state_change`, 15 × 15 expected-value dict | tests **53%** of the matrix — see below           |
| `tests/unit/cmk/gui/watolib/test_services.py`     | ~2400 lines, ~20 scenario tests                                                                   | no matrix; mocks `local_discovery_preview` (B-F1) |
| `tests/openapi/test_openapi_service_discovery.py` | ~2100 lines                                                                                       | mocks `local_discovery_preview` throughout (B-F1) |

**A matrix test already exists, and it silently covers a little over half the matrix.** Its driver is:

```python
def _get_combinations() -> list:
    states = [value for state, value in vars(DiscoveryState).items() if state.isupper()]
    return list(itertools.combinations_with_replacement(states, 2))
```

`combinations_with_replacement` yields **unordered** pairs — 120 of the 225 ordered
`(source, target)` combinations. Which 120 depends on the _declaration order_ of the attributes in
`DiscoveryState`. The assertion is
`known_results.get((source, target), empty_result) == result`, so any pair the generator never
produces is never asserted at all.

The 105 missing cells are not the boring ones. Every "accept" and every "re-enable" transition is
in the untested half:

| untested transition   | meaning                                                                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `changed → unchanged` | **accept new service properties** — the core transition of the whole feature                                                            |
| `ignored → unchanged` | re-enable a disabled service                                                                                                            |
| `ignored → new`       | declare a disabled service undecided                                                                                                    |
| `unchanged → new`     | declare a monitored service undecided                                                                                                   |
| `vanished → new`      | an **invalid** transition (A2-F6) that the code nevertheless implements as "keep" — the untested cell that should have been a rejection |
| `changed → new`       | declare a changed service undecided                                                                                                     |

Worse, `known_results` contains **dead expected-data**: the entry for
`(MONITORED, UNDECIDED)` (`test_do_discovery.py:75-80`) can never be generated by
`combinations_with_replacement`, so it looks like a pinned cell and is not one. A reader sees a
15 × 15 table and reasonably concludes the matrix is covered.

This is the guardrail illusion CMK-34150 exists to remove, and it is the direct explanation for
A2-F2 surviving werk 19800: the `(MONITORED, IGNORED)` cell _is_ in `known_results` and _is_
generated — pinning the buggy value `{MOCK_KEY: MOCK_VALUE}` — while the neighbouring cells that
would have shown the inconsistency were never run.

**Consequence for the plan:** Tier 1 **replaces** `test_do_discovery.py` rather than sitting beside
it. Two competing matrices for the same function would be worse than one. The migration is
mechanical: swap `combinations_with_replacement` for `itertools.product`, port the expected values,
and fix or delete whatever the newly-covered 105 cells reveal. Note that the three
`(*, IGNORED)` rows currently pin A2-F2's buggy behaviour, so those rows must change in the same
commit as the fix.

### Tier 1 — exhaustive matrix, pure (replaces `tests/unit/cmk/gui/watolib/test_do_discovery.py`)

`Discovery.compute_discovery_transition` takes a `DiscoveryResult` as an argument and
`user_need_permission` as a constructor parameter. **No mocking is needed at all** for this tier —
it is a pure function over a hand-built `DiscoveryResult`. Assertions are on `DiscoveryTransition`
fields (which survive the rewrite), never on `_get_table_target` or other privates.

**Tier 1 is split by verdict, not by subject.** §11 establishes that a substantial part of today's
behaviour is wrong, so pinning all of it as "expected" would bake in defects and make the suite an
obstacle to the very refactoring it exists to protect. Instead:

- **Tier 1a — conformance.** Cells where today's behaviour already matches §11.2. These are ordinary
  passing tests and they are the actual regression guardrail. They must stay green through every phase.
- **Tier 1b — quarantine.** Cells where today's behaviour contradicts §11.2. Each is written **twice**
  from one data row: an `xfail(strict=True)` test asserting the _intended_ outcome, and a plain test
  asserting the _current_ one. The first is a tripwire that fires when the behaviour is fixed; the second
  is the guardrail that holds until then. Both are deleted together when the ticket lands.

The `xfail` must carry `strict=True` **explicitly**. `pyproject.toml:15-16` does set
`xfail_strict = true`, but in a bare `[pytest]` table, which pytest does not read from `pyproject.toml` —
it reads only `[tool.pytest.ini_options]` (line 317), where the setting is absent. So the repo default is
non-strict and an XPASS would pass silently, defeating the whole mechanism. The single existing strict
xfail in the tree (`tests/unit/cmk/gui/monitor/hosts/test_sorting.py:203`) spells it out for the same
reason. Filing the dead-config cleanup separately is worthwhile, but it must not be assumed: switching
`xfail_strict` on globally changes the verdict of the other twelve `mark.xfail` uses in `tests/`, so this
tier depends on the explicit flag, not on the fix.

#### Tier 1a — conformance (must pass)

| #      | test                                             | parametrization                                                                                                            | pins                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1a.1  | `test_meaningful_cell_outcome`                   | **8 of the 10** meaningful `(state, command)` pairs of §11.2 — those with at least one realisation that is already correct | `CellOutcome(in_new_autochecks, params, labels, add_disabled, remove_disabled, need_sync, permission)`. Expected values are §11.2's, not a transcript of the code. Five pairs are wholly correct today (`new + monitor`, `new + disable`, `unchanged + drop`, `changed + drop`, `ignored + monitor`); three are correct in one realisation only and have their other realisation in 1b — `changed + monitor` (correct under the adopting actions, T1b.8), `ignored + drop` (correct via the `new` label, T1b.6), `vanished + drop` (correct via the `removed` label, T1b.5). The two remaining pairs, `unchanged + disable` and `changed + disable`, have no correct realisation and live entirely in 1b. |
| T1a.2  | `test_no_op_cells_yield_no_transition`           | 3 cells                                                                                                                    | `new + drop`, `unchanged + monitor`, `ignored + disable` ⇒ `compute_discovery_transition() is None`, no write, no permission demanded. Idempotency, which the REST `PUT` contract needs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| T1a.3  | `test_permission_demanded_per_cell`              | the 1a cells                                                                                                               | The §4 `Perm` column via a recording `user_need_permission`, **including** the cells that must demand nothing.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| T1a.4  | `test_unreachable_sources`                       | 2                                                                                                                          | `removed` ∉ `Transition`; `clustered_ignored` is not produced by `_node_service_source`/`_make_cluster_table`. Pins §2.1's unreachability claims so they cannot silently become false.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| T1a.5  | `test_matrix_is_total`                           | 1                                                                                                                          | Every `DiscoveryState` and `DiscoveryAction` member appears in the 1a table, the 1b table, or an explicit `UNREACHABLE` / `NO_PER_SERVICE_EFFECT` / `NOT_ELIGIBLE` set. **Fails when an enum value is added without a verdict.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| T1a.6  | `test_value_adoption_matrix`                     | 12 actions                                                                                                                 | §5 A3-F1, source `changed` with distinguishable old/new params and labels. The per-action adoption table is current _and_ intended behaviour — the divergence is only whether plain `monitor` should adopt, which is 1b.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| T1a.7  | `test_disabled_rule_arithmetic`                  | ~6 scenarios                                                                                                               | §4.2: the `saved_services − selected_services` term; `FIX_ALL` (`selected=()`) vs `UPDATE_SERVICES` (`selected=EVERYTHING`); `need_sync=True` with an empty final `add_disabled_rule`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| T1a.8  | `test_old_autochecks_audit_shape`                | 4                                                                                                                          | §4.2: `old_autochecks` built from `{unchanged, changed, ignored, vanished}` with **old** values.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| T1a.9  | `test_cluster_node_table_handling`               | ~6 scenarios                                                                                                               | `_get_effective_check_tables`: `found_on_nodes` filtering, "not found on any node ⇒ keep", the same action applied to node tables. Structural, not a transition verdict.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| T1a.10 | `test_has_discovery_action_specific_permissions` | 12 actions × permission sets                                                                                               | §5.1 pre-gate table; total via the existing `assert_never`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

#### Tier 1b — quarantine (each row yields one strict-xfail + one characterization test)

One parametrized table, one row per divergence, each row carrying `intended`, `current` and `ticket`:

| #      | divergence                                                 | intended (§11.2)            | current                                                                                          | ticket |
| ------ | ---------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------ | ------ |
| T1b.1  | `unchanged + disable`                                      | entry absent, rule added    | entry **written**, rule added                                                                    | §10.1  |
| T1b.2  | `changed + disable`                                        | entry absent, rule added    | entry **written**, rule added                                                                    | §10.1  |
| T1b.3  | `vanished + disable`                                       | rejected                    | entry written + rule added                                                                       | §10.16 |
| T1b.4  | `vanished + monitor`                                       | rejected                    | entry kept                                                                                       | §10.16 |
| T1b.5  | `vanished + drop` via the `new` label                      | entry dropped               | entry **kept** (only the `removed` label drops)                                                  | §10.16 |
| T1b.6  | `ignored + drop` via the `removed` label                   | rule removed, entry absent  | rule **left in place**                                                                           | §11.3  |
| T1b.7  | `new + drop` via the `removed` label                       | rejected (wrong label)      | accepted, demands `to_removed`, does nothing                                                     | §11.3  |
| T1b.8  | `monitor` on `changed` via `SINGLE_UPDATE` / `BULK_UPDATE` | adopts the requested facets | writes **old** values ⇒ returns as `changed`                                                     | A3-F1  |
| T1b.9  | any command on a non-discovered origin                     | rejected                    | `FIX_ALL` retargets to `monitored`, forcing a spurious write                                     | §10.8  |
| T1b.10 | any command on a `clustered_*` source                      | rejected with a redirect    | handled by `_case_clustered`; `disable` drops the node's entry and un-monitors it on the cluster | §10.17 |
| T1b.11 | any non-command target (13 values)                         | `400`                       | silently deletes the service, `204`, and 10 of them demand no permission                         | §10.3  |

Two properties this buys:

1. **Nothing wrong is asserted as correct.** Every 1b characterization test sits next to a test that
   states what the answer should be, in the same table, with a ticket reference.
2. **The scaffolding removes itself.** When a ticket lands, its `xfail` test XPASSes and — because
   `strict=True` — the suite goes red until someone deletes the marker and the paired characterization
   row. There is no way to fix a defect and leave stale expectations behind, which is exactly how A2-F2
   survived werk 19800 (§7.0).

A single `_expect` helper generating both tests from one row keeps this at one edit per ticket.

### Tier 2 — side effects and local/remote dispatch (new file: `tests/unit/cmk/gui/watolib/test_services_dispatch.py`)

**Every test parametrized over `automation_config ∈ {LocalAutomationConfig(), RemoteAutomationConfig(...)}`,
patching only the automation transport** — never `local_discovery_preview` (B-F1).

| #     | test                                               | pins                                                                                                                                                                                                                                                                                                             |
| ----- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T2.1  | `test_get_check_table_dispatch`                    | Local → `check_mk_local_automation_serialized("service-discovery-preview", …)`. Remote → `sync_changes_before_remote_automation(site_id)` **then** `do_remote_automation(cfg, "service-discovery-job", [host_name, options])` with the exact options payload, and the result is the deserialized remote payload. |
| T2.2  | `test_write_paths_use_the_given_automation_config` | **The PoC's worst defect.** `set_autochecks_v2`, `update_host_labels` and `get_services_labels` all receive the _same_ `automation_config` that was passed to `perform_*`. Fails if any write path is hard-coded local.                                                                                          |
| T2.3  | `test_tabula_rasa_pending_change_is_central`       | B-F2.2: `refresh-autochecks` added before the branch, scoped to the host's site; no equivalent remote change.                                                                                                                                                                                                    |
| T2.4  | `test_remote_sync_only_on_remote`                  | B-F2.1: `sync_changes_before_remote_automation` called exactly once on remote, never on local.                                                                                                                                                                                                                   |
| T2.5  | `test_job_lifecycle_per_action`                    | §6 Matrix B row-by-row: which actions start the job, which call `job.stop()`, `prevent_fetching` per call, and that only `TABULA_RASA` reaches `local_discovery` (with all five `DiscoverySettings` flags `True`).                                                                                               |
| T2.6  | `test_discovery_result_wire_round_trip`            | B-F2.3: `serialize`/`deserialize` for `2.4.0`, `2.5.0b1`, `3.0.0b1` peers — field truncation and the `sources` dict/list shape.                                                                                                                                                                                  |
| T2.7  | `test_pending_changes_recorded`                    | Change `action_name`, `object_ref`, domains, `force_sync` (from `need_sync`) and site scope for `set-autochecks`, `update-host-labels`, `refresh-autochecks`.                                                                                                                                                    |
| T2.8  | `test_service_discovery_context_side_effects`      | P-F3: `wato.services` demanded; `clear_discovery_failed` called for unlocked hosts, skipped for locked ones, on every `perform_*` including no-ops.                                                                                                                                                              |
| T2.9  | `test_discovery_used_directly_skips_context`       | P-F1: `Discovery(...).do_discovery(...)` (the `update_service_phase` shape) does **not** demand `wato.services` and does **not** clear `discovery_failed`.                                                                                                                                                       |
| T2.10 | `test_fix_all_updates_host_labels_before_services` | Ordering: labels are written even when the transition is `None` (already covered by one existing test — fold it in).                                                                                                                                                                                             |
| T2.11 | `test_read_during_active_job_yields_empty_table`   | Mechanic 5 / B-F3: with `is_active()` patched `True`, `execute_discovery_job` returns `check_table == []` and `check_table_created == 0`, and `Discovery(...).do_discovery(...)` against that result calls **no** write automation. Pins the silent no-op until §10.18 replaces it with a rejection.             |

### Tier 3 — REST characterization (extend `tests/openapi/test_openapi_service_discovery.py`)

| #    | test                                                         | pins                                                                                                                                                                                                                                                                                                                              |
| ---- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T3.1 | `test_api_mode_matrix` — 7 modes                             | Per mode: resulting `check_table` phases, whether `set_autochecks_v2` was called and with what. Explicitly pins **`only_service_labels` accepting undecided services and keeping vanished ones** (A1-F2) and **`new`/`remove` not adopting new parameters** (A3-F1).                                                              |
| T3.2 | `test_update_service_phase_target_matrix` — 17 target phases | §5.2 / A2-F1: the resulting autochecks for each accepted `target_phase`, incl. the `legacy`, `manual`, `active`, `custom` drop cells. Parametrize the source too, at least `unchanged` and `vanished`, so the pair-validity gap (A2-F6) is visible: the same `target_phase` deletes for one source and writes-back for the other. |
| T3.3 | `test_update_service_phase_permissions`                      | The four blanket `need_permission` calls, and that `Discovery` itself adds none for the `other` targets.                                                                                                                                                                                                                          |
| T3.4 | `test_execute_discovery_conflicts_with_running_job`          | `409` from `job_snapshot(...).is_active`.                                                                                                                                                                                                                                                                                         |
| T3.5 | `test_refresh_and_tabula_rasa_redirect`                      | `303` to `wait-for-completion` instead of a result body.                                                                                                                                                                                                                                                                          |
| T3.6 | `test_update_service_phase_during_active_job`                | B-F3: **`204` and no autochecks write** while a job is active — the asymmetry against T3.4's `409`. Becomes the assertion for §10.18 by changing the expected status.                                                                                                                                                             |

### Tier 4 — remote-site parity (new file: `tests/system/multisite/cmk/gui/test_service_discovery_remote_parity.py`)

Uses the existing `central_site` / `remote_site` session fixtures. One identically-configured host
per site (same agent output, so the same preview), everything driven through the REST API **on the
central site**. `ServiceDiscoveryAPI` in `tests/testlib/openapi_session.py` already has
`run_discovery`, `run_discovery_and_wait_for_completion` and `get_discovery_result`; an
`update_service_phase` helper needs adding there (and in `tests/testlib/rest_api_client.py`, which
has no method for it either).

| #    | test                                                                       | pins                                                                                                                                                                                                                                                                |
| ---- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T4.1 | `test_mode_parity[7 modes]`                                                | Identical resulting discovery result for the local-site and remote-site host. **This is the AC's "every action is exercised against a host on a remote site".**                                                                                                     |
| T4.2 | `test_autochecks_written_on_the_owning_site`                               | `var/check_mk/autochecks/<host>.mk` changes on the **remote** site and **not** on the central. Direct regression test for the PoC's worst defect.                                                                                                                   |
| T4.3 | `test_disabled_services_rule_is_central_and_activates`                     | `ignored → unchanged` and `unchanged → ignored` on a remote host: the `ignored_services` rule lands in the central config and takes effect on the remote after activation.                                                                                          |
| T4.4 | `test_update_service_phase_parity[monitored, undecided, ignored, removed]` | The second entry point, remotely.                                                                                                                                                                                                                                   |
| T4.5 | `test_refresh_and_tabula_rasa_parity`                                      | Background job runs on the remote; central sees status; `refresh-autochecks` change appears centrally (B-F2.2).                                                                                                                                                     |
| T4.6 | `test_host_label_parity`                                                   | `only_host_labels` writes discovered host labels on the remote.                                                                                                                                                                                                     |
| T4.7 | `test_cluster_parity`                                                      | A cluster whose nodes live on the remote site: node-table handling (T1a.9) end-to-end.                                                                                                                                                                              |
| T4.8 | _(reserved)_ SUP-derived scenarios                                         | **Input needed.** The ticket names SUP-28115 / SUP-28119 / SUP-28127 / SUP-28128 as real-world cases to cover. Those are customer tickets, not readable from this repository; their reproduction shapes must be extracted by hand and each turned into a case here. |

**Not proposed:** `test-system-gui` coverage. The AC excludes the AJAX transport and
`DiscoveryPageRenderer`, and both are deleted in Phase 5; pinning them is wasted work.

### Volume

| tier | files                 | test functions                       | generated cases | speed                                       |
| ---- | --------------------- | ------------------------------------ | --------------- | ------------------------------------------- |
| 1a   | 1 new                 | 10                                   | ~120            | fast, pure                                  |
| 1b   | same file, own module | 2 (table-driven, 11 rows ⇒ 22 cases) | ~22             | fast, pure; 11 of them `xfail(strict=True)` |
| 2    | 1 new                 | 11                                   | ~27             | fast, mocked at the transport               |
| 3    | extend 1              | 6                                    | ~36             | medium                                      |
| 4    | 1 new                 | 7 (+ reserved)                       | ~20             | slow, real sites                            |

---

## 8. Summary of findings, for triage

`⚠️` cells are behaviour, not bugs-to-fix-now. Each needs a disposition in the Phase 2 contract.
The **Status** column reflects the 2026-08-14 review; see §9 for detail.

| ID    | Finding                                                                                                                                                                                                                                         | Consequence for the rewrite                                                                                                                                              | Status                                                                      |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| A1-F1 | `FIX_ALL` retargets **11 of 13** sources to `unchanged`; the guarding comment is false and never was true (since 2020)                                                                                                                          | Spurious pending change + automation round trip per click on most real hosts; silently prunes enforced-shadowed autochecks                                               | ✅ **confirmed** → §10.8                                                    |
| A1-F2 | `UPDATE_SERVICE_LABELS` / `UPDATE_DISCOVERY_PARAMETERS` ignore **`update_source`** (not `selected_services` — host-wide scope is intended)                                                                                                      | Accepts every undecided service on the host; unfixed remainder of werk 17711                                                                                             | ✅ **confirmed defect** → §10.5                                             |
| A1-F3 | `FIX_ALL` ≠ `UPDATE_SERVICES` (adoption + disabled-rule arithmetic)                                                                                                                                                                             | Two "accept" semantics; batch-apply must pick one                                                                                                                        | open                                                                        |
| A1-F4 | The alias is correct and disclosed ("including changed" in both titles); `changed` really is a subset of monitored                                                                                                                              | Alias is fine; the asymmetry surfaces as dead `bulk_changed_*` enables                                                                                                   | ✅ **not a defect**; separate bug → §10.7                                   |
| A2-F1 | Permission half is **not exploitable today** (the only caller demands all four); data-loss half is **real** — 13 of 17 `target_phase` values delete a service and return `204`, and 10 of the 17 demand no permission                           | Latent authz hole that goes live with a second caller                                                                                                                    | ✅ **verified, split verdict** → §10.3                                      |
| A2-F2 | **werk 19800 gap:** `unchanged`/`changed` → `ignored` still write the service to autochecks; only the `ignored` and `clustered_*` sources were fixed                                                                                            | Autochecks residue — entries for services a "Disabled services" rule matches — accumulating on hosts with volatile services                                              | ✅ **confirmed defect** → §10.1                                             |
| A2-F3 | **No inconsistency exists** — `unchanged` is the only source for which `undecided` is a valid target; the two apparent disagreements (`vanished`, `clustered_*`) are invalid transitions                                                        | An apparent inconsistency in a transition table is a symptom of cells that should be rejections                                                                          | ✅ **verified — not a defect**; splits into A2-F6 / A2-F7                   |
| A2-F4 | `_case_vanished`'s `else` keeps the service for every unlisted target, so `removed` is the only target that cleans up                                                                                                                           | **No data harm** — the write is value-identical (`older is newer` for vanished rows), so nothing is resurrected; the effect is a failure to clean up                     | ✅ **verified — not a defect**                                              |
| A2-F5 | **No gap on GUI paths** — `may_edit_ruleset("ignored_services")` is `wato.services or wato.rulesets`, already guaranteed by `_service_discovery_context`. The real gap is the REST endpoint (= P-F1)                                            | Vacuous on GUI paths                                                                                                                                                     | ✅ **verified — not a defect**; folded into §10.4                           |
| A2-F7 | **No operation on a `clustered_*` row is valid on the node** — the service is owned by the cluster. The GUI honours this (no bulk actions, no row buttons); `_verify_permissions`, `_apply_state_change`, REST and the host-wide actions do not | `clustered_* → ignored` drops the node's entry with no rule, silently un-monitoring the service **on the cluster** until the next node discovery                         | ✅ **confirmed defect** → §10.17                                            |
| A2-F6 | **`removed` is the only valid target for `vanished`** — `ignored`, `undecided` and `monitored` name states the classifier cannot produce for a not-discovered service, yet the GUI offers `ignored` in two places and REST offers all three     | `vanished → ignored` writes the service back with a rule attached, creating inescapable residue; the fix is withdrawal, not repair                                       | ✅ **confirmed defect** → §10.16                                            |
| A3-F1 | `SINGLE_UPDATE` / `BULK_UPDATE` / `UPDATE_SERVICES` don't adopt new params or labels                                                                                                                                                            | **The exact PoC downgrade.** Batch apply must state its side                                                                                                             | **intended** — contract input                                               |
| A3-F2 | `TABULA_RASA` is a second, independent "accept everything"                                                                                                                                                                                      | Story F2                                                                                                                                                                 | **intended** — revisit after epic                                           |
| P-F1  | `update_service_phase` bypasses `wato.services` **and** `wato.edit`, and requires only host _read_ on a mutating `PUT`                                                                                                                          | A role denied "Manage services" can still write `ignored_services` rules and delete services                                                                             | ✅ **confirmed authz gap** → §10.4                                          |
| P-F2  | GUI degrades permission failure to `NONE`; REST returns `403`                                                                                                                                                                                   | REST is correct; GUI is deleted                                                                                                                                          | **closed**                                                                  |
| P-F3  | `clear_discovery_failed` is **guarded**, so it costs near nothing. But it can raise _after_ the write, and `update_service_phase` never clears the flag                                                                                         | Stale "discovery failed" icon; bulk-discovery retry set never converges                                                                                                  | ✅ **verified**; not a cost issue, 2 real defects → §10.9                   |
| C-F1  | `clustered_ignored` has had no producer since `692c918bf86` (2021-02-05) — an early `return "ignored"` replaced a mutate-then-prefix, reverting werk 7128                                                                                       | Disabled clustered services misfiled on the node with bulk actions enabled, and shown as `vanished`/absent on the cluster; re-enabling from the node silently fails      | ✅ **confirmed regression** → §10.13                                        |
| C-F2  | `ignored_active` / `ignored_custom` were unrenderable GUI values from `35b96ecaeb9` (2021-11-11) until werk 18136 (2025-10-09, 2.5.0b1) — producer and consumer spelled the two halves in opposite order                                        | Third cross-boundary string mismatch to survive years unnoticed; concealed N-F1 for four years; the concrete case for §10.12                                             | ✅ **fixed upstream** — precedent, no ticket                                |
| N-F1  | The Nagios config writer applies no "Disabled services" / `effective_host` filter to `custom_checks`; the omit call was deleted in passing by werk 10883 (`cbbcad6fb5f`, 2020-04-09). CMC is unaffected                                         | A service the discovery page files under "Disabled custom checks" keeps being checked and keeps notifying on every Nagios-core site                                      | ✅ **confirmed regression** → §10.15                                        |
| L-F1  | `legacy` / `legacy_ignored` are fossils of `legacy_checks` (removed in 1.6, werk 7342), still published in the v1 REST `target_phase` enum                                                                                                      | Two of the 13 destructive values in §10.3                                                                                                                                | ✅ **confirmed** → §10.14                                                   |
| Q-F1  | Quick setup passes `LocalAutomationConfig()` to `perform_fix_all` while deriving the real config for the read                                                                                                                                   | Remote-site hosts get autochecks written on the **central** site — the PoC's worst bug, in surviving production code                                                     | ✅ **confirmed defect** → §10.10                                            |
| R-F1  | All writing REST modes pass `selected_services=EVERYTHING`, collapsing the duplicate-service guard term to ∅                                                                                                                                    | Spurious `ignored_services` rule for plugin-disabled services                                                                                                            | ⚠️ confirmed in part; `ignored_checks` sub-case needs a live check → §10.11 |
| T-F1  | `test_do_discovery.py`'s matrix uses `combinations_with_replacement`, covering 120 of 225 cells; the untested half contains every "accept" and "re-enable" transition, and some `known_results` rows are unreachable dead data                  | Explains how A2-F2 survived werk 19800; Tier 1 must replace this file, not extend it                                                                                     | ✅ **confirmed** → §7.0                                                     |
| B-F1  | `local_discovery{,_preview}` hard-code `LocalAutomationConfig()`                                                                                                                                                                                | Mocking them erases the remote branch — the AC's forbidden pattern                                                                                                       | confirmed, drives test design                                               |
| B-F2  | 5 distinct remote asymmetries (pre-sync, central-only change, lossy wire format, double permission check, cross-site rule write)                                                                                                                | R5 in the plan; must be re-verified at every phase exit                                                                                                                  | open                                                                        |
| B-F3  | `update_service_phase` performs no job-active check; while a scan runs, `get_result` hands it an empty table, so the transition is `None` and the endpoint answers `204`                                                                        | A requested change is silently discarded. Low severity, but it shows _job-active_ being used as a proxy for _your table is still current_, in one entry point out of two | ✅ **confirmed defect** → §10.18                                            |
| §2.1  | `removed` is target-only (alive, required); `clustered_ignored` is unreachable; `legacy` / `legacy_ignored` aren't `DiscoveryState` members but are accepted by REST                                                                            | `DiscoveryState` mixes one verb with 14 nouns; evidence for splitting source from target (Phase 3)                                                                       | `removed` **closed**; rest investigating                                    |

---

## 9. Review status and open investigations

The findings above were reviewed on 2026-08-14. This section records what has been adjudicated and
what is still being verified, so that the document is honest about its own confidence level.

### 9.1 Adjudicated — no ticket

| ID        | Disposition                                                                                                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A3-F1     | **Intended.** Narrow adoption is why `UPDATE_SERVICE_LABELS` / `UPDATE_DISCOVERY_PARAMETERS` exist. Kept as a contract requirement for batch apply, not as a defect.                             |
| A3-F2     | **Intended.** `FIX_ALL` accepts; `TABULA_RASA` forgets _then_ accepts. Follow-up question deferred to after the epic: is `TABULA_RASA` still needed once Phase 1's primitives exist?             |
| P-F2      | **Closed.** REST's `403` is correct; the degrading GUI is deleted at the end of the epic.                                                                                                        |
| `removed` | **Not a defect.** Target-only by design and required in that role.                                                                                                                               |
| A2-F2     | **Confirmed defect, ticket proposed (§10.1).** werk 19800 landed, but covered only the `ignored` and `clustered_*` sources. `unchanged`/`changed`/`vanished` → `ignored` still write autochecks. |

### 9.2 Resolved by investigation

All items are folded into the sections above and, where confirmed, ticketed in §10.

| ID                          | Outcome                                                                                                                                                                                                                                                                             |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1-F1                       | **Confirmed.** Comment false since 2020; no upstream filter; the `is_discovered` filter is only a status-message heuristic. 11 of 13 sources reach the fall-through. → §10.8                                                                                                        |
| A1-F2                       | **Confirmed.** The missing gate is `update_source`, not `selected_services` — host-wide scope is intended. Unfixed remainder of werk 17711. → §10.5                                                                                                                                 |
| A1-F4                       | **Not a defect.** The alias is intentional and disclosed; `changed` genuinely is a subset of monitored. Uncovered a separate real bug → §10.7                                                                                                                                       |
| A2-F1                       | **Split.** Permission half not exploitable today; data-loss half real (13 values delete, 10 of 17 undefended). → §10.3                                                                                                                                                              |
| A2-F2                       | **Confirmed defect.** werk 19800 covered only the `ignored` and `clustered_*` sources. → §10.1                                                                                                                                                                                      |
| A2-F3 / A2-F4               | **No data harm** — the write is value-identical, so nothing is resurrected; the effect is a failure to clean up. `vanished → new` is reachable via REST (the endpoint's HATEOAS links advertise it on vanished rows) but is an **invalid** transition, split out as A2-F6 → §10.16. |
| A2-F5                       | **Not a defect on GUI paths** — `may_edit_ruleset("ignored_services")` is satisfied by `wato.services`, which every GUI path already holds. Real gap is P-F1. → §10.4                                                                                                               |
| P-F1                        | **Confirmed authorization gap**, covering `wato.edit` as well as `wato.services`. → §10.4                                                                                                                                                                                           |
| P-F3                        | **Not a cost issue** (the write is guarded and normally a no-op); two real defects underneath. → §10.9                                                                                                                                                                              |
| `legacy` / `legacy_ignored` | **Origin found:** they were real `DiscoveryState` members at `aecd8007105` (June 2020). Removal path still open.                                                                                                                                                                    |

### 9.3 Still open

Everything else has been resolved. What remains:

| ID            | Question                                                                                                                                                        |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-F1 / §10.11 | The `ignored_checks` sub-case (a disabled check _plugin_, where `analyse_ruleset` returns `None`) needs one confirmation on a live site before §10.11 is filed. |
| §10.14 step 3 | Whether to narrow the v1 request enum at the next major API version or leave it rejecting with `400` indefinitely — an API-ownership call, not a code question. |

### 9.4 Resolved — the `DiscoveryState` values with no producer

| ID                          | Outcome                                                                                                                                                                                                                                                     |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `clustered_ignored`         | **Dead by accident.** Regression datable to `692c918bf86` (2021-02-05), which turned a mutate-then-prefix into an early return and silently reverted werk 7128. Live user-visible misclassification. **Must be fixed, not deleted.** → §10.13               |
| `legacy` / `legacy_ignored` | **Confirmed unproducible.** Display phases for `legacy_checks`, removed from base by werk 7342 (1.6.0b1) and from `DiscoveryState` by `e7d3d548913` (2023); the REST mapping was never cleaned and the 2026 framework migration re-published them. → §10.14 |
| `_lookup_phase_name`        | **Total** over all 13 reachable sources; no 500-on-GET. Not enforced by types, so worth a test.                                                                                                                                                             |

### 9.5 Resolved — the `custom` origin

`DiscoveryState.CUSTOM` is a read-only projection of the
`custom_checks` ruleset (_"Integrate Nagios plug-ins"_), synthesized per host by
`ConfigCache.custom_check_preview_rows` (`cmk/base/config/_impl.py:2180-2212`) and appended to the preview
in `check_mk.py:968-985`. No discovery is involved and the state has no lifecycle — in §2.4's terms it is
`origin=custom` with `disabled_by_rule` as its only other axis, which is why every `custom` cell in §3 and
§4 is ⚠️ noise. Both findings below are **outside `services.py`**, so neither changes a cell in §3–§6.

| ID   | Outcome                                                                                                                                                                                                                                    |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| C-F2 | **Already fixed upstream.** `ignored_active` / `ignored_custom` were unrenderable GUI values from `35b96ecaeb9` (2021-11-11) to werk 18136 (2025-10-09). Recorded as precedent for C-F1 and §10.12, not as a ticket. → §2.1                |
| N-F1 | **Confirmed regression, ticket proposed.** The Nagios core writer stopped honouring "Disabled services" for `custom_checks` in `cbbcad6fb5f` (2020-04-09) — an editing slip inside an unrelated fix (werk 10883). CMC unaffected. → §10.15 |

---

## 10. Confirmed defects — proposed tickets

Only findings that survived verification appear here: each was checked against the code, the git
history and the existing tests, and traced to a concrete, reproducible symptom. Items that turned out
not to be defects (§9.2) are deliberately absent.

### 10.1 Disabling a monitored service still writes it into the autochecks file

**Verified:** code path, `git show 3b05a138153`, werks 19800 / 19801 / 19806 / 20035, and the
existing test pins. Source finding: A2-F2.

**Proposed title:** _Service discovery: disabling a monitored or changed service still writes it into
the autochecks file (werk 19800 gap for the `unchanged` and `changed` sources)_

**Summary.** Werk 19801 established the contract that services matched by a "Disabled services" rule
must never be written to the autochecks file, and werk 19800 (CMK-33299, commit `3b05a138153`)
implemented it — but that commit's `services.py` diff changed only `_case_ignored` and
`_case_clustered`. The three sibling handlers still add the entry to `autochecks_to_save` when the
target is `ignored`: `_case_monitored` (`services.py:1027-1031`), `_case_changed`
(`services.py:1048-1053`) and `_case_vanished` (`services.py:1010-1012`). The fix therefore covers
the rule-driven case — a service already classified `ignored` because a rule matched it — but not the
ordinary user action of clicking "disable" on a currently monitored service, or
`PUT /objects/host/{host}/actions/update_discovery_phase/invoke` with `target_phase: "ignored"`.
Nothing downstream filters the entry out: `set_autochecks_v2` →
`_automation_set_autochecks_v2` → `set_autochecks_for_effective_host` (`_autochecks.py:202-222`)
never consults `ignore_service` / `ignore_plugin`.

**Symptom.** The defect is latent at first: the next preview still classifies the service `ignored`,
because `_node_service_source` applies the ignore filter to a service that is still discovered. What
accumulates is the autochecks **residue** that werks 19800/19801 set out to eliminate — an entry for a
service a "Disabled services" rule matches — growing without bound on hosts with volatile services
(Kubernetes, Docker). Once such a service also disappears from the agent output, the residual entry is
what makes it surface as `vanished`, which werk 19801 designates as the cleanup signal. The
classification is by design; the entry that triggers it is the bug.

**Scope.** `_case_vanished` (`services.py:1010-1012`) writes on target `ignored` as well, but that
transition is invalid in the first place — `ignored` is not a state a not-discovered service can occupy
— so it needs withdrawing rather than correcting. Separate ticket, §10.16. This ticket is the two cells
where `ignored` is a legitimate target.

**Reproduction.** On a host with an agent-provided service, disable a single **monitored** service
from the discovery page (source `unchanged` → target `ignored`). Confirm
`var/check_mk/autochecks/<host>.mk` still contains it. Remove the service from the agent output and
re-run discovery: it appears as `vanished` instead of disappearing.

**Note for the fix commit.** The current behaviour is _pinned_ by
`tests/unit/cmk/gui/watolib/test_do_discovery.py` — `(MONITORED, IGNORED)` at `:81-86` and
`(CHANGED, IGNORED)` at `:339-344` — so both rows must change together with the fix (and
`(VANISHED, IGNORED)` at `:116-121` with §10.16). `tests/unit/cmk/gui/watolib/test_services.py:1119`
already drives the `unchanged → ignored` transition and needs only an assertion on
`mock_set_autochecks.call_args.args[1].target_services`; today it requests the
`mock_set_autochecks` fixture and never inspects it.

### 10.2 The `_apply_state_change` matrix test covers 120 of 225 cells

**Verified:** re-derived the generator's output. Source finding: T-F1, detail in §7.0.

**Proposed title:** _Service discovery: `test_do_discovery.py` matrix uses
`combinations_with_replacement` and silently skips 47% of the (source, target) cells_

**Summary.** `_get_combinations` in `tests/unit/cmk/gui/watolib/test_do_discovery.py` builds its test
matrix with `itertools.combinations_with_replacement(states, 2)`, which yields **unordered** pairs —
120 of the 225 ordered `(source, target)` combinations, and which 120 depends on the declaration
order of the attributes in `DiscoveryState`. Because the assertion is
`known_results.get((source, target), empty_result) == result`, any pair the generator does not
produce is never asserted. The untested half contains every "accept" and "re-enable" transition,
including `changed → unchanged` — the core transition of the feature — plus `ignored → unchanged`,
`ignored → new`, `unchanged → new`, `changed → new` and `vanished → new`. Additionally,
`known_results` holds unreachable rows such as `(MONITORED, UNDECIDED)` (`:75-80`), which read as
pinned cells but are never executed. The file presents as an exhaustive 15 × 15 matrix and is not
one, which is how A2-F2 survived werk 19800: the `(MONITORED, IGNORED)` cell _is_ generated and pins
the buggy value, while the neighbouring cells that would have exposed the inconsistency never ran.
The fix is to switch to `itertools.product` and resolve whatever the newly covered 105 cells reveal —
which is exactly the Tier 1 work in §7, so this ticket and CMK-34150's Tier 1 should be the same
change.

### 10.3 REST `update_discovery_phase`: 13 of 17 `target_phase` values silently delete services

**Verified:** all three `Discovery` construction sites enumerated; end-to-end trace; no test coverage
exists (`grep target_phase tests/` → nothing). Source finding: A2-F1.

`UpdateDiscoveryPhaseModel.target_phase` accepts all 17 `SERVICE_DISCOVERY_PHASES` keys, but only
`monitored`, `undecided`, `ignored` and `removed` are meaningful transitions. For a currently
monitored service, each of the other 13 (`legacy`, `legacy_ignored`, `manual`, `active`, `custom`,
`ignored_active`, `ignored_custom`, `vanished`, `changed`, and the four `clustered_*`) causes
`_case_monitored` to skip the write, so the service is erased from
`var/check_mk/autochecks/<host>.mk` — behaviour identical to `removed` — while the endpoint returns
**`204 No Content`**. Ten of the 13 additionally pass `_verify_permissions` without demanding any
`wato.service_discovery_to_*`, because its `match` has no default arm and `table_target` is typed
`str` so mypy cannot flag it. That is masked today only because the handler demands all four
permissions unconditionally, and becomes a live authorization hole the moment a second caller exists —
which the planned batch-apply endpoint is. Realistic harm: an integration author reads the OpenAPI
enum, picks `active` to "activate" a service, and silently un-monitors services in a loop.
Repro: `PUT /objects/host/myhost/actions/update_discovery_phase/invoke`
`{"check_type":"df","service_item":"/","target_phase":"legacy"}` → `204`, service gone.
Fix: narrow the accepted set to the four meaningful phases (in `unstable`/v2, or return an explicit
`400` in v1 since narrowing a published enum is breaking), and add a `case _: raise` default arm.

### 10.4 REST `update_discovery_phase` bypasses `wato.services` and `wato.edit`

**Verified:** `may_edit_ruleset` definition; endpoint permission surface; framework validation order.
Source findings: P-F1, A2-F5.

`update_service_phase_v1` calls `Discovery(...).do_discovery(...)` directly, never entering
`_service_discovery_context` and therefore never checking `wato.services`. Its entire authorization
surface is authentication, host **read** (`HostConverter(permission_type="setup_read")` — not write,
on a mutating `PUT`), and the four `wato.service_discovery_to_*`. Every sibling endpoint in the family
requires `wato.edit`; this one does not. Because `may_edit_ruleset("ignored_services")` is defined as
`user.may("wato.services") or user.may("wato.rulesets")`, a custom role granted the four
discovery-target permissions but denied both "Manage services" and "Rule sets" is correctly locked out
of the entire GUI discovery page — every control checks `wato.services` — yet can `PUT
target_phase: "ignored"` and have `EnabledDisabledServicesEditor` write an `ignored_services` rule
into the host's folder, or delete services outright. Neither the editor nor the generic ruleset-save
path performs any permission check of its own. Note `EndpointPermissions(required=...)` is not a gate:
the framework validates it only after the handler has written to disk, and only to confirm declared
permissions were used. **Implementer note:** adding `need_permission("wato.services")` requires
extending `UPDATE_PHASE_PERMISSIONS` too, or `PermissionValidator` raises under `is_testing=True`.

### 10.5 "Update service labels" / "Update discovery parameters" retarget every service on the host

**Verified:** empirically, by running `compute_discovery_transition` over all 13 sources; plus werk
and git archaeology. Source finding: A1-F2.

Both branches of `_get_table_target` (`services.py:558-566`) ignore `update_source`, so every row is
retargeted to `update_target` (always `unchanged`). Werks 16466 and 17710 promise "all **changed**
services or a specific service", and both callers already transmit `update_source="changed"` — read
only inside the `BULK_UPDATE` branch, so it is dead here. Every `new` row therefore reaches
`_case_undecided`, which writes it to autochecks: **the action accepts every undecided service on the
host**, in the same response, with a pending change that looks like an ordinary
"Saved check configuration … with N services". `vanished`/`manual`/`active`/`custom`/`clustered_*` rows
additionally force the host-global `apply_changes` and demand
`wato.service_discovery_to_monitored`, which the pre-gate for these actions does not require.
This is the unfixed remainder of **werk 17711 / CMK-22272**, which fixed the identical bug for the
`ignored` source alone by adding a per-source carve-out instead of a source filter.
Repro (REST, works even with **no** changed services):
`POST /domain-types/service_discovery_run/actions/start/invoke`
`{"host_name":"myhost","mode":"only_service_labels"}` after a `refresh`.
GUI: Actions ▸ "Update service labels" on a host with one changed and one undecided service — and note
the ticked checkboxes are ignored even though the menu topic is titled "On selected services".
**Fix must key off `update_source`, not `selected_services`:**
`tests/unit/cmk/gui/watolib/test_services.py:2201-2235` pins the selection-ignoring behaviour and
stays green for the former, breaks for the latter.

### 10.6 Bulk-action pre-gate disagrees with the permission the action demands

**Verified:** both gates read. Source finding: A2-F5 side-effect.

`has_discovery_action_specific_permissions` grants `BULK_UPDATE` on `to_monitored ∧ to_removed` and
ignores `update_target` entirely (`services.py:811-815`), while
`_toggle_bulk_action_page_menu_entries` enables each button on its own target's permission
(`wato/pages/services.py:1379-1402`). A user holding only `to_undecided` sees "Declare monitored
services as undecided" **enabled**; clicking it is rewritten to `DiscoveryAction.NONE` and the page
silently refreshes with nothing done. The same mismatch exists for `UPDATE_SERVICE_LABELS` /
`UPDATE_DISCOVERY_PARAMETERS`, pre-gated on `wato.services` alone but always demanding
`to_monitored` — there the action raises `MKAuthException` (HTTP 403 via REST) instead of no-opping.
Failure is clean in both cases: all permission checks run inside the pure
`compute_discovery_transition` before any write.

### 10.7 Bulk actions for the "Changed services" table are never enabled

**Verified:** `grep -rn "bulk_changed"` → no matches anywhere in the repo.

`_toggle_bulk_action_page_menu_entries` handles `MONITORED | CHANGED` in one arm and enables
`f"bulk_{table_source}_{target}"` (`wato/pages/services.py:1379-1383`), so the Changed table emits
`bulk_changed_new` / `bulk_changed_ignored`. No `PageMenuEntry` with those names exists — the eight
real entries are all `bulk_{new,unchanged,ignored,vanished}_*`. `enable_page_menu_entry` resolves a
null element and silently does nothing. On a host where every monitored service is classified
`changed` and no `unchanged` table is rendered, both "including changed" buttons stay permanently
greyed out and the user cannot bulk-undecide or bulk-disable their changed services.
_In code scheduled for deletion in Phase 5 — but it ships in released versions, so it needs a decision
rather than silent inheritance by the new UI._

### 10.8 `FIX_ALL` forces an autochecks rewrite on hosts with non-discovered services

**Verified:** see A1-F1. Ships on most real hosts, including the Checkmk server host itself.

`_get_table_target` retargets 11 of 13 reachable sources to `MONITORED`, so `apply_changes` — a
host-global flag derived from a raw `check_source != table_target` string comparison — is always set on
any host with an active check, a custom check, an enforced service, or cluster membership. Each "Accept
all" click then costs one `set-autochecks` pending change **with an empty diff**, one audit entry, one
`set-autochecks-v2` automation round trip and one autochecks rewrite. Worse than cosmetic in one case:
where an "Enforced services" rule shadows a previously discovered service, the shadowed entry is
dropped from the transition table upstream and re-added as `manual`, which has no
`_apply_state_change` case — so a nothing-to-do `FIX_ALL` **silently deletes that autochecks entry**.
The guarding comment `# entry.check_source in [MONITORED, UNDECIDED]` has been false since the file was
created in 2020.

### 10.9 Two defects around the `inventory_failed` host flag

**Verified:** guard in `set_discovery_failed`; `save_hosts` permission check; single producer.
Source finding: P-F3 (whose cost claim was wrong — the write is guarded and normally a no-op).

**(a) `clear_discovery_failed` can raise after the discovery has been written.** Its comment claims
_"We do not check permissions. They are checked during the discovery."_, but when the flag is set it
reaches `Folder.save_hosts`, which requires folder **write** (`hosts_and_folders.py:1652`). The
discovery page requires only host `read` plus `wato.services`. A user with
`wato.services` + `wato.see_all_folders` who is not a folder contact therefore gets a
"no permissions to the folder" error _after_ `set_autochecks_v2` has run and the pending change was
recorded, because the clear happens on context-manager exit.

**(b) `update_service_phase` never clears the flag.** It bypasses `_service_discovery_context`
entirely, so a host flagged by a failed bulk discovery stays flagged indefinitely for a client that
only uses that endpoint — even though the endpoint runs a full preview and succeeds. Visible as a
stale warning icon in the folder host list and, operationally worse, permanent inclusion in bulk
discovery's _"Only include hosts that failed on previous discovery"_ set, so automation retrying the
failed hosts never converges. Fix by moving the clear into `Discovery.do_discovery` or routing the
endpoint through the context manager.

### 10.10 Quick setup applies discovery to the central site for remote-site hosts

**Verified:** read the call site; `site_id` comes from an explicit user selection and the surrounding
code handles remote sites explicitly.

`_run_service_discovery` (`cmk/gui/quick_setup/v0_unstable/predefined/_complete.py`) receives a
correctly derived `automation_config` and uses it for `get_check_table` and
`_get_service_discovery_result` — then passes **`automation_config=LocalAutomationConfig()`** to
`perform_fix_all` (`:540`). For a quick-setup bundle whose target site is remote, the preview is
fetched from the remote while `set_autochecks_v2` and `update_host_labels` execute on the **central**
site, so the autochecks land in the wrong site's `var/check_mk/autochecks/`. The site is chosen by the
user (`site_id = SiteId(site_selection) if site_selection else omd_site()`, `:305`) and the same file
explicitly handles remote sites elsewhere (`site_is_local` at `:447`, a remote-site error message at
`:480`), so this is a missed parameter rather than an unreachable path.

**This is the same defect class as the hackathon PoC's worst bug** — an apply path that is
unconditionally local — in production code that _survives_ the rewrite. It is exactly what test T2.2
is designed to catch, and it is the strongest argument for that test.

### 10.11 REST modes pass `selected_services=EVERYTHING`, disabling the duplicate-service guard

**Verified empirically** for the `add_disabled_rule` delta; the `ignored_checks` sub-case is
**unconfirmed** and needs one check on a live site before this is filed.

`compute_discovery_transition` guards against creating "Disabled services" rules for services disabled
by a _plugin_ rule via `add_disabled_rule - remove_disabled_rule - (saved_services - selected_services)`
(`services.py:404-406`). All three writing REST modes pass `selected_services=EVERYTHING`, so
`_get_selected_descriptions` yields every description and the subtraction term collapses to ∅ —
measured: an already-`ignored` row yields `add_disabled_rule=['svc-ignored']` under `EVERYTHING`
versus `[]` under the GUI's `()`. Every REST save on a host with disabled services therefore invokes
`EnabledDisabledServicesEditor`, costing one `get_services_labels` automation; and for services
disabled through `ignored_checks` (a disabled check _plugin_) `analyse_ruleset` returns `None`, so they
survive the filter at `rulesets.py:1931-1934` and `_update_rule_of_host` creates a host-pinned
`ignored_services` rule the user never asked for — with neither
`wato.service_discovery_to_ignored` nor `may_edit_ruleset` checked on that path (source == target, so
`_verify_permissions` demands nothing). Idempotent after the first write.

### 10.12 Split `DiscoveryState` into a display state and a transition command

**Refactoring ticket, not a defect** — but it is the root cause of §10.3, A2-F1 and several
inconsistencies in §4. See §2.4.

Only 4 of 15 values are honest members of both the source and target vocabularies: 8 are source-only,
`removed` is target-only, `clustered_ignored` is dead, and `changed`/`clustered_old`/`clustered_new`
are half-wired — accepted as targets by `_verify_permissions` and `_get_autochecks_values`, then
silently dropped by `_apply_state_change`. The sharpest demonstration is `unchanged → changed`
(reachable via REST): the permission is demanded, the new parameters and labels are computed, and then
`_case_monitored` discards them and deletes the service, because `changed` is not in its write list.
Two of three `match` statements say `changed` is a valid target; the third disagrees, and the third
decides.

Because `_apply_state_change` has no `case _`, a source-only value used as a target silently means
"delete from autochecks, demand no permission". The merge also forces `table_target: str`, which is why
the file carries a blanket `# mypy: disable-error-code="exhaustive-match"` — and note the stated reason
for `DiscoveryState` not being an enum (_"Enum is not serializable"_) is obsolete and refuted by
`DiscoveryAction`, a `StrEnum` twelve lines below with the docstring _"This is exported to javascript,
so it has to be json serializable"_. A `StrEnum` alone would still not suffice, because `table_target`
must currently hold `legacy` and `legacy_ignored`, which are not members at all. Modelling the target
as a **3**-element command enum — `monitor`, `disable`, `drop` (§11.1) — makes all three `match`
statements exhaustive and lets the Tier-1 matrix assert a total `source × command` table. Three, not
four: `forget` and `delete` write the same thing and differ only in an observation the caller cannot
change, so they are one command whose label the row decides.

### 10.13 Disabled clustered services are misclassified — `clustered_ignored` lost its producer in 2021

**Verified:** the regression commit's diff, werk 7128's introducing commit, and the surviving GUI group.
Source finding: §2.1 / C-F1.

**Proposed title:** _Service discovery: disabled clustered services are shown on the node as plain
"Disabled services" and are missing from the cluster page (`clustered_ignored` never produced)_

**Summary.** For a service that a _Clustered services_ rule maps from node N onto cluster C and that is
also matched by a _Disabled services_ rule, `_node_service_source`
(`packages/cmk-check-engine/cmk/checkengine/discovery/_autodiscovery.py:772-776`) returns plain
`"ignored"` instead of `"clustered_ignored"`. The node's discovery page therefore files it under the
generic "Disabled services" group **with bulk actions enabled**, while the cluster's page — where a
clustered service is actually managed — shows it as "Vanished services" if a stale autocheck remains,
and does not list it at all once werks 19800/19806 stop disabled services being written to autochecks
(the steady state going forward).

Everything needed for correct behaviour already exists and is unreachable: the `TableGroupEntry`
_"Disabled clustered services - located on cluster host"_ (`cmk/gui/wato/pages/services.py:2168-2178`,
`show_bulk_actions=False`, translated in 8 locales), the `Transition` literal, the
`DiscoveryReport.clustered_ignored` counter, and `_case_clustered`'s match arm. All dead since
**`692c918bf86`** (2021-02-05, _"discovery: towards `QualifiedDiscovery` 1"_) replaced
`check_source = "ignored"` followed by `"clustered_" + check_source` with an early `return "ignored"`,
silently reverting **werk 7128** (1.6.0i1, _"Display vanished and disabled clustered services on
discovery page of the nodes"_). The code's own `# TODO: this does not make much sense. If the service is
clustered, but ignored _on that cluster_, it should be shown there.` was added in 2024, above the
already-broken line.

**Not cosmetic.** Because `_case_ignored` handles the service instead of `_case_clustered` — which
deliberately refuses non-`ignored` targets for clustered services — a user can move it to "monitored"
from the node page. `EnabledDisabledServicesEditor` is constructed with the _node_ and writes a
node-scoped `ignored_services` rule, but the effective disable for a clustered service is evaluated on
the cluster, so the service stays disabled while the GUI reports _"Saved check configuration of host …"_
and files a pending change. The `vanished` label on the cluster also invites the wrong remedy — "Remove
vanished services" deletes the autocheck without touching the responsible rule.

**Reproduction.** Create cluster C over node N; add a _Clustered services_ rule on N matching service S;
add a _Disabled services_ rule with no host restriction matching S. Open N's service discovery: S is
under "Disabled services", not "Disabled clustered services". Open C's: S is under "Vanished services"
or absent. Re-enable S from N's page: reports success, has no effect.

**Fix.** Return `"clustered_ignored"` from the node branch, and classify the cluster side with
`is_ignored(cluster)` rather than letting `appears_on_cluster`'s node-level ignore filter drop the
service out of the cluster's `current` list. Note the asymmetry that makes the common case worst:
`_node_service_source` tests the rule on the **cluster** while `appears_on_cluster` tests it on the
**node**. Add regression tests for all three rule-scoping cases (matches both hosts / only the cluster /
only the node). Also correct werk 19806's claim about this transition.

### 10.14 Remove the `legacy` / `legacy_ignored` REST phases

**Verified:** origin, removal commits, the compatibility policy text, and an existing precedent.
Source finding: §2.1 / L-F1. Overlaps §10.3 — implement them together.

`SERVICE_DISCOVERY_PHASES` still maps `"legacy"` and `"legacy_ignored"` to themselves, and the
`target_phase` `Literal` still publishes them in the **stable v1** OpenAPI enum, although the feature
they described (`legacy_checks` in `main.mk`) was removed by werk 7342 in 1.6.0b1 and the states left
`DiscoveryState` in 2023. They are not inert: sending `target_phase: "legacy"` deletes the service from
autochecks and returns `204` (§10.3).

**Recommended path — do not run a deprecation cycle.** The framework has no value-level deprecation
flag (only whole-version, whole-field and whole-endpoint), so "deprecate the value then remove it" is
not expressible; a cycle would mean advertising a silently destructive value for another release. The
compatibility policy's "undocumented behaviour" clause applies — the _value_ is documented, its
_behaviour_ is not.

1. Delete both entries from `SERVICE_DISCOVERY_PHASES` — internal, unreferenced, unreachable.
2. In **v1**, reject the value with `400` rather than removing it from the enum, following
   `.werks/16037.md` (_"folder_config/host_config: No longer accept non-existent site"_, 2.3.0b1,
   `compatible: yes`) in shape. Do this for **all 13** meaningless values at once, not just these two.
   Add the missing `case _:` arms so exhaustiveness becomes enforceable once the target is its own enum
   (§10.12).
3. In **`APIVersion.UNSTABLE`**, override the handler with a narrowed
   `Literal["monitored", "undecided", "ignored", "removed"]`, so the unstable spec stops advertising the
   dead values immediately. Narrow the v1 enum itself only at the next major API version.
4. **Werk:** class `fix`, component `rest-api`, level 1, `compatible: yes`, modelled on 16037. Mention
   `legacy` / `legacy_ignored` explicitly as remnants of werk 7342.
5. Add the test that does not exist: `git grep target_phase -- tests` returns nothing. Parametrize over
   all 17 values — `400` for the 13, `204` plus the expected autochecks state for the 4.

### 10.15 Nagios core: disabling a custom check has no effect

**Verified:** the removing commit's diff, `do_omit_service` present at `0ad335773ff` (2020-01-07) and
absent at the 2.0.0 / 2.1.0 / 2.2.0 / 2.3.0 / 2.4.0 / 2.5.0 branch heads and current master, and the
surviving CMC call site. Source finding: N-F1 / §9.5.

> **Outside this document's stated scope** (`cmk/gui/watolib/services.py` + the automation boundary).
> Found while characterizing the `custom` origin, and recorded here because it is what makes the
> `ignored_custom` display state a false statement. It needs its own ticket and its own owner — the
> Nagios config writer, not service discovery.

**Proposed title:** _Nagios core: services from the "Integrate Nagios plug-ins" (`custom_checks`) rule set
are still monitored after being disabled via "Disabled services"_

**Summary.** `create_nagios_servicedefs` applies `_skip_service` — which is `service_ignored(...) or
host_name != effective_host(...)` — at exactly **one** place, the active-check loop
(`cmk/base/core/nagios/_create_config.py:830`; definition at `:1118-1128`). The `custom_checks` loop at
`:904-921` → `_create_custom_check` (`:998-1109`) applies no filter at all, so the `service` object is
written unconditionally. The microcore does apply it: `_add_active_check_from_custom_entry` calls
`_do_omit_service` (`cmk/base/nonfree/cmc/_services.py:195-201`, definition at `:146-151`).

**It is a regression with a datable, accidental cause.** ✅ _verified against the commit_

At `0ad335773ff` (2020-01-07, then `cmk/base/core_nagios.py:441`) the custom-check loop still called it:

```python
if do_omit_service(hostname, description):
    continue
```

Commit **`cbbcad6fb5f`** (2020-04-09, werk **10883** _"Prevent empty service descriptions from being
activated"_, class `fix`) added an empty-description guard to three blocks. In the passive and active-check
blocks it **inserted** the new guard above the existing code; in the custom-check block it **replaced** the
omit call, reusing its `continue`:

```diff
-            if do_omit_service(hostname, description):
+            if not description:
+                core_config.warning("Skipping invalid service with empty description on host %s" %
+                                    hostname)
                 continue
```

Neither the commit message nor the werk mentions disabled services; both are about empty descriptions
only. The occurrence count of `do_omit_service` in the file goes 3 → 2 in that commit and stays there, the
single surviving call site being the active-check one — which is why the two families have behaved
differently ever since.

**Scope.** Present in 2.0.0 through current master. Affects any site running the Nagios core: the only
choice in the **community** edition, and a selectable option in every other edition
(`_monitoring_core_choices`, `cmk/gui/wato/_omd_configuration.py:123-133`). CMC sites are unaffected, so
this is a core-dependent divergence in what "disabled" means.

**Two symptoms, one cause** — `_skip_service` is a disjunction and both halves were lost:

1. **"Disabled services" / "Disabled checks" are ignored.** The service keeps being checked and keeps
   notifying. Since werk 18136 (2.5.0b1) the discovery page files it under _"Disabled custom checks -
   defined via rule"_ (`cmk/gui/wato/pages/services.py:2190-2200`), so the GUI now actively asserts
   something untrue.
2. **The clustered redirection is ignored.** A custom check whose description a _Clustered services_ rule
   maps onto a cluster is still created on the node, because `host_name != effective_host(...)` is no
   longer consulted.

**Why it went unreported for six years — see C-F2 (§2.1).** Until werk 18136 the `ignored_custom` row was
dropped from the discovery page entirely, so disabling a custom check _looked_ like it had worked: the row
vanished while the core kept monitoring the service. The two regressions concealed each other. The GUI half
is now fixed, which is precisely what makes this newly visible in 2.5 — and makes it more urgent, not less.

**Reproduction.** On a Nagios-core site: add a `custom_checks` rule with service name `My custom check` and
command line `echo "OK - hi" && exit 0`; activate; confirm the service is monitored. Add a _Disabled
services_ rule matching `My custom check`; activate. Expected: the service leaves monitoring. Actual: it is
still present in the generated Nagios object configuration and still checked, while service discovery shows
it under "Disabled custom checks - defined via rule". Repeat on a CMC site to see the intended behaviour.

**Fix.** Restore the call in `_create_custom_check`, mirroring the CMC ordering — CMC registers the
description for duplicate detection _first_ and omits afterwards, so insert directly after the existing
`labels` assignment at `:1071`, which already computes exactly the labels the CMC path uses (no discovered
labels exist for a custom check):

```python
labels = _get_service_labels(config_cache.label_manager, hostname, description)
if _skip_service(config_cache, hostname, description, labels):
    return
```

Note the residual inconsistency to decide deliberately: the active-check path skips _before_ its duplicate
check, CMC skips _after_. Either is defensible; they should not differ silently. Add a regression test in
the Nagios config-writer tests asserting that a `custom_checks` entry matched by `ignored_services`
produces no `service` object, parametrized over both cores so the two paths are pinned against each other —
the absence of such a test is why an unrelated `fix` commit could delete the behaviour unnoticed. Werk:
class `fix`, component `core`, `compatible: yes`, stating explicitly that it affects the Nagios core only
and that existing configurations will lose services that were never meant to be monitored.

### 10.16 `vanished` services accept only `removed`, but three other targets are offered

**Verified:** the classifier guards and their two test pins, all three offer sites, and the
`_case_vanished` branches. Source finding: A2-F6.

**Proposed title:** _Service discovery: "Disable vanished services" (and REST `target_phase` on a
vanished service) offers a transition whose target state cannot exist, and writes the service back into
the autochecks file_

**Summary.** A vanished service is present in the autochecks file and no longer discovered. `removed` is
the only target that means anything for it; `ignored`, `undecided` and `monitored` all name states the
classifier cannot produce for a not-discovered service, so the next preview contradicts whatever the
action wrote. For `ignored` this is asserted deliberately in the check engine —
`_node_service_source` skips the ignore filter whenever the basic transition is `vanished`
(`_autodiscovery.py:764`), `_make_cluster_table` carries the same guard, and both are pinned by
`test_vanished_service_matching_disabled_rule_is_discovered_as_vanished`
(`packages/cmk-check-engine/tests/cmk/checkengine/discovery/test__autodiscovery.py:127`, cluster variant
`:214`), whose docstring states the rule outright.

Nonetheless the transition is offered in three places:

| offered by                                       | code                                                                                                                                                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GUI bulk action **"Disable vanished services"**  | `BulkEntry(VANISHED, IGNORED, …)` at `wato/pages/services.py:2630-2637`, enabled by `_toggle_bulk_action_page_menu_entries`'s `case DiscoveryState.VANISHED` (`:1392-1397`) for any user holding `to_ignored` |
| GUI per-row **"Move to disabled services"** icon | `case DiscoveryState.VANISHED` → `_icon_button(VANISHED, …, IGNORED, "disabled", …)` (`:1815-1827`)                                                                                                           |
| REST `update_service_phase`                      | `target_phase: "ignored"` / `"undecided"` / `"monitored"`, each returning `204`                                                                                                                               |

**Symptom.** `_case_vanished`'s `IGNORED` branch adds the description to `add_disabled_rule` **and**
writes the entry to `autochecks_to_save` (`services.py:1010-1012`). The service is therefore put back
into the autochecks file with a "Disabled services" rule attached — precisely the residue that werk
19801's vanished-classification exists to eliminate (§10.1). It is also inescapable by repetition: the
entry is preexisting and the service is still absent, so every subsequent preview classifies it
`vanished` again, now with a rule that changes nothing. The user is told the configuration was saved and
nothing is cleaned up; only "Remove vanished services" resolves it. The `undecided` and `monitored`
targets fall into the catch-all `else` and keep the entry without a rule (A2-F4) — a failure to clean up
rather than residue, since the write is value-identical.

**Fix — withdraw, do not repair.** Making `_case_vanished` drop the entry on `ignored` would turn
"Disable vanished services" into a duplicate of "Remove vanished services" that additionally writes a
rule for a service that no longer exists. Instead:

1. Remove the `BulkEntry(VANISHED, IGNORED, …)` page-menu entry and its enable in
   `_toggle_bulk_action_page_menu_entries`; drop the `IGNORED` arm from the row-button
   `case DiscoveryState.VANISHED`, leaving only `_icon_button_removed`.
2. Make the pair `(vanished, ignored|undecided|monitored)` a `400` in `update_service_phase` rather than
   a silent `204`. This overlaps §10.3, which narrows the same enum; do the pair validation there.
3. Have `_case_vanished` reject rather than fall through, so the invalid pair cannot be reached by any
   future caller — the same argument as §10.12 (type the target, make the matches exhaustive).
4. A1-F2's fix (§10.5) removes the fourth route in, by stopping `UPDATE_SERVICE_LABELS` from assigning
   `unchanged` to vanished rows.

**Note for the fix commit.** `tests/unit/cmk/gui/watolib/test_do_discovery.py` pins the current
behaviour at `(VANISHED, IGNORED)` `:116-121`; that row must be replaced by a rejection assertion.
Werk: class `fix`, component `wato`, `compatible: yes`, noting that hosts on which the action was used
carry autochecks entries and disabled-services rules that a re-discovery plus "Remove vanished services"
will clean up.

### 10.17 Disabling a clustered service from the node page un-monitors it on the cluster

**Verified:** `_case_clustered`'s branches, the GUI's clustered table-group flags, and the cluster
autochecks-gathering path. Source finding: A2-F7.

**Proposed title:** \_Service discovery: operations on clustered services are rejected by the GUI but
accepted by the backend; `clustered\__ → ignored` drops the node's autochecks entry and silently
un-monitors the service on the cluster\_

**Summary.** A `clustered_*` row on a node's discovery page is informational: a "Clustered services" rule
assigns the service to a cluster, the cluster owns it, and the responsibility for discovering it belongs
to the cluster. `_case_clustered`'s comment says so — _"we do not allow any operation for this clustered
service on the related node"_ — and the GUI implements it: all four clustered table groups pass
`show_bulk_actions=False` (`wato/pages/services.py:2068, 2141, 2154, 2169`), three render collapsed
(`:1181-1187`), and `_show_check_row`'s `match entry.check_source` emits no row buttons for them.

The backend does not implement it. `_verify_permissions` accepts `clustered_new`/`clustered_old` as
targets, `_apply_state_change` routes to `_case_clustered`, which acts instead of rejecting, and the
transition is reachable through REST `update_service_phase` (any `target_phase`) and through the
host-wide actions that retarget every row (A1-F1 `FIX_ALL`, A1-F2 `UPDATE_SERVICE_LABELS`).

**Symptom.** Two severities:

1. Every target except `ignored` rewrites the identical entry and adds it to `saved_services`. No data
   change, but it forces the host-global `apply_changes`, producing a `set-autochecks` pending change and
   an automation round trip for a host where nothing changed.
2. Target `ignored` **drops the entry from the node's autochecks and adds no disabled-services rule**
   (`services.py:1106-1108`; `_case_clustered` has no `add_disabled_rule` parameter at all). Because
   cluster services are gathered from the nodes' autochecks filtered by `effective_host`, removing the
   node's entry removes the service from the **cluster's** monitoring — with no rule recording the
   decision and nothing on the cluster's page to explain it. The next discovery on the node re-adds it as
   `clustered_new`, so the net effect is a transient loss of a cluster service, triggered from a page
   that is documented not to allow any action.

**Reproduction.** Create a cluster with one node, add a "Clustered services" rule matching one of the
node's services, and run discovery on both hosts: the service shows as `clustered_old` on the node and as
a normal monitored service on the cluster. Then, on the **node**, issue
`PUT /objects/host/<node>/actions/update_discovery_phase/invoke` with `target_phase: "ignored"` for that
service. Expected: rejection. Actual: `204`, the entry disappears from
`var/check_mk/autochecks/<node>.mk`, no `ignored_services` rule is created, and after activation the
service is gone from the cluster.

**Fix.** Reject the operation rather than handling it. `effective_host(host, entry) != host` is a
precondition that can be evaluated before the transition table is consulted, which is what the domain
model calls Gate 0 — a rejection carrying a redirect to the effective host. Concretely: make
`_apply_state_change` reject `clustered_*` sources instead of dispatching to `_case_clustered`; drop
`clustered_new`/`clustered_old` from `_verify_permissions`' target arms (§10.12 types the target and
makes the matches exhaustive, which surfaces them); and have `update_service_phase` answer `400` for a
clustered row. Note the interaction with §10.13: while `clustered_ignored` has no producer, disabled
clustered services are misclassified as plain `ignored` and reach `_case_ignored`, so §10.13 must land
for this rejection to cover them.

**Do not implement this by copying the GUI.** The GUI's correctness here is not code that can be
moved: it consists of three _absences_ — four `show_bulk_actions=False` arguments, three groups left
out of `isopen`, and a `match` with no `clustered_*` arm. There is nothing to relocate, so the rule has
to be written down for the first time, and the only place it can live once is the layer both entry
points call. Two reasons not to mirror the front end instead:

- **The GUI is not uniformly right.** For `clustered_*` it declines correctly; for `vanished` it
  _offers_ an invalid operation in two places (§10.16). Mirroring current GUI behaviour into the
  backend would enshrine A2-F6 while fixing A2-F7. Single-sourcing fixes both directions at once.
- **The facts are already in hand where the check is missing.** `update_service_phase` already calls
  `get_check_table(...)` and passes the result into `do_discovery`
  (`openapi/api_endpoints/service_discovery/update_service_phase.py:106-116`), so `origin`,
  `effective_host` and the lifecycle state of the addressed row are available at the one boundary that
  validates none of them. Rules 2–4 of §11.2a are a test on data already fetched, not a new query.

The direction of the dependency inverts: instead of each front end deciding what to offer and the
backend accepting whatever arrives, the gate is evaluated once and the read model carries, per row,
which operations that row admits. The GUI renders that set. What stays in the GUI is presentation —
the two labels for the single `drop` command (§11.3), the grouping and collapsing, and where a
rejection's redirect points.

**Note for the fix commit.** `tests/unit/cmk/gui/watolib/test_do_discovery.py` pins the current
behaviour for the clustered cells it generates; those rows become rejection assertions. A cluster
fixture is required — this is one of the axes that cannot be exercised with a single host (§2.4). Werk:
class `fix`, component `wato`, `compatible: yes`.

### 10.18 A service update issued while a scan is running is answered `204` and discarded

**Verified:** `execute_discovery_job`, `ServiceDiscoveryBackgroundJob.get_result`,
`compute_discovery_transition`'s `apply_changes` guard, and the absence of a job probe in
`update_service_phase`. Source finding: B-F3 (§6.2).

**Proposed title:** _Service discovery: `update_discovery_phase` silently discards the change when a
discovery background job is running for the host_

**Summary.** `execute_service_discovery` refuses with `409` while a job is active
(`execute_service_discovery.py:95-97`); `update_service_phase` does not check. While a job is active,
`get_result` returns `self._pre_discovery_preview` (`services.py:1426-1427`), which in the requesting
process is still the empty preview built by `__init__` (`:1332`) — the job's real pre-scan snapshot
exists only inside the job process. The write path therefore receives `check_table=[]`,
`compute_discovery_transition` never sets `apply_changes`, returns `None` at `:393`, and the endpoint
answers `204 No Content` without writing anything.

**Symptom.** A `PUT .../update_discovery_phase/invoke` issued during a rescan reports success and has
no effect. Scripted use is the realistic exposure: a client that starts `refresh`, does not wait for
`wait-for-completion`, and then sets phases loses those calls silently. No data is corrupted — the
`apply_changes` guard is what stops an empty table from being rebuilt into an empty autochecks file.

**Fix.** Do **not** add a second `job_snapshot` probe. Probing the job answers a narrower question than
the one that matters, and leaves the more common case — a page or script acting on a table read minutes
ago — undetected by either endpoint. Make the table the client decided against an explicit
precondition of the write:

1. Accept `check_table_created` (already computed, already serialized to the client) as a required
   field of the update request.
2. Compare it against the value the freshly read `DiscoveryResult` carries; on mismatch answer `409`
   with the current value. An active job yields `check_table_created == 0`, so the same comparison
   covers B-F3 without a job probe.
3. Keep `execute_service_discovery`'s existing `409` — it is about starting a second scan, which is a
   genuinely different conflict.

This is the mechanism §11.4 item 6 and domain model §9.4 name; B-F3 is the case that makes it concrete
rather than prudential. Requiring a new request field is not backward compatible, so it belongs in the next
API version or behind an optional field that is enforced when present. Werk: class `fix`, component
`rest-api`, and — if the field is made mandatory — `compatible: no` with the migration note that
clients must echo `check_table_created` from a preceding discovery read.

---

## 11. Intended semantics — which operations are meaningful per state

> **This section is normative, not descriptive.** §3–§6 characterize what the code does _today_;
> this section states which operations _should_ be offered per state and what monitoring state each
> should produce. It is the input to the Phase 2 contract, the basis for narrowing the REST API
> (§10.3, §10.14), and the specification the transition-table rework should be written against.
> Where current behaviour diverges, the cell says so and points at the finding.

### 11.1 The operation vocabulary

Per §2.4, the target axis is not a set of states but a set of **commands** — and the command set is
derivable rather than a matter of taste. Discovery can write exactly two things: the **autochecks entry**
for this key on this host, and the **disabled-services rule** matching this description. Everything else
in §2.4 (`found_now`, `origin`, `effective_host_is_self`, "properties diverge") is an _observation_ that
no user action can change. Two writable booleans give four combinations, one of which §10.1's invariant
forbids:

| autochecks entry | disabled rule | command         | today's target name                                     |
| ---------------- | ------------- | --------------- | ------------------------------------------------------- |
| present          | absent        | **M** `monitor` | `unchanged`                                             |
| absent           | present       | **D** `disable` | `ignored`                                               |
| absent           | absent        | **X** `drop`    | `new` _and_ `removed`                                   |
| present          | present       | —               | **forbidden** — the residue werk 19801 exists to remove |

**There are therefore exactly three commands**, and they are exactly the three legal states of the
writable facts.

Two consequences that remove long-standing confusion:

- **`removed` was never a fourth command.** `forget` and `remove` write _the same thing_. They differ
  only in the observation that must hold: forget presupposes `found_now=yes`, so the service returns as
  `new`; remove presupposes `found_now=no`, so it is gone. They are one command whose **UI label** depends
  on the row — "Remove service" on a vanished row, "Move to undecided" everywhere else. The apparent rule
  "only `vanished` may target `removed`, and `vanished` may target nothing else" is not a rule to enforce;
  it is what makes the two names the same operation.
- **`accept_properties` was never a command either.** It is a **parameter of `monitor`**: which facets of
  `ObservedProperties` the write adopts, `⊆ {parameters, labels}`. That is why
  `UPDATE_SERVICE_LABELS` and `UPDATE_DISCOVERY_PARAMETERS` exist as separate _actions_ (A3-F1) — they
  are `monitor` with a restricted adoption set and a `changed`-only selector, not distinct operations.
  Adoption is meaningful **only** for source `changed`, the only state where both property sides are set
  and differ (§5).

The three state-facts the commands produce — _in autochecks?_, _disabled rule?_ — plus the two the
observation supplies — _discovered?_, _properties match?_ — are what the next preview re-derives the
display state from. That is the whole state machine.

### 11.2 The matrix

`✓` meaningful · `–` no-op, to be accepted idempotently rather than rejected · `✗` must be rejected

Sources with `origin ≠ discovered` (`manual`, `active`, `custom`, `ignored_active`, `ignored_custom`) and
sources with `effective_host_is_self = no` (all `clustered_*`) admit **no** operation at all, and are
excluded from the table by the eligibility gate rather than given rows of `✗` — see §11.2a. What remains:

| state                                             | M `monitor`                 | D `disable` | X `drop`                | meaningful  | resulting state                                             |
| ------------------------------------------------- | --------------------------- | ----------- | ----------------------- | ----------- | ----------------------------------------------------------- |
| **`new`** <br>found, ¬stored, ¬ruled              | ✓                           | ✓           | – already in this state | **M, D**    | M → `unchanged` · D → `ignored`                             |
| **`unchanged`** <br>found, stored, props=, ¬ruled | – already                   | ✓           | ✓                       | **D, X**    | D → `ignored` · X → `new`                                   |
| **`changed`** <br>found, stored, props≠, ¬ruled   | ✓ adopts the changed facets | ✓           | ✓                       | **M, D, X** | M → `unchanged` with new values · D → `ignored` · X → `new` |
| **`ignored`** <br>found, ¬stored, ruled           | ✓ drops the rule            | – already   | ✓ drops the rule        | **M, X**    | M → `unchanged` · X → `new`                                 |
| **`vanished`** <br>¬found, stored, ¬ruled         | ✗                           | ✗           | ✓                       | **X only**  | X → gone                                                    |

**Fifteen cells: 10 meaningful, 3 no-op, 2 rejections.** Against **206** off-diagonal
`(source, target)` combinations reachable today via `update_service_phase` (13 sources × 17 targets − 15
diagonals). That ratio is the case for validating the _pair_, not merely narrowing the target vocabulary.

Note what the table no longer contains: a **duplicate** verdict. Earlier drafts needed one because
`removed` shadowed `forget` for every source that is still discovered. Merging them removes the concept,
and with it the two cells that were pure anomalies — a `removed` on an undecided service (a
permission-demanding no-op) and a `removed` on a disabled service (drops nothing, leaves the rule, and
still forces a host-wide autochecks rewrite).

### 11.2a The eligibility gate

Two rejections are properties of the **row**, not of the pair, and are evaluated before the table above
is consulted:

| condition                     | response                                          | why                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `origin ≠ discovered`         | **reject**                                        | the service is defined by the _Enforced services_, _Active checks_ or _Custom checks_ ruleset; there is no autochecks entry to write. The one exception worth stating explicitly: `disable` on such a row _would_ be consequential, because `ignored_services` really does suppress active and custom checks (which is why `ignored_active` / `ignored_custom` exist as states) — but it is a ruleset edit on a non-discovery-managed service, so it belongs in the ruleset editor, and on Nagios cores it silently does not work anyway (N-F1). Prohibited, not impossible. |
| `effective_host_is_self = no` | **reject, with a redirect** to the effective host | the cluster owns the service and the responsibility for discovering it. Nothing needs migrating if the clustering rule is withdrawn — the entry never left the node's autochecks, so the service simply reappears as `unchanged` (A2-F7)                                                                                                                                                                                                                                                                                                                                     |

Together with the table, that is the **complete** validation rule set — four rules, no per-cell list:

1. the target is not one of the three commands → reject
2. `origin ≠ discovered` → reject
3. `effective_host_is_self = no` → reject with a redirect
4. source is `vanished` and the command is not `drop` → reject

### 11.3 What the collapses show

**`drop` unifies `forget` and `remove`, and that is why `vanished` has exactly one operation.** For
sources `unchanged` and `changed`, the targets `new` and `removed` produce **byte-identical**
transitions — neither value is in the handler's write list, both add the description to
`saved_services`; the only difference is which permission `_verify_permissions` demands. For `vanished`,
`forget` cannot be distinguished from `remove` either, because the service is not discovered and so
dropping the entry does not make it undecided — it makes it disappear. One command throughout; the row
decides the label.

**The other two operations are unreachable for `vanished`** — the general form of A2-F6:

- `disable` (→ `ignored`): the classifier deliberately never assigns `ignored` to a not-discovered
  service. `_node_service_source` skips the ignore filter when the basic transition is `vanished`
  (`_autodiscovery.py:764`), `_make_cluster_table` likewise, and two tests pin the rule
  (`test__autodiscovery.py:127`, `:214`).
- `monitor` (→ `unchanged`): monitoring something that is not there yields a stale check and re-vanishes.

Neither can be implemented correctly — each promises a state the next preview contradicts — so both must
be **rejected** rather than made harmless. This holds for the **GUI as much as for REST**: the bulk
action "Disable vanished services" (`wato/pages/services.py:2630-2637`) and the per-row "Move to disabled
services" icon (`:1815-1827`) both offer `disable` today.

**The `removed` target on a still-discovered service is the mirror-image defect.** Because `drop` is one
command, `unchanged → removed`, `changed → removed`, `new → removed` and `ignored → removed` are all
requests for a command under the wrong label. Today they are handled rather than rejected, and two of
them are outright anomalies: `new → removed` demands `to_removed` to do nothing, and `ignored → removed`
is the one `drop` cell where `_case_ignored` does **not** add to `remove_disabled_rule`, so it leaves the
rule in place, has nothing to drop from autochecks (per werk 19800 the entry should not be there), and
still forces a host-wide rewrite.

**The four non-autocheck origins admit nothing at all** — and that set is exactly what the existing
predicate `DiscoveryState.is_discovered` excludes (`services.py:114-127`). That predicate is currently
used in **one** place, to pick a status message (`wato/pages/services.py:725`). It should be the gate on
every operation. Had it been, A1-F1 and A2-F1's `manual`/`active`/`custom` cells would not exist.

**The clustered sources admit nothing on the node** — not because the operations are dangerous but
because the node has nothing to decide: the service is owned by the cluster, and so is the
responsibility for discovering it. `_case_clustered`'s own comment states exactly this: _"there are
already operations for adding, removing, etc. of this service on the cluster. Therefore we do not allow
any operation for this clustered service on the related node."_ Nothing has to be migrated when the
clustering rule is withdrawn, either — the entry never left the node's autochecks, so the service simply
reappears as `unchanged`. The GUI honours this (no bulk actions, no row buttons, collapsed by default);
the backend does not, and `_case_clustered`'s `ignored` branch actively un-monitors the service on the
cluster. That is A2-F7 / §10.17; the misclassification that routes disabled clustered services into
`_case_ignored` instead is the separate `clustered_ignored` story (§10.13).

**`changed` is the only state where property adoption is meaningful**, because it is the only transition
where `DiscoveredItem` has both sides set and differing (§5). It is also the only state with three
meaningful operations, and the only one where `monitor` needs a parameter: today's `SINGLE_UPDATE` and
`BULK_UPDATE` reclassify without adopting, so the service returns as `changed` (A3-F1). The contract must
state, per caller, which facets `monitor` adopts — it cannot be left implicit.

### 11.4 Consequences for the contract and the API

1. **Validate the pair, not the target.** Narrowing `target_phase` to the three commands removes the
   nonsense targets but still admits meaningless pairs such as `vanished → monitored` and
   `manual → monitored`. The check that matters is the four rules of §11.2a plus
   `(current_state, command) ∈ the ten meaningful pairs`; anything else is `400`, not a silent no-op and
   not a silent deletion.
2. **The command set is 3, not 17** — `monitor` (with an adoption set), `disable`, `drop`. `remove`
   versus `forget` is a _label_, chosen by the row's `found_now`, not a disposition. Note that this does
   **not** make the existing `to_undecided` / `to_removed` permission split redundant: once `removed` is
   legal only on a `vanished` row, the two gate disjoint sets of `drop` cells — `to_removed` gates
   `vanished + drop` and nothing else. The gate is therefore keyed on `(state, command)`, not on the
   command alone, and both permissions survive without a deprecation.
3. **`is_discovered` is the authorization gate for the whole feature**, not a message helper. Enforce it
   once, at the entry to the transition, and the non-autocheck rows disappear from every matrix in this
   document.
4. **Clustered services need a redirect, not an operation.** The read contract should tell the client
   which host owns the decision (the cluster), so the UI can link there instead of offering actions
   that silently do the wrong thing.
5. **This table is what the Phase 3 transition table should be generated from.** Five states × three
   commands, plus two row-level gates — every cell is either an operation with a defined result or an
   explicit rejection, which is what makes `match` exhaustiveness achievable once the target is its own
   enum (§10.12).
6. **The pair is validated against a _row_, so the row has to be pinned.** Rules 2–4 of §11.2a are
   predicates on the current state of the service, which means a write is only well-defined relative to
   the table the decision was made against. `check_table_created` already carries that version and is
   already sent to the client; making it a precondition of the write turns two silent failure modes into
   `409`s — a stale page or script (undetected today by either entry point) and a write during an active
   scan (B-F3, §10.18, where `check_table_created` is `0`). This replaces the job-active probe rather
   than adding to it; see domain model §9.4 and its API-compatibility decision in §12.7.

### 11.5 Divergences from current behaviour, indexed

| #   | intended (§11.2)                                                   | current                                                                                                         | finding                           |
| --- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| 1   | `vanished + disable` rejected                                      | writes the service back into autochecks, with a rule attached                                                   | A2-F6, §10.16                     |
| 2   | `vanished + monitor` rejected                                      | keeps it; `vanished` forever                                                                                    | A2-F6, A2-F4, reachable via A1-F2 |
| 3   | `vanished + drop` drops the entry, whichever label the caller used | only the `removed` label drops; `new` and `unchanged` keep it                                                   | A2-F6, §10.16                     |
| 4   | `monitor` always adopts the changed facets it is asked for         | `SINGLE_UPDATE` / `BULK_UPDATE` reclassify without adopting, so the service returns as `changed`                | A3-F1                             |
| 5   | `{unchanged, changed} + disable` → absent from autochecks          | writes it                                                                                                       | §10.1                             |
| 6   | non-autocheck origins reject everything                            | `FIX_ALL` retargets them to `monitored`; REST admits every target                                               | §10.8, §10.3                      |
| 7   | clustered sources reject everything on the node                    | every target except `ignored` rewrites the entry; `ignored` drops it and un-monitors the service on the cluster | A2-F7, §10.17                     |
| 8   | `ignored + drop` removes the disabled rule                         | the `removed` label leaves the rule in place — the one `drop` cell `_case_ignored` treats differently           | §11.3, §10.3                      |
| 9   | the `removed` label is rejected on any still-discovered source     | accepted and handled as `drop`, with a different permission                                                     | §11.3                             |
| 10  | only 10 pairs accepted, under 4 rules                              | 206 reachable via `update_service_phase`                                                                        | §10.3, §10.14                     |
