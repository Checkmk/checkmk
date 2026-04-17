# Check Plugin Migration Guide

Your mission is to migrate check plugins from the legacy API to Check API v2, working autonomously.
You are an experienced python developer. You are methodical and patient.

## AI Agent Instructions

**Autonomous Operation Mode**:

- **Complete both commits**: For every individual plugin, complete Commit 1 AND Commit 2 before moving to the next
- **Commit changes yourself**: Use git to commit after each step (Commit 1, then Commit 2)
- **Standardized commit message titles**: Use the commit message titles "Legacy check migration: <name> I" and "Legacy check migration: <name> II"
- **One plugin at a time**: Fully complete both commits for one plugin before starting the next. Every Commit 1 must be immediately followed by a Commit 2.

## Overview

**Two-Commit Process**: Migration always happens in two separate commits to facilitate code review:

1. **Commit 1 - Migrate in place**: Convert code to new API while keeping the file in `cmk/legacy_checks/`
2. **Commit 2 - Move to final location**: Move file to `cmk/plugins/<family>/agent_based/` and update all references

**Reference commits**: `d366886d8ec` (migrate in place) and `f8d882421bb` (move to final location) demonstrate this process for `appdynamics_memory`.
If needed you can look for more reference commits by searching the latest merged commits using the standardized commit message title.

## What This Migration Does

Legacy check plugins use an older, less type-safe API. The migration:

- **Converts to modern Python**: Type hints, f-strings, modern idioms
- **Improves type safety**: Typed enums (e.g., `State.OK` instead of `0`)
- **Modernizes structure**: Classes (`Service`, `Result`, `Metric`) instead of tuples
- **Enhances organization**: Family-specific locations under `cmk/plugins/<family>/`
- **Maintains compatibility**: Plugin behavior remains identical

## Step-by-Step Migration Process

### Commit 1: Migrate in Place

**Goal**: Convert the plugin to use Check API v2 while keeping it in the legacy location.

1. **Run automated migration script**:

   ```bash
   scripts/run-uvenv doc/treasures/migration_helpers/legacy_checks/to_v2.py cmk/legacy_checks/<plugin_name>.py
   ```

   This handles most boilerplate conversions but **manual fixes are always required**.

