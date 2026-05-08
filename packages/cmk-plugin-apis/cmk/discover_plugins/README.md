# Plugin discovery — reference and migration guide

This package replaces the old **registry-based** plugin model with a
**discovery-based** one. This document describes the target pattern,
the API in this package, and how to migrate a registry-based domain
to it. It also lists known half-migrated domains and what is needed
to finish them.

Audience: contributors (human or AI agent) who are adding a new
plugin domain, migrating an old one, or completing a partial
migration.

## 1. TL;DR

- **Old world (registry):** plugins are classes that _push_ themselves
  into a mutable singleton (`some_registry.register(Cls)`) at import
  time. The loader's job is to make sure the right modules get
  imported. Failures are silent.
- **New world (discovery):** plugins are inert module-level data
  living under `cmk/plugins/<family>/<group>/`. A central scanner
  _pulls_ them out by walking namespaces. The result is an immutable
  `Mapping`. Failures are returned explicitly.
- **Canonical call:**
  ```python
  discover_all_plugins(
      PluginGroup.X,
      {PluginType: "prefix_"},
      skip_wrong_types=False,
      raise_errors=...,
  ).plugins
  ```
  `PluginType` and the prefix come from the domain's API package
  (`cmk.<group>.<variant>.entry_point_prefixes()`); see §2.1.
- **Migrating a domain?** Skip to §4.
- **Adding a brand-new domain?** §2 + §3 are enough.

## 2. The target pattern

### 2.1 API package and dependency layout

The architectural property that makes discovery worth doing:
**backend code and plugin code share one dependency — the
per-domain API package.**

Each domain has an API subpackage at the `cmk.<group>.<variant>` namespace.
The `<variant>` is one of:

- **`internal`** — internal API, the default when the API is not
  exposed to third-party plugin authors. Examples:
  `cmk.dcd_connectors.internal`, `cmk.server_side_calls.internal`.
- **`v1`, `v2`, …** — stable public API. Examples:
  `cmk.server_side_calls.v1`, `cmk.agent_based.v2`.
- **`v1_unstable`, `v2_unstable`, …** — work-in-progress public API.
  Examples: `cmk.bakery.v2_unstable`, `cmk.inventory_ui.v1_unstable`.

A domain may expose several variants in parallel (e.g.,
`server_side_calls` ships `internal` and `v1`); the loader can
discover plugins of each by passing both prefixes (see the simplest
example in §2.5).

Each variant's `__init__.py` exposes:

- the plugin dataclass(es) (e.g., `ActiveCheckConfig`,
  `ConnectorSpec`);
- `entry_point_prefixes()` returning `{PluginType: "<prefix>_"}` —
  the authoritative source of which name prefix a plugin declaration
  must use;
- any domain helper types plugins need (e.g., `HostConfig`, `Secret`,
  `IPv4Config` for server-side calls).

### 2.2 Public API

Defined in `_python_plugins.py` and `_wellknown.py`:

| Symbol                                                                                | Where                     | Purpose                                                                                                                           |
| ------------------------------------------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `discover_all_plugins(group, prefixes, *, skip_wrong_types, raise_errors)`            | `_python_plugins.py:47`   | Primary entry point. Walks `cmk.plugins.*.<group>` and `cmk_addons.plugins.*.<group>`, returns plugins keyed by `PluginLocation`. |
| `discover_plugins_from_modules(prefixes, modules, *, skip_wrong_types, raise_errors)` | `_python_plugins.py:72`   | Escape hatch: scan an explicit list of module names instead of well-known namespaces. **Treat new uses as transitional.**         |
| `discover_modules` / `discover_submodules` / `discover_families`                      | `_python_plugins.py:124+` | Lower-level enumeration helpers. Rarely needed by callers.                                                                        |
| `PluginGroup` (enum)                                                                  | `_wellknown.py:16`        | Authoritative list of discoverable groups. The enum _value_ is the directory name.                                                |
| `PluginLocation(module, name)`                                                        | `_python_plugins.py:28`   | Identifies a discovered plugin by module path + attribute name.                                                                   |
| `DiscoveredPlugins(errors, plugins)`                                                  | `_python_plugins.py:41`   | Result type. `errors` is a `Sequence[Exception]`; `plugins` is a `Mapping[PluginLocation, PluginType]`.                           |
| `_PluginProtocol`                                                                     | `_python_plugins.py:19`   | Plugin contract: must expose a hashable `.name`.                                                                                  |

