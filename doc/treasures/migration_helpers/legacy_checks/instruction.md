# Check Plugin Migration Guide

Your mission is to migrate check plugins from legacy API to Check API v2, working autonomously.

## AI Agent Instructions

**Autonomous Operation Mode**:

- **Complete both commits**: For each plugin, complete Commit 1 AND Commit 2 before moving to the next
- **Commit changes yourself**: Use git to commit after each step (Commit 1, then Commit 2)
- **Process 10 plugins**: Continue until you've completed the plugins to migrate or encounter a problem
- **One plugin at a time**: Fully complete both commits for one plugin before starting the next

## Overview

**Two-Commit Process**: Migration always happens in two separate commits to facilitate code review:

1. **Commit 1 - Migrate in place**: Convert code to new API while keeping the file in `cmk/base/legacy_checks/`
2. **Commit 2 - Move to final location**: Move file to `cmk/plugins/<family>/agent_based/` and update all references

**Reference commits**: `8797ecb2a10` (migrate in place) and `5809af00e3a` (move to final location) demonstrate this process for `mssql_instance`.

## What This Migration Does

Legacy check plugins use an older, less type-safe API. The migration:

- **Converts to modern Python**: Type hints, f-strings, modern idioms
- **Improves type safety**: Typed enums (e.g., `State.OK` instead of `0`)
- **Modernizes structure**: Classes (`Service`, `Result`, `Metric`) instead of tuples
- **Enhances organization**: Family-specific locations under `cmk/plugins/<family>/`
- **Maintains compatibility**: Plugin behavior remains identical

## Key Concepts

### The \_discover.py Hack

During Commit 1, the plugin lives in the old location but uses the new API. To make it discoverable:

1. Add the module path to `_NOT_YET_MOVED_PLUGINS` in `cmk/checkengine/plugin_backend/_discover.py`
2. This is a **temporary hack** for one commit only
3. Revert this change immediately in Commit 2 when moving the file

## Step-by-Step Migration Process

### Commit 1: Migrate in Place

**Goal**: Convert the plugin to use Check API v2 while keeping it in the legacy location.

1. **Run automated migration script**:

   ```bash
   scripts/run-uvenv doc/treasures/migration_helpers/legacy_checks/to_v2.py cmk/base/legacy_checks/<plugin_name>.py
   ```

   This handles most boilerplate conversions but **manual fixes are always required**.

2. **Manual code improvements** (required):
   - **Fix State types**: Change `state` argument in `Result()` to use `State` enum (e.g., `State.OK`, `State.WARN`)
     - Note: `params` may still contain integers (0, 1, 2, 3) - this is expected
   - **Adjust calls to check_levels**: The new check_levels function is a generator. Its calls must become `yield from check_levels(...)` but otherwise remain unchanged.
   - **Run mypy and fix errors**:
     ```bash
     scripts/run-uvenv mypy cmk/base/legacy_checks/<plugin_name>.py tests/unit/cmk/base/legacy_checks/
     ```
   - **Check default parameters**: Include them if and only if there's a ruleset for the plugin
   - **Modernize discovery function**:
     - Yield `Service` objects directly (no intermediate lists)
     - Use f-strings instead of `%` or `.format()`
     - Remove `parameters=None` (it's the default)
   - **Other improvements**: Apply modern Python idioms as needed

3. **Temporarily enable plugin discovery**:
   - Edit `cmk/checkengine/plugin_backend/_discover.py`
   - Add the module path to `_NOT_YET_MOVED_PLUGINS` tuple:
     ```python
     _NOT_YET_MOVED_PLUGINS = (
         "cmk.base.legacy_checks.<plugin_name>",
     )
     ```
   - **Important**: This is a temporary hack for one commit only!

4. **Validate changes**:
   Run the following command and fix all potential findings. Repeat this until all issues are fixed.

   ```bash
   ./doc/treasures/migration_helpers/legacy_checks/validation.sh
   ```

5. **Commit changes** with descriptive message (e.g., "migrate <plugin_name> I")

   Commit the changes using **individual** commands:

   ```bash
   git commit -am "migrate <plugin_name> I"
   ```

### Commit 2: Move to Final Location

**Goal**: Move the plugin to its final family-specific location and clean up all references.

1. **Revert the \_discover.py hack**:
   - Edit `cmk/checkengine/plugin_backend/_discover.py`
   - Remove the entry from `_NOT_YET_MOVED_PLUGINS` (set it back to empty)

2. **Move the plugin file**:
   - Destination: `cmk/plugins/<family>/agent_based/<plugin_name>.py`
   - Choose appropriate family (e.g., `mssql`, `oracle`, `aws`, `azure`, `netapp`, etc.)
   - Can merge into existing file or create new one (prefer new file)
   - Create the directory structure with `mkdir -p` if it doesn't exist (no need for `__init__.py` files)

3. **Move the manpage** (if exists):
   - From: `cmk/plugins/collection/checkman/<plugin_name>`
   - To: `cmk/plugins/<family>/checkman/<plugin_name>`

4. **Move the unit tests** (if there are any):
   - From: `tests/unit/cmk/base/legacy_checks/test_<derived from plugin_name>`
   - To: `tests/unit/cmk/plugins/<family>/agent_based/` (keep the base name)

5. **Update build configuration**:
   - Edit `cmk/legacy_checks_list.bzl`
   - Remove the plugin from the list

6. **Validate changes**:
   Run the following command and fix all potential findings. Repeat this until all issues are fixed.

   ```bash
   ./doc/treasures/migration_helpers/legacy_checks/validation.sh
   ```

7. **Commit changes** with descriptive message (e.g., "migrate <plugin_name> II")

   Commit the changes using **individual** commands:

   ```bash
   git add cmk/plugins/<family>
   git commit -am "migrate <plugin_name> II"
   ```

8. **Continue to next plugin**: After completing both commits, immediately start the next plugin

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

### Testing Failures

- **Problem**: Plugin not discovered after migration
  - **Solution**: Verify `_NOT_YET_MOVED_PLUGINS` is correctly set in Commit 1
- **Problem**: Tests fail after move to final location
  - **Solution**: Ensure `_NOT_YET_MOVED_PLUGINS` is reverted in Commit 2

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
