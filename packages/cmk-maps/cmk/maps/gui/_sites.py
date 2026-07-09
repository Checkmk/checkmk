#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Prepared Livestatus site specs for the Maps daemon.

The daemon fans its Livestatus queries out across the distributed setup, but
normalising the site specs for that (proxy sockets, the local socket path,
tls/cache hints) is GUI logic. Instead of the daemon re-implementing it, the
GUI runs its own machinery (``cmk.gui.sites``) and writes the ready-to-use specs
to ``etc/check_mk/maps.d/sitespecs.mk``.

The specs are (re)written on two triggers: ``sites-saved`` (so a distributed
setup takes effect the moment the connection is saved, like liveproxyd) *and*
``pre-activate-changes`` (so the file lands in every activation's replication
snapshot). The activation trigger is what makes the specs appear for a
distributed setup that predates Maps — or one configured outside the WATO save
flow — without requiring a manual sites re-save; it mirrors how
:mod:`cmk.maps.gui._folders` regenerates the folder skeleton.

The file holds the *central* site's fan-out view and is deliberately not
replicated: on remote sites (and single-site setups) it is absent or empty,
which the daemon takes as "stay on the single-socket fast path".
"""

from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.site import SiteId
from cmk.gui import hooks, site_config
from cmk.gui.config import active_config
from cmk.gui.log import logger
from cmk.gui.sites import encode_socket_for_livestatus
from cmk.livestatus_client import SiteConfiguration, SiteConfigurations
from cmk.maps.shared.config_vars import VAR_SITE_SPECS


def site_specs_path() -> Path:
    return cmk.utils.paths.default_config_dir / "maps.d" / "sitespecs.mk"


def _for_livestatus(site_id: SiteId, site_spec: SiteConfiguration) -> SiteConfiguration:
    """Normalise a site spec for ``livestatus.MultiSiteConnection``.

    Mirrors ``cmk.gui.sites``' own (module-private) normalisation: encode the
    socket via the public ``encode_socket_for_livestatus`` helper (the same one
    the NagVis backend writer uses) and carry the proxy-cache / TCP-tls hint the
    connection needs. Kept here rather than widening the ``cmk.gui.sites`` API for
    a single caller; the socket encoding itself (the proxy/OMD-specific part) is
    the shared helper.
    """
    prepared = site_spec.copy()
    proxy = site_spec.get("proxy")
    socket = site_spec["socket"]
    if proxy is not None:
        prepared["cache"] = proxy.get("cache", True)
    elif isinstance(socket, tuple) and socket[0] in ("tcp", "tcp6"):
        prepared["tls"] = socket[1]["tls"]
    prepared["socket"] = encode_socket_for_livestatus(site_id, site_spec)
    return prepared


def _prepared_site_specs(sites: SiteConfigurations) -> dict[SiteId, SiteConfiguration]:
    enabled = site_config.enabled_sites(sites)
    if site_config.is_single_local_site(enabled):
        # Empty specs = the daemon's single-socket fast path; written (not
        # skipped) so shrinking a distributed setup back down takes effect.
        return {}
    return {site_id: _for_livestatus(site_id, spec) for site_id, spec in enabled.items()}


def _write_site_specs(sites: SiteConfigurations) -> None:
    path = site_specs_path()
    path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    store.save_to_mk_file(path, key=VAR_SITE_SPECS, value=_prepared_site_specs(sites))


def _on_sites_saved(sites: SiteConfigurations) -> None:
    # Builtin hooks propagate: a failure here would make the sites save itself
    # fail. Writing the daemon's fan-out view is not part of saving a connection,
    # and the activation hook below writes it again, so log and carry on.
    try:
        _write_site_specs(sites)
    except Exception:
        logger.exception(
            "Cannot write the Maps site specs to %(path)s", {"path": site_specs_path()}
        )


def _on_pre_activate_changes(*_args: object) -> None:
    # Regenerate from the current sites on every activation so an existing
    # distributed setup (one that predates Maps, or was configured outside the
    # WATO save flow) gets its fan-out specs without a manual sites re-save.
    # Non-fatal for the same reason as cmk.maps.gui._folders: Maps must not abort
    # an activation — a stale/missing file only costs the daemon its fan-out
    # (it falls back to the single-socket path).
    try:
        _write_site_specs(active_config.sites)
    except Exception:
        logger.exception(
            "Cannot write the Maps site specs to %(path)s", {"path": site_specs_path()}
        )


def register() -> None:
    hooks.register_builtin("sites-saved", _on_sites_saved)
    hooks.register_builtin("pre-activate-changes", _on_pre_activate_changes)