2. **Manual code improvements** (required):
   - **Fix State types**: Change `state` argument in `Result()` to use `State` enum (e.g., `State.OK`, `State.WARN`)
     - Note: `params` may still contain integers (0, 1, 2, 3) - this is expected
   - **Adjust calls to check_levels**: The new check_levels function is a generator. Its calls must become `yield from check_levels(...)` but otherwise remain unchanged.
   - **Run mypy and fix errors**:
     ```bash
     scripts/run-uvenv mypy cmk/legacy_checks/<plugin_name>.py tests/unit/cmk/legacy_checks/
     ```
   - **Check default parameters**: Include them if and only if there's a ruleset for the plugin
   - **Modernize discovery function**:
     - Yield `Service` objects directly (no intermediate lists)
     - Use f-strings instead of `%` or `.format()`
     - Remove `parameters=None` (it's the default)
   - **Other improvements**: Apply modern Python idioms as needed
   - **Human in the loop**: Avoid changes like reorderings that increase the diff

3. **Temporarily enable plugin discovery**:
   - Editing `cmk/checkengine/plugin_backend/_discover.py` is no longer
     necessary

4. **Validate changes**:
   Run the following command and fix all potential findings. Repeat this until all issues are fixed.

   ```bash
   ./doc/treasures/migration_helpers/legacy_checks/validation.sh
   ```

   There **must not** be any preexisting issues. This command must succeed.

5. **Commit changes** with descriptive message following the standard pattern

   This step must only be done once the validation script in step 4 passed without any issues.
   Commit the changes using **individual** commands:

   ```bash
   git commit -am "Legacy check migration: <plugin_name> I"
   ```

### Commit 2: Move to Final Location

**Goal**: Move the plugin to its final family-specific location and clean up all references.

1. **Move the plugin file**:
   - Destination: `cmk/plugins/<family>/agent_based/<plugin_name>.py`
   - Choose appropriate family (e.g., `mssql`, `oracle`, `aws`, `azure`, `netapp`, etc.)
   - Can merge into existing file or create new one (prefer new file)
   - Create the directory structure with `mkdir -p` if it doesn't exist (no need for `__init__.py` files)

2. **Move the manpage** (if exists):
   - From: `cmk/plugins/collection/checkman/<plugin_name>`
   - To: `cmk/plugins/<family>/checkman/<plugin_name>`

3. **Move the unit tests** (if there are any):
   - From: `tests/unit/cmk/legacy_checks/test_<derived from plugin_name>`
   - To: `tests/unit/cmk/plugins/<family>/agent_based/` (keep the base name)

4. **Validate changes**:
   Run the following command and fix all potential findings. Repeat this until all issues are fixed.

   ```bash
   ./doc/treasures/migration_helpers/legacy_checks/validation.sh
   ```

5. **Commit changes** with descriptive message following the standart pattern

   Commit the changes using **individual** commands:

   ```bash
   git add cmk/plugins/<family>
   git commit -am "Legacy check migration: <plugin_name> II"
   ```

## Moving a Plugin Family to `packages/cmk-plugins`

Some families live in `packages/cmk-plugins/` rather than `cmk/plugins/`. When
moving a family there (or creating a new one), the BUILD system requires several
files that don't exist in `cmk/plugins/` and are easy to miss:

1. **`py.typed` marker** — empty PEP 561 file in the family root:

   ```bash
   touch packages/cmk-plugins/cmk/plugins/<family>/py.typed
   ```

2. **`requirements.in-<family>`** — lists pip dependencies; empty for families
   with no third-party requirements (most SNMP/agent-based families):

   ```bash
   touch packages/cmk-plugins/requirements.in-<family>
   ```

3. **`tests/cmk/plugins/<family>/OWNERS`** — mirrors the plugin's OWNERS file.
   Copy from `cmk/plugins/<family>/OWNERS` and adjust paths as needed.

4. **BUILD entry** — add `py_library` and `py_test` targets to
   `packages/cmk-plugins/BUILD`. Use the `ipmi` entry as a template for
   SNMP/agent-based families with no external pip deps.

Verify the build succeeds after making these changes:

```bash
bazel build //packages/cmk-plugins/...
```

## Common Issues and Solutions

### Type Issues

- **Problem**: `params` contains integers but `State` expects enum
  - **Solution**: Keep integers in params; only convert when creating `Result(state=State.OK)`
- **Problem**: mypy complains about missing types in plugin definitions
  - **Solution**: Add complete type annotations to all function signatures

### Discovery Function

- **Anti-pattern**: Building lists then returning them
  - **Better**: Directly yield `Service` objects
- **Anti-pattern**: String formatting with `%` or `.format()`
  - **Better**: Use f-strings

## Plugin Family Categories

Choose the appropriate family when moving files in Commit 2.
If there are multiple legacy checks with the same prefix n their name,
this likely the family.

**Storage**: `netapp`, `emc`, `hitachi`, `ibm`, `oracle`
**Virtualization**: `vmware`, `hyperv`, `proxmox`
**Cloud**: `aws`, `azure`, `gcp`
**Database**: `mssql`, `mysql`, `postgres`, `mongodb`, `oracle`
**Network**: `cisco`, `juniper`, `hp`, `huawei`, `fortinet`
**Applications**: `apache`, `nginx`, `mail`, `sap`
**Hardware**: `dell`, `hp`, `fujitsu`, `supermicro`
**Security**: `mcafee`, `symantec`, `firewall`
**Monitoring**: `nagios`, `icinga`, `checkmk`

If unsure, look at existing plugin structure or ask for guidance.
