#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.structured_data import InventoryPaths

from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.i18n import _
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.valuespec import ValueSpec
from cmk.gui.views.icon import IconRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.visuals.info import VisualInfo, VisualInfoRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry

from . import _rulespec
from ._icon import InventoryHistoryIcon, InventoryIcon
from ._openapi import register as openapi_register
from ._rulespec import RulespecGroupInventory
from ._tree import (
    get_history,
    get_raw_status_data_via_livestatus,
    get_short_inventory_filepath,
    InventoryPath,
    load_delta_tree,
    load_latest_delta_tree,
    load_tree,
    parse_internal_raw_path,
    TreeSource,
    verify_permission,
)
from ._valuespecs import vs_element_inventory_visible_raw_path, vs_inventory_path_or_keys_help
from ._webapi import page_host_inv_api
from .filters import FilterHasInv, FilterInvHasSoftwarePackage

__all__ = [
    "InventoryPath",
    "RulespecGroupInventory",
    "TreeSource",
    "get_history",
    "get_raw_status_data_via_livestatus",
    "get_short_inventory_filepath",
    "load_delta_tree",
    "load_latest_delta_tree",
    "load_tree",
    "parse_internal_raw_path",
    "register",
    "vs_element_inventory_visible_raw_path",
    "vs_inventory_path_or_keys_help",
    "verify_permission",
]


def register(
    page_registry: PageRegistry,
    visual_info_registry: VisualInfoRegistry,
    filter_registry: FilterRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
    rulespec_registry: RulespecRegistry,
    icon_and_action_registry: IconRegistry,
    cron_job_registry: CronJobRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
) -> None:
    page_registry.register_page_handler("host_inv_api", page_host_inv_api)
    cron_job_registry.register(
        CronJob(
            name="execute_inventory_housekeeping_job",
            callable=InventoryHousekeeping(cmk.utils.paths.omd_root),
            interval=timedelta(hours=12),
        )
    )
    visual_info_registry.register(VisualInfoInventoryHistory)
    filter_registry.register(FilterHasInv())
    filter_registry.register(FilterInvHasSoftwarePackage())
    _rulespec.register(rulespec_group_registry, rulespec_registry)
    icon_and_action_registry.register(InventoryIcon)
    icon_and_action_registry.register(InventoryHistoryIcon)
    openapi_register(endpoint_family_registry, versioned_endpoint_registry)


# .
#   .--Inventory API-------------------------------------------------------.
#   |   ___                      _                        _    ____ ___    |
#   |  |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _     / \  |  _ \_ _|   |
#   |   | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |   / _ \ | |_) | |    |
#   |   | || | | \ V /  __/ | | | || (_) | |  | |_| |  / ___ \|  __/| |    |
#   |  |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, | /_/   \_\_|  |___|   |
#   |                                          |___/                       |
#   '----------------------------------------------------------------------'


class InventoryHousekeeping:
    def __init__(self, omd_root: Path) -> None:
        super().__init__()
        self.inv_paths = InventoryPaths(omd_root)

    def __call__(self) -> None:
        if not (self.inv_paths.delta_cache_dir.exists() and self.inv_paths.archive_dir.exists()):
            return

        inventory_archive_hosts = {
            x.name for x in self.inv_paths.archive_dir.iterdir() if x.is_dir()
        }
        inventory_delta_cache_hosts = {
            x.name for x in self.inv_paths.delta_cache_dir.iterdir() if x.is_dir()
        }

        folders_to_delete = inventory_delta_cache_hosts - inventory_archive_hosts
        for foldername in folders_to_delete:
            shutil.rmtree(str(self.inv_paths.delta_cache_host(HostName(foldername))))

        inventory_delta_cache_hosts -= folders_to_delete
        for raw_host_name in inventory_delta_cache_hosts:
            host_name = HostName(raw_host_name)
            available_timestamps = self._get_timestamps_for_host(host_name)
            for file_path in [
                x for x in self.inv_paths.delta_cache_host(host_name).iterdir() if not x.is_dir()
            ]:
                delete = False
                try:
                    first, second = file_path.with_suffix("").name.split("_")
                    if not (first in available_timestamps and second in available_timestamps):
                        delete = True
                except ValueError:
                    delete = True
                if delete:
                    file_path.unlink()

    def _get_timestamps_for_host(self, host_name: HostName) -> set[str]:
        timestamps = {"None"}  # 'None' refers to the histories start
        tree_path = self.inv_paths.inventory_tree(host_name)
        try:
            timestamps.add(str(int(tree_path.stat().st_mtime)))
        except FileNotFoundError:
            # TODO CMK-23408
            try:
                timestamps.add(str(int(tree_path.legacy.stat().st_mtime)))
            except FileNotFoundError:
                pass

        for filename in [
            x for x in self.inv_paths.archive_host(host_name).iterdir() if not x.is_dir()
        ]:
            timestamps.add(filename.with_suffix("").name)
        return timestamps


class VisualInfoInventoryHistory(VisualInfo):
    @property
    def ident(self) -> str:
        return "invhist"

    @property
    def title(self) -> str:
        return _("Inventory history")

    @property
    def title_plural(self) -> str:
        return _("Inventory histories")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []
