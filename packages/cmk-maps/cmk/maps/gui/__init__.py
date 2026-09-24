#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI integration for Checkmk Maps.

Replaces the standalone MKP's runtime monkeypatch plugins with a regular,
registry-based GUI module: it declares the Maps permissions and the
session-authenticated endpoints backing the SPA.
"""

import cmk.utils.paths
from cmk.gui import pagetypes
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.permissions import (
    PermissionRegistry,
    PermissionSectionRegistry,
)
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
)
from cmk.gui.watolib.sample_config import SampleConfigGeneratorRegistry
from cmk.maps.gui import (
    _config_variables,
    _folders,
    _main_menu,
    _permissions,
    _settings_page,
    _sites,
)
from cmk.maps.gui._config_domain import ConfigDomainMaps
from cmk.maps.gui._pages import ShowMapsPage
from cmk.maps.gui._sample_config import SampleConfigGeneratorMapsConnections
from cmk.maps.gui.pagetype import MapPage

__all__ = ["register"]


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    page_registry: PageRegistry,
    config_domain_registry: ConfigDomainRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
    replication_path_registry: ReplicationPathRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
) -> None:
    _permissions.register(permission_section_registry, permission_registry)
    # No page_handlers on MapPage, so declare() registers no generic pagetype
    # list/edit pages: that UI stays maps-own (the SPA via maps.py).
    pagetypes.declare(MapPage)
    # The page mounting the SPA: everything the SPA calls is a REST endpoint
    # (map CRUD the official ``cmk.maps.rest_api``, everything else the internal
    # family in ``cmk.maps.rest_api.internal``), reached through the generated,
    # typed client.
    page_registry.register(PageEndpoint("maps", ShowMapsPage()))
    _settings_page.register(page_registry)
    maps_domain = ConfigDomainMaps()
    config_domain_registry.register(maps_domain)
    _config_variables.register(config_variable_group_registry, config_variable_registry)
    # Ships the domain's config dir (maps.d/wato) to the remote sites, so their
    # daemon reads the same settings; see cmk.maps.gui._config_domain.
    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident=maps_domain.ident(),
            site_path=str(maps_domain.config_dir().relative_to(cmk.utils.paths.omd_root)),
        )
    )
    sample_config_generator_registry.register(SampleConfigGeneratorMapsConnections)
    # Both write a file the daemon consumes instead of re-implementing GUI logic:
    # the Livestatus site specs and the SETUP-folder skeleton.
    _sites.register()
    _folders.register()
    # Contributes the viewable maps to the Monitor menu through a registry, so
    # cmk.gui's menu builders need no Maps import.
    _main_menu.register()
