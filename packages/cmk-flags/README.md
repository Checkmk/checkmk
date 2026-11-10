# cmk-flags

Experimental flags for Checkmk: site-wide, file-backed boolean feature toggles.

An experimental flag lets developers merge unfinished work to the `master` and `2.5`
branches without exposing it to users.
Each flag is a field on the single `ExperimentalFlagConfig` model and is persisted as
JSON in `$OMD_ROOT/etc/check_mk/release_flag.json`.

This package owns only the flag _model_ and its loader.
Surfacing flags in the GUI, generating site settings, and syncing them to remote
sites live in the consuming components, not here.

> **Legacy naming:** flags used to be called "release flags". The code is now
> named "experimental flags", but the file (`release_flag.json`) and the
> `ConfigDomain` ident (`"release_flags"`) keep the old names on purpose.
> See [Version compatibility](#version-compatibility).

## Design

A flag is declared as an `Annotated[bool, experimental_field(...)]` field on
`ExperimentalFlagConfig`. `experimental_field()` defaults it to `False` and
attaches the metadata that keeps flags from rotting:

- `description` — what the flag gates
- `remove_ticket` — the ticket tracking its removal
- `remove_after` — the version by which the flag must be gone
- `owner` — who is responsible for removing it

`ExperimentalFlagConfig` is `frozen=True` (flags are read-only at runtime) and
`extra="ignore"`, so deleting a flag does not break sites whose on-disk config
still names it.

A test (`test_no_expired_flags`) compares every flag's `remove_after` against the
current Checkmk version and fails once a flag outlives its deadline — the feature
must then be made permanent by deleting the flag, or the gated code removed.

## Usage

Declare a flag as a field on `ExperimentalFlagConfig` in `cmk/flags/_config.py`
using `experimental_field()`; the class docstring there carries the canonical
declaration example.

Read flags at runtime — missing file yields an all-off config:

```python
from pathlib import Path

from cmk.flags import load_experimental_flags

flags = load_experimental_flags(Path("/omd/sites/mysite/etc/check_mk"))
if flags.new_monitoring_views:
    ...
```

The GUI shows the flags in the global settings only on development sites, as
defined by `is_development_site()` in `cmk/gui/experimental_flags/global_config.py`.
Flags already set in `release_flag.json` stay in effect either way.

A changed flag takes effect only once it is activated, and discarding changes reverts it.

The public API is `load_experimental_flags`, `ExperimentalFlagConfig`, and
`CONFIG_FILENAME` (still `"release_flag.json"`, see above). `experimental_field`
is exported for use inside the model declaration.

## Version compatibility

The package was introduced in 2.5.0p8 and renamed later. In a distributed setup,
the central site and the remote sites may run different versions: different 2.5.0
patch releases, or 2.5.0 and 3.0.0 during an update. This section tracks which
combinations work.

### Wire contract

These names cross site boundaries during `activate_changes` (the file only in
2.5.0p8 to p14, see below). They must stay the same on every branch:

| Name                 | Value                   | Where it is used                                                                    |
| -------------------- | ----------------------- | ----------------------------------------------------------------------------------- |
| `ConfigDomain` ident | `release_flags`         | Domain requests the central site sends to remotes                                   |
| Config file          | `release_flag.json`     | `etc/check_mk/release_flag.json`, replicated to remote sites only in 2.5.0p8 to p14 |
| Flag field names     | e.g. `exp_ai_assistant` | JSON keys in that file                                                              |

Renaming the ident or the file makes remote sites on the other version fail the
activation with a `KeyError`. Werk #22265 did that and was reverted before any
release. A rename needs an alias that spans a major version (CMK-38694). On
master, `ABCConfigDomain.previous_idents()` provides that alias for the ident
(CMK-38543); 2.5.0 does not have it.

Renaming a flag is a removal plus a new flag: the old key is ignored and the new
flag starts off.

### History

| Version        | Change                                                                                                                                                           | Wire change               |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| 2.5.0p8        | Package, `release_flags` config domain, replication of `release_flag.json` (werk #19980). No flags yet.                                                          | New                       |
| 2.5.0p13       | Flag `exp_relay_active_checks`                                                                                                                                   | New key                   |
| 2.5.0p14       | Flag `exp_ai_assistant`. Settings section renamed to "Experimental flags (for testing only)". Werk #22265 (ident rename) added and reverted in the same release. | New key                   |
| 2.5.0p15       | Python API renamed from `release_*` to `experimental_*`. Flags are no longer synced to remote sites.                                                             | File no longer replicated |
| 2.5.0p18       | Flag `exp_relay_active_checks` removed: active checks on relays are released (werk #20175)                                                                       | Key ignored               |
| 3.0.0 (master) | Has the package from the start, with the `experimental_*` API. Flag `exp_trial_mode_selection` exists only here.                                                 | —                         |

3.0.0 is not released yet (state 2026-11-10).

### Mixed versions

| Central site                | Remote site                | Result                                                                                                                                                           |
| --------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.5.0p8 or newer, or 3.0.0  | 2.5.0p7 or older           | Breaks when a flag is changed: the remote site has no `release_flags` domain and fails the activation with a `KeyError`. Update the remote site first.           |
| 2.5.0p7 or older            | 2.5.0p8 or newer, or 3.0.0 | Works. The central site syncs no flags, so the remote site keeps its own file (no file: all flags off).                                                          |
| 2.5.0p15 or newer, or 3.0.0 | 2.5.0p8 or newer, or 3.0.0 | Works. No flags are synced: each site keeps its own file (no file: all flags off).                                                                               |
| 2.5.0p8 to p14              | 2.5.0p8 or newer, or 3.0.0 | The central site syncs its file, but the remote site resets it to the default flags on activation and restarts. 2.5.0p15 fixed this by not syncing flags at all. |

Remote sites do not get the central site's flags. Each site only knows the
flags its own version declares: a key the site does not declare is ignored
(`extra="ignore"`).

### Backporting a flag

Declare the flag with the same field name on master and 2.5.0, and add the
release to the history table above on both branches. Import the API with the
names of the target branch: `release_*` before 2.5.0p15, `experimental_*` from
2.5.0p15 and on master.