Plugins are deduplicated on `(type, name)` (see
`_python_plugins.py:272`); a duplicate becomes an error in the
`DiscoveredPlugins.errors` list (or a raise, depending on
`raise_errors`).

### 2.3 File-system convention

```
cmk/plugins/<family>/<group_value>/<file>.py
cmk_addons/plugins/<family>/<group_value>/<file>.py
```

- `<family>` groups plugins by vendor or feature (e.g., `acme`,
  `tsm`, `dcd`).
- `<group_value>` is the **string value** of a `PluginGroup` member
  (`agent_based`, `server_side_calls`, `rulesets`, …).
- Adding a new domain means adding a `PluginGroup` entry in
  `_wellknown.py`. The string you pick _is_ the directory name.

### 2.4 Plugin object shape

- A frozen dataclass (or other instance) with a hashable `.name`.
- Declared at module top level; **no** registration call, **no**
  decorator:
  ```python
  check_plugin_acme_sbc = CheckPlugin(
      name="acme_sbc",
      service_name="Status",
      discovery_function=...,
      check_function=...,
  )
  ```
- The variable name must start with the prefix the plugin's API
  declares, by convention via `entry_point_prefixes()`. For example
  `cmk.server_side_calls.v1.entry_point_prefixes()` returns
  `{ActiveCheckConfig: "active_check_", SpecialAgentConfig: "special_agent_"}`.

### 2.5 Canonical examples

#### Simplest ideal — `cmk/server_side_calls_backend/_loading.py`

```python
def load_active_checks(*, raise_errors: bool) -> Mapping[
    PluginLocation, internal.ActiveCheckConfig | v1.ActiveCheckConfig
]:
    entry_points = {
        internal.ActiveCheckConfig: internal.entry_point_prefixes()[internal.ActiveCheckConfig],
        v1.ActiveCheckConfig:       v1.entry_point_prefixes()[v1.ActiveCheckConfig],
    }
    return discover_all_plugins(
        PluginGroup.SERVER_SIDE_CALLS,
        entry_points,
        skip_wrong_types=False,
        raise_errors=raise_errors,
    ).plugins
```

No registry, no post-processing, no module-level state. Callers
consume the returned `Mapping` directly. Two API versions are loaded
in one pass by giving the discoverer two `(type, prefix)` pairs.

#### Ideal with type dispatch — `cmk/checkengine/plugin_backend/_discover.py:46+`

Agent-based plugins ship four object types in the same group
(`AgentSection`, `SNMPSection`, `CheckPlugin`, `InventoryPlugin`).
The loader runs one discovery and pattern-matches per location:

```python
discovered_plugins = discover_all_plugins(
    PluginGroup.AGENT_BASED,
    v2.entry_point_prefixes(),
    skip_wrong_types=False,
    raise_errors=raise_errors,
)
for location, plugin in discovered_plugins.plugins.items():
    match plugin:
        case v2.AgentSection():    ...
        case v2.SNMPSection():     ...
        case v2.CheckPlugin():     ...
        case v2.InventoryPlugin(): ...
```

The downstream `registered_*` mappings here are built once from the
discovery result and are immutable — they are _not_ the old mutable
`Registry` shim. Same mental model as §2.5 simplest case, just with
type dispatch on top.

#### Migration helper — `cmk/gui/rule_specs/loader.py:76+`

How to merge `discover_all_plugins` (new home) with
`discover_plugins_from_modules` (legacy modules) during an
in-progress migration:

```python
discovered = discover_all_plugins(PluginGroup.RULESETS, prefixes, ...)
if not_yet_moved_plugins:
    legacy = discover_plugins_from_modules(prefixes, not_yet_moved_plugins, ...)
    discovered = DiscoveredPlugins(
        [*discovered.errors, *legacy.errors],
        {**discovered.plugins, **legacy.plugins},
    )
```

