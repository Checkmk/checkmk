#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job.job import BackgroundJobRegistry
from cmk.gui.i18n import _l
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.parentscan import page_menu as _page_menu
from cmk.gui.parentscan import rest_api as _rest_api
from cmk.gui.parentscan.background_job import ParentScanBackgroundJob
from cmk.gui.parentscan.page import ModeParentScan
from cmk.gui.permissions import Permission, PermissionRegistry
from cmk.gui.wato._permissions import PERMISSION_SECTION_WATO
from cmk.gui.wato.pages.folders import (
    FolderBulkAction,
    FolderBulkActionRegistry,
    FolderMenuEntry,
    FolderMenuEntryRegistry,
    FolderMenuLocation,
)
from cmk.gui.watolib.hosts_and_folders import HostActionMenuEntry, HostActionMenuRegistry
from cmk.gui.watolib.mode import ModeRegistry


def register(
    mode_registry: ModeRegistry,
    job_registry: BackgroundJobRegistry,
    endpoint_registry: EndpointRegistry,
    folder_menu_entry_registry: FolderMenuEntryRegistry,
    host_action_menu_registry: HostActionMenuRegistry,
    permission_registry: PermissionRegistry,
    folder_bulk_action_registry: FolderBulkActionRegistry,
) -> None:
    mode_registry.register(ModeParentScan)
    job_registry.register(ParentScanBackgroundJob)
    _rest_api.register(endpoint_registry)
    folder_bulk_action_registry.register(
        FolderBulkAction(request_var="_parentscan", mode_name="parentscan")
    )
    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="parentscan",
            title=_l("Perform network parent scan"),
            description=_l(
                "This permission is necessary for performing automatic "
                "scans for network parents of hosts (making use of traceroute). "
                "Please note, that for actually modifying the parents via the "
                "scan and for the creation of gateway hosts proper permissions "
                "for host and folders are also necessary."
            ),
            defaults=["admin", "user"],
        )
    )
    folder_menu_entry_registry.register(
        FolderMenuEntry(
            location=FolderMenuLocation.IN_FOLDER,
            ident="parentscan_in_folder",
            func=_page_menu.folder_page_menu_entries,
        )
    )
    folder_menu_entry_registry.register(
        FolderMenuEntry(
            location=FolderMenuLocation.SELECTED_HOSTS,
            ident="parentscan_selected_hosts",
            func=_page_menu.selected_hosts_page_menu_entries,
        )
    )
    host_action_menu_registry.register(
        HostActionMenuEntry(
            ident=_page_menu.HOST_ACTION_MENU_IDENT,
            is_shown=_page_menu.host_action_menu_is_shown,
            render=_page_menu.render_host_action_menu_entry,
        )
    )
