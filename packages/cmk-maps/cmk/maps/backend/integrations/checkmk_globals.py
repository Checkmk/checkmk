#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Read the Maps daemon's runtime settings from its config domain's files.

The daemon's runtime knobs are native Checkmk *global settings* owned by the
Maps config domain (``ConfigDomainMaps``, ident ``maps``): ``maps_connections``,
``maps_log_level`` and ``maps_state_refresh_interval``. Like every other Checkmk
daemon (liveproxyd, dcd, mkeventd), WATO writes them to the daemon's *own*
directory ``etc/check_mk/maps.d/wato/`` — ``global.mk`` plus per-site
``sitespecific.mk`` — which a ReplicationPath ships to remote sites on Activate
Changes. We never read the GUI's ``multisite.d``. Map/object authoring
defaults are GUI-owned (a separate GUI-side config domain) and never read here.

Flask-free, the same direct ``exec`` pattern :mod:`checkmk_sites` uses for
``sites.mk``. ``sitespecific.mk`` is loaded *after* ``global.mk`` into the same
namespace, so a remote site's per-site override wins over the replicated central
value.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk as _cmk_integration
from cmk.maps.shared import config_vars as maps_config_vars

log = logging.getLogger(__name__)

# The daemon-side names of the GUI↔daemon runtime globals; the string values are
# the shared contract (cmk.maps.shared.config_vars), re-exported here so callers
# read them off the daemon's own globals module.
VAR_CONNECTIONS = maps_config_vars.VAR_CONNECTIONS
VAR_LOG_LEVEL = maps_config_vars.VAR_LOG_LEVEL
VAR_STATE_REFRESH_INTERVAL = maps_config_vars.VAR_STATE_REFRESH_INTERVAL

# Map/object authoring defaults are GUI-owned (a separate GUI-side config
# domain) and never read here — the daemon carries only its runtime knobs.
_MAPS_VARS = (
    VAR_CONNECTIONS,
    VAR_LOG_LEVEL,
    VAR_STATE_REFRESH_INTERVAL,
)

# Unique marker for "not present in any .mk file" (distinct from a configured value).
_ABSENT = object()


def _maps_wato_dir() -> Path:
    # The Maps config domain's own directory (ConfigDomainMaps.config_dir()), NOT
    # the GUI's multisite.d — the daemon reads its own config like every other
    # Checkmk daemon (liveproxyd/dcd/mkeventd).
    return Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "maps.d" / "wato"


def load_maps_globals() -> dict[str, object]:
    """Return the effective Maps global settings, ``None`` per var if unset.

    Reads ``global.mk`` then ``sitespecific.mk`` into one namespace, so a remote
    site's per-site override wins over the replicated central value — the same
    merge the GUI does. ``None`` (var absent from both files) lets the caller
    fall back to its own defaults rather than treat "never configured" as a
    value.
    """
    wato_dir = _maps_wato_dir()
    ns: dict[str, object] = dict.fromkeys(_MAPS_VARS, _ABSENT)
    for name in ("global.mk", "sitespecific.mk"):
        path = wato_dir / name
        if not path.is_file():
            continue
        try:
            ns = _cmk_integration.exec_mk_file(path, ns)
        except Exception:
            log.exception("Failed to parse %(path)s", {"path": path})
    return {var: (None if ns.get(var, _ABSENT) is _ABSENT else ns[var]) for var in _MAPS_VARS}