Use this shape (not a pile of ad-hoc loops) when straddling old and
new homes.

## 3. Adding a new plugin domain

1. **Add a `PluginGroup` member** in `_wellknown.py`. The value is
   the directory name; pick something stable.
2. **Define the plugin type as data** in a new API subpackage at
   `cmk.<group>.<variant>`. A frozen
   dataclass with at least a `.name`. Use `internal` as the variant
   unless you're committing to a third-party-stable API (`v1` /
   `v1_unstable`); see §2.1.
3. **Expose `entry_point_prefixes()`** from the variant's
   `__init__.py` returning `{<PluginType>: "<prefix>_"}`, so backend
   code can import it as
   `cmk.<group>.<variant>.entry_point_prefixes`. Pick a prefix that
   doesn't collide with existing groups — duplicates are deduplicated
   on `(type, name)`, so your prefix only needs to be unique among the
   types your group accepts.
4. **Place plugins** at `cmk/plugins/<family>/<group_value>/<file>.py`
   as module-level data (`prefix_foo = Type(name="foo", ...)`).
5. **Write the loader** as a thin wrapper around
   `discover_all_plugins`. Surface `.errors` to a logger; do not
   silently drop them.
6. **Document the prefix and dataclass** in the relevant API package
   so plugin authors know what to write.

## 4. Migrating a registry-based domain

Given a domain `X` whose plugins live in `x_registry` (a
`cmk.ccc.plugin_registry.Registry` subclass — see
`packages/cmk-ccc/cmk/ccc/plugin_registry.py`):

1. **Add `PluginGroup.X`** to `_wellknown.py`.
2. **Define / reuse a plugin dataclass.** If today's "plugin" is a
   _class_ (e.g., a `WatoMode` subclass), introduce a dataclass that
   wraps the relevant fields (name, handler, permissions, …) — the
   target shape is data, not subclassing. The dataclass lives in a
   new (or existing) API subpackage at
   `cmk.<group>.<variant>` — see §2.1. Most
   migrations introduce a new `internal` variant.
3. **Define `entry_point_prefixes()`** for the new dataclass and
   expose it from the variant's `__init__.py` so backend code can
   import it as `cmk.<group>.<variant>.entry_point_prefixes`.
4. **Move plugins** to `cmk/plugins/<family>/<group_value>/`. Each
   former `x_registry.register(Foo)` site becomes a module-level
   `prefix_foo = X(name="foo", ...)`. Delete the registration call.
5. **Replace the loader.** Wherever code iterates `x_registry`, call
   `discover_all_plugins(PluginGroup.X, entry_point_prefixes(), ...)`
   and consume `.plugins` directly.
6. **Retire the `register()` cascade** (typically in
   `cmk/gui/main_modules.py` and `cmk/gui/community_registration.py`).
   The registry instance itself often _also_ serves as the global
   that downstream code reads from; replacing every read site with a
   plain argument is the desirable end state but is out of scope for
   the discovery migration. It's fine to keep the registry as a
   read-only singleton populated from the discovery result, and tackle
   the read-side refactor separately.
7. **Verify**: `bazel test` for the affected domain; exercise the
   feature end-to-end (CLI / GUI); compare plugin count before vs.
   after.

### Common pitfalls

- **Hard-coded module list smell.** Reaching for
  `discover_plugins_from_modules` with a literal list of module names
  means plugins aren't yet under `cmk/plugins/<family>/<group>/`.
  Acceptable as a transitional step — leave a clear `TODO` and a
  tracking ticket.
- **Plugin missing `.name`.** `_PluginProtocol` requires it. The
  collector keys deduplication on `(type, name)`, so name uniqueness
  matters across the _whole_ group, not just per-file.
- **Mutating the discovery result.** `DiscoveredPlugins.plugins` is a
  `Mapping`; treat it as immutable. If callers want add/remove
  semantics they're rebuilding the registry — push back.
- **Swallowing `.errors`.** The whole point of discovery is that
  failures are explicit. Always log or raise; never drop.
