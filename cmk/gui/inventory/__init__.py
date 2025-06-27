#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from datetime import timedelta

import cmk.utils.paths

from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.visuals.info import VisualInfoRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry

from . import _rulespec
from ._housekeeping import InventoryHousekeeping
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
from ._visuals import VisualInfoInventoryHistory
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
    *,
    ignore_duplicate_endpoints: bool = False,
) -> None:
    page_registry.register(PageEndpoint("host_inv_api", page_host_inv_api))
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
    openapi_register(
        endpoint_family_registry,
        versioned_endpoint_registry,
        ignore_duplicates=ignore_duplicate_endpoints,
    )
