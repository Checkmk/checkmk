# cmk-flags

Experimental flags for Checkmk: site-wide, file-backed boolean feature toggles.

An experimental flag lets developers merge unfinished work to the `master` and `2.5`
branches without exposing it to users.
Each flag is a field on the single `ExperimentalFlagConfig` model and is persisted as
JSON in `$OMD_ROOT/etc/check_mk/release_flag.json`.

This package owns only the flag _model_ and its loader.
Surfacing flags in the GUI, generating site settings, and syncing them to remote
sites live in the consuming components, not here.

> **Legacy naming:** this package, and the flags it defines, used to be called
> "release flags" — the code and docs have since been renamed to "experimental
> flags", but `CONFIG_FILENAME` still points at `release_flag.json`, and the
> `ConfigDomain` ident consuming components register it under is still
> `"release_flags"`. Both are replicated verbatim to remote sites during
> `activate_changes`, so a straight rename breaks any distributed setup where
> the central and a remote site run different versions (one side raises
> `KeyError` looking the other's ident/file up). That happened once already
> (`#22265`, reverted 2026-09-09) and is deferred to a proper dual-registration
> alias at the next major version boundary — see CMK-38694.

## Design

A flag is declared as a field on `ExperimentalFlagConfig` via `experimental_field()`, which
fixes the type to `bool`, defaults it to `False`, and attaches the metadata that
keeps flags from rotting:

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

The public API is `load_experimental_flags`, `ExperimentalFlagConfig`, and
`CONFIG_FILENAME` (still `"release_flag.json"`, see above). `experimental_field`
is exported for use inside the model declaration.
