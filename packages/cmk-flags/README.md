# cmk-flags

Release flags for Checkmk: site-wide, file-backed boolean feature toggles.

A release flag lets developers merge unfinished work to the `master` and `2.5`
branches without exposing it to users.
Each flag is a field on the single `ReleaseFlagConfig` model and is persisted as
JSON in `$OMD_ROOT/etc/check_mk/release_flag.json`.

This package owns only the flag _model_ and its loader.
Surfacing flags in the GUI, generating site settings, and syncing them to remote
sites live in the consuming components, not here.

## Design

A flag is declared as a field on `ReleaseFlagConfig` via `release_field()`, which
fixes the type to `bool`, defaults it to `False`, and attaches the metadata that
keeps flags from rotting:

- `description` — what the flag gates
- `remove_ticket` — the ticket tracking its removal
- `remove_after` — the version by which the flag must be gone
- `owner` — who is responsible for removing it

`ReleaseFlagConfig` is `frozen=True` (flags are read-only at runtime) and
`extra="ignore"`, so deleting a flag does not break sites whose on-disk config
still names it.

A test (`test_no_expired_flags`) compares every flag's `remove_after` against the
current Checkmk version and fails once a flag outlives its deadline — the feature
must then be made permanent by deleting the flag, or the gated code removed.

## Usage

Declare a flag as a field on `ReleaseFlagConfig` in `cmk/flags/_config.py`
using `release_field()`; the class docstring there carries the canonical
declaration example.

Read flags at runtime — missing file yields an all-off config:

```python
from pathlib import Path

from cmk.flags import load_release_flags

flags = load_release_flags(Path("/omd/sites/mysite/etc/check_mk"))
if flags.new_monitoring_views:
    ...
```

The public API is `load_release_flags`, `ReleaseFlagConfig`, and
`CONFIG_FILENAME` (`"release_flag.json"`); `release_field` is exported for use
inside the model declaration.
