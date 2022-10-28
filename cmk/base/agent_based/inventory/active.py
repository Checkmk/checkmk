#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from functools import partial
from typing import Callable

import cmk.utils.paths
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode, TreeOrArchiveStore
from cmk.utils.type_defs import EVERYTHING, HostName, ServiceState

from cmk.core_helpers.type_defs import NO_SELECTION

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config
from cmk.base.config import HostConfig

from ._inventory import check_inventory_tree
from ._tree_aggregator import TreeAggregator

__all__ = ["active_check_inventory"]


def active_check_inventory(
    hostname: HostName,
    options: dict,
    *,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    host_config = HostConfig.make_host_config(hostname)
    return error_handling.check_result(
        partial(_execute_active_check_inventory, host_config, options),
        host_config=host_config,
        plugin_name="check_mk_active-cmk_inv",
        service_name="Check_MK HW/SW Inventory",
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )


def _execute_active_check_inventory(
    host_config: HostConfig,
    options: dict,
) -> ActiveCheckResult:
    tree_or_archive_store = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    )
    old_tree = tree_or_archive_store.load(host_name=host_config.hostname)

    result = check_inventory_tree(
        host_config=host_config,
        selected_sections=NO_SELECTION,
        run_plugin_names=EVERYTHING,
        parameters=config.HWSWInventoryParameters.from_raw(options),
        old_tree=old_tree,
    )

    if not result.processing_failed:
        _save_inventory_tree(
            hostname=host_config.hostname,
            tree_or_archive_store=tree_or_archive_store,
            old_tree=old_tree,
            tree_aggregator=result.tree_aggregator,
        )

    return result.check_result


def _save_inventory_tree(
    *,
    hostname: HostName,
    tree_or_archive_store: TreeOrArchiveStore,
    tree_aggregator: TreeAggregator,
    old_tree: StructuredDataNode,
) -> None:
    inventory_tree = tree_aggregator.inventory_tree

    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        tree_or_archive_store.remove(host_name=hostname)
        return

    update_result = tree_aggregator.may_update(int(time.time()), old_tree)

    if old_tree.is_empty():
        console.verbose("New inventory tree.\n")

    elif not old_tree.is_equal(inventory_tree):
        console.verbose("Inventory tree has changed. Add history entry.\n")
        tree_or_archive_store.archive(host_name=hostname)

    elif update_result.save_tree:
        console.verbose(
            "Update inventory tree%s.\n"
            % (" (%s)" % update_result.reason if update_result.reason else "")
        )
    else:
        console.verbose(
            "Inventory tree not updated%s.\n"
            % (" (%s)" % update_result.reason if update_result.reason else "")
        )
        return

    tree_or_archive_store.save(host_name=hostname, tree=inventory_tree)
