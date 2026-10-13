#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""In-site helper that seeds legacy ``user_sync`` values into a site's ``sites.mk``.

Runs as the site user under the site's own Python (via ``Site.python_helper``): it
imports the site's ``cmk`` modules and writes the site config through the same
``store`` helper the product uses, so the seeded file is byte-shaped exactly like one
the product wrote. Reads its instructions as JSON on stdin — see
``seed_legacy_user_sync`` in ``user_sync_migration.py`` for the payload shape.

JSON carries neither tuples nor a usable ``None``, so two values are encoded on the
wire and restored by :func:`_coerce`: ``("list", [...])`` arrives as
``["list", [...]]``, and ``"disabled"`` stands in for a legacy ``user_sync = None``
(the "Disable automatic user synchronization" choice) — a value the payload cannot
express directly, because ``None`` there already means "not provided".
"""

import json
import sys
from copy import deepcopy
from typing import Any, Final

from cmk.ccc import store
from cmk.utils import paths

# Wire marker for a legacy ``user_sync = None``. Not a legacy value itself (those are
# "all", "master", ("list", [...]) and None), so it cannot collide with one.
DISABLED_MARKER: Final = "disabled"

SiteCfg = dict[str, Any]


def _cfg_path() -> Any:
    return paths.omd_root / "etc/check_mk/multisite.d/sites.mk"


def _load_sites() -> dict[str, SiteCfg]:
    ns: dict[str, Any] = {"sites": {}}
    path = _cfg_path()
    if path.exists():
        exec(path.read_text(), ns)  # nosec B102 # the site's own config, written by us
    return dict(ns.get("sites", {}))


def _coerce(value: Any) -> Any:
    """Restore the wire encoding to the legacy value the migration expects."""
    if value == DISABLED_MARKER:
        return None
    if isinstance(value, list) and len(value) == 2 and value[0] == "list":
        return ("list", list(value[1]))
    return value


def _strip_new_fields(cfg: SiteCfg) -> None:
    """Drop the post-migration fields so a seeded entry carries ONLY the legacy
    ``user_sync``.

    The migration only fills a new field when it is absent, so an inherited value here
    would mask its own derivation (the ``presets`` entries deliberately keep them, to
    assert the opposite).
    """
    cfg.pop("authentication_connections", None)
    cfg.pop("user_attribute_sync_connections", None)


def _make_clone(template: SiteCfg, site_id: str, port: int) -> SiteCfg:
    clone = deepcopy(template)
    clone["id"] = site_id
    clone["alias"] = site_id
    clone["socket"] = ("tcp", {"address": ("127.0.0.1", port), "tls": ("plain_text", {})})
    clone["replication"] = "slave"
    clone["multisiteurl"] = f"http://127.0.0.1/{site_id}/check_mk/"
    clone.pop("secret", None)
    _strip_new_fields(clone)
    return clone


def _seed(payload: dict[str, Any]) -> None:
    own_site_id = payload["own_site_id"]
    sites = _load_sites()
    template = deepcopy(sites[own_site_id])

    if "own" in payload:
        own_cfg = sites[own_site_id]
        _strip_new_fields(own_cfg)
        own_cfg["user_sync"] = _coerce(payload["own"])

    # Set a legacy user_sync on EXISTING entries (e.g. a real connected remote's
    # entry) in place, without cloning — so the live connection is preserved.
    for site_id, value in payload.get("existing", {}).items():
        if site_id in sites:
            _strip_new_fields(sites[site_id])
            sites[site_id]["user_sync"] = _coerce(value)

    for entry in payload.get("remotes", []):
        clone = _make_clone(template, entry["site_id"], entry["port"])
        clone["user_sync"] = _coerce(entry["user_sync"])
        sites[entry["site_id"]] = clone

    # Entries that ALREADY carry the new fields (e.g. an admin migrated them by hand)
    # alongside a stale legacy user_sync: the migration must drop user_sync but leave
    # the pre-existing new fields untouched (fill-only-if-absent).
    for entry in payload.get("presets", []):
        clone = _make_clone(template, entry["site_id"], entry["port"])
        clone["user_sync"] = _coerce(entry["user_sync"])
        clone["authentication_connections"] = [
            tuple(e) for e in entry["authentication_connections"]
        ]
        clone["user_attribute_sync_connections"] = entry["user_attribute_sync_connections"]
        sites[entry["site_id"]] = clone

    path = _cfg_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save_to_mk_file(path, key="sites", value=sites)


if __name__ == "__main__":
    _seed(json.loads(sys.stdin.read()))
