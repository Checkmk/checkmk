#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pre-seed the local-site Maps connection on fresh site creation.

So an operator opening *Customize → Maps → "Connections & daemon"* for the
first time already sees a working connection to their own site, this sample
config generator writes one ``maps_connections`` entry on ``omd create`` (it
runs once, via ``init_wato_datastructures``). The daemon's built-in local-site
fallback (``connection_service``) is the safety net for any site whose sample
config predates Maps.
"""

from typing import Literal, override, TypedDict

import cmk.utils.paths
from cmk.ccc.site import omd_site
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings_raw
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.sample_config import SampleConfigGenerator
from cmk.maps.gui._config_domain import CONFIG_VAR_CONNECTIONS


class _SocketTarget(TypedDict):
    socket_path: str


class _LivestatusOptions(TypedDict):
    """The Livestatus arm of the connection form's ``type`` cascade."""

    target: tuple[Literal["socket"], _SocketTarget]
    timeout: int
    checkmk_url: str
    metric_history: tuple[Literal["livestatus"], None]


class _ConnectionEntry(TypedDict):
    """One ``maps_connections`` entry in the nested FormSpec shape WATO stores.

    The daemon flattens this back into a ``ConnectionConfig``
    (``cmk.maps.backend.services.connection_forms``).
    """

    id: str
    label: str
    type: tuple[Literal["livestatus"], _LivestatusOptions]


def _local_connection_entry() -> _ConnectionEntry:
    """The ``maps_connections`` form-shape entry for this site's own Livestatus."""
    site = omd_site()
    return {
        "id": f"cmk_{site}",
        "label": f"Checkmk {site}",
        "type": (
            "livestatus",
            {
                "target": (
                    "socket",
                    {"socket_path": str(cmk.utils.paths.omd_root / "tmp" / "run" / "live")},
                ),
                "timeout": 10,
                "checkmk_url": f"/{site}/check_mk",
                "metric_history": ("livestatus", None),
            },
        ),
    }


class SampleConfigGeneratorMapsConnections(SampleConfigGenerator):
    """Seed the local-site connection into ``maps_connections``."""

    @classmethod
    @override
    def ident(cls) -> str:
        return "maps_connections"

    @classmethod
    @override
    def sort_index(cls) -> int:
        # After the basic WATO config (11); the value is independent of the rest.
        return 80

    @override
    def generate(self, tree: FolderTree) -> None:
        # The writer writes EVERY enabled domain's file, so a partial dict would
        # blank out the settings other generators already wrote (e.g. the site-CA
        # trust from ConfigGeneratorBasicWATOConfig, sort_index 11 < 80). Load the
        # current settings first and merge, like every other caller. The
        # connections themselves land in maps.d/wato/global.mk, not in
        # multisite.d: the writer routes each variable to its ConfigVariable's
        # primary_domain, which is ConfigDomainMaps here.
        settings = dict(load_configuration_settings())
        settings[CONFIG_VAR_CONNECTIONS] = [_local_connection_entry()]
        # The raw writer, like the core sample-config generators: seeding a fresh
        # site is not a user-made settings change, so the domains must neither get
        # the chance to reject it nor see it as one (skip_cse_edition_check keeps
        # the entry from being filtered away before any admin could activate it).
        save_global_settings_raw(settings, skip_cse_edition_check=True)