- **Plugin imports from a consumer module.** Plugin files in
  `cmk/plugins/<family>/<group>/` ideally only import from
  `cmk.<group>.<variant>` and stdlib. An import from `cmk.base.*`,
  `cmk.gui.*`, or `cmk.ccc.*` is undesirable but currently has to
  be accepted sometimes. It **might** indicate that the type or helper
  the plugin needs is on the wrong side of the API boundary — consider moving
  it into the API package. See §2.1.

## 5. Half-migrated domains (concrete deviation list)

Three recent migrations are discovery-flavoured but not yet aligned
with the target pattern. Each is a tractable follow-up.

### 5.1 Modes — `cmk/gui/watolib/mode/_registry.py`

- **Status:** **No discovery.** `mode_registry.register(Cls)` is
  called from feature-specific registration functions; modes are
  classes inheriting `WatoMode`, scattered across `cmk/gui/<feature>/`.
  The cascade is wired through `cmk/gui/community_registration.py` /
  `cmk/gui/common_registration.py`.
- **Deviations:**
  - Pure registry — no call to anything in this package.
  - No `PluginGroup.MODES`.
  - Plugins live outside `cmk/plugins/`.
  - Plugin objects are _classes_, not data.
- **To finish:** largest of the three. Add `PluginGroup.MODES`,
  introduce a `Mode` dataclass (name, page handler, permissions, …),
  move definitions to `cmk/plugins/<family>/modes/`, replace the
  `mode_registry` cascade with one `discover_all_plugins` call and
  delete the registry.

### 5.2 Automations — `cmk/base/automations/automations.py:97`

- **Status:** uses `discover_plugins_from_modules` with a hard-coded
  list of five module names. The file already carries a TODO comment
  noting that this list needs to go away.
- **Deviations:**
  - No `PluginGroup.AUTOMATIONS`; the listed modules don't live under
    `cmk/plugins/`.
  - Plugins live in `cmk/base/`, mixed with non-plugin code.
  - GUI side has a _separate_ registry (`AutomationCommand` in
    `cmk/gui/watolib/automation_commands.py`) that wasn't migrated
    together.
- **To finish:** add `PluginGroup.AUTOMATIONS`, move automation
  definitions into `cmk/plugins/<family>/automations/`, switch to
  `discover_all_plugins`. Decide separately whether to unify the GUI
  `AutomationCommand` domain with the base one or leave them
  distinct.

### 5.3 Post-rename-site — `cmk/post_rename_site/main.py:99`

- **Status:** `discover_plugins_from_modules` over a hard-coded
  namespace list assembled by `discover_submodules`. The file carries
  a TODO comment to switch to the generic `cmk.plugins.*.<GROUP>`
  mechanism once all plugins are moved.
- **Deviations:**
  - No `PluginGroup` entry.
  - Plugins split between `cmk/post_rename_site/plugins/actions/`
    (legacy) and `cmk/plugins/{dcd,otel_collector}/post_rename_site/`
    (already moved).
  - `discover_submodules` does not enforce the
    `<family>/<group>/` convention.
- **To finish:** smallest of the three. Add a `PluginGroup` member
  (directory value `post_rename_site`), move the remaining legacy
  plugins (including the non-free siblings under
  `cmk/post_rename_site/nonfree/...`) into
  `cmk/plugins/<family>/post_rename_site/`, switch the loader to
  `discover_all_plugins`.

## 6. Registry → discovery, at a glance

| Registry world                              | Discovery world                                    |
| ------------------------------------------- | -------------------------------------------------- |
| `cmk.ccc.plugin_registry.Registry` subclass | `PluginGroup` member + plugin dataclass            |
| `registry.register(Cls)` at import time     | module-level `prefix_name = Cls(name="…", …)`      |
| `register()` cascade in `main_modules.py`   | one `discover_all_plugins` call                    |
| Imports drive registration (silent on miss) | namespace scan drives discovery (errors collected) |
| Lookup: `registry["name"]`                  | `{p.name: p for p in plugins.values()}["name"]`    |
| Plugin lives wherever its feature does      | Plugin lives in `cmk/plugins/<family>/<group>/`    |
| Plugin is a subclass                        | Plugin is a dataclass instance                     |
