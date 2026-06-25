#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Read the prepared distributed-monitoring site specs.

Normalising site specs for :class:`livestatus.MultiSiteConnection` (proxy
sockets, the local socket path, tls/cache hints) is GUI logic: the GUI runs
its own machinery on every site save and writes the ready-to-use specs to
``etc/check_mk/maps.d/sitespecs.mk`` (``cmk.maps.gui._sites`` — the same way
liveproxyd gets its site config). This module only reads them back.

A missing or empty file means "stay on the single-socket fast path": fresh
and single-site setups, and remote sites — the file holds the central site's
fan-out view and is deliberately not replicated.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk as _cmk_integration
from cmk.maps.shared.config_vars import VAR_SITE_SPECS

log = logging.getLogger(__name__)


def _site_specs_path() -> Path:
    return Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "maps.d" / "sitespecs.mk"


def sites_mk_mtime() -> float:
    """Return mtime of the site-specs file for cache invalidation, or 0.0 when absent."""
    return _cmk_integration.mtime_or_zero(_site_specs_path())


def load_sites() -> dict[str, dict[str, object]] | None:
    """Return the prepared site specs for ``MultiSiteConnection``.

    Returns ``None`` (= keep the single-socket fast path) when the specs file
    is missing, unparseable or empty.
    """
    p = _site_specs_path()
    if not p.is_file():
        return None
    try:
        raw = _cmk_integration.exec_mk_file(p, {VAR_SITE_SPECS: {}})[VAR_SITE_SPECS]
    except Exception:
        log.exception("Failed to parse %(path)s", {"path": p})
        return None
    if not isinstance(raw, dict) or not raw:
        return None
    return {str(site_id): dict(spec) for site_id, spec in raw.items()}
