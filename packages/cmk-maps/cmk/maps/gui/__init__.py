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
from cmk.gui.watolib.mode import ModeRegistry
from cmk.gui.watolib.sample_config import SampleConfigGeneratorRegistry
from cmk.maps.gui import (
    _config_variables,
    _folders,
    _permissions,
    _settings_modes,
    _sites,
)
from cmk.maps.gui._cfg_import import AjaxMapsParseCfg
from cmk.maps.gui._commands import AjaxMapsCommand
from cmk.maps.gui._config_domain import ConfigDomainMaps
from cmk.maps.gui._form_schemas import AjaxMapsFormParse, AjaxMapsFormSchema
from cmk.maps.gui._images import (
    AjaxMapsBackgroundDelete,
    AjaxMapsBackgroundUpload,
    AjaxMapsImageDelete,
    AjaxMapsImageUpload,
)
from cmk.maps.gui._main_menu import monitor_menu_topics
from cmk.maps.gui._pages import AjaxMapsTicket
from cmk.maps.gui._sample_config import SampleConfigGeneratorMapsConnections
from cmk.maps.gui.pagetype import MapPage

__all__ = ["register", "monitor_menu_topics"]


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    page_registry: PageRegistry,
    config_domain_registry: ConfigDomainRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
    replication_path_registry: ReplicationPathRegistry,
    sample_config_generator_registry: SampleConfigGeneratorRegistry,
    mode_registry: ModeRegistry,
) -> None:
    _permissions.register(permission_section_registry, permission_registry)
    # Not pagetypes.declare(): the registry it fills also drives the Customize
    # menu, whose entry would link to the not-yet-merged maps.py. Swap back once
    # that page exists.
    MapPage.declare_overriding_permissions()
    page_registry.register(PageEndpoint("ajax_maps_ticket", AjaxMapsTicket()))
    # Map CRUD is the official REST API (cmk.maps.rest_api) and every read-only
    # SPA lookup is an internal REST endpoint, so only these remain AjaxPages:
    # the two uploads (the versioned framework has no multipart support) plus the
    # endpoints whose request context is the point — .cfg parsing, commands, form
    # schemas, and the page that mounts the SPA.
    page_registry.register(PageEndpoint("ajax_maps_parse_cfg", AjaxMapsParseCfg()))
    page_registry.register(PageEndpoint("ajax_maps_image_upload", AjaxMapsImageUpload()))
    page_registry.register(PageEndpoint("ajax_maps_image_delete", AjaxMapsImageDelete()))
    page_registry.register(PageEndpoint("ajax_maps_background_upload", AjaxMapsBackgroundUpload()))
    page_registry.register(PageEndpoint("ajax_maps_background_delete", AjaxMapsBackgroundDelete()))
    page_registry.register(PageEndpoint("ajax_maps_command", AjaxMapsCommand()))
    page_registry.register(PageEndpoint("ajax_maps_form_schema", AjaxMapsFormSchema()))
    page_registry.register(PageEndpoint("ajax_maps_form_parse", AjaxMapsFormParse()))
    maps_domain = ConfigDomainMaps()
    config_domain_registry.register(maps_domain)
    _config_variables.register(config_variable_group_registry, config_variable_registry)
    _settings_modes.register(mode_registry)
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
