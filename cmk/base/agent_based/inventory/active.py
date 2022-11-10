#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from typing import Callable

import cmk.utils.paths
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode, TreeOrArchiveStore, UpdateResult
from cmk.utils.type_defs import EVERYTHING, HostName, ServiceState

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.core_helpers.type_defs import NO_SELECTION

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config
from cmk.base.auto_queue import AutoQueue
from cmk.base.config import HostConfig

from ._inventory import check_inventory_tree

__all__ = ["active_check_inventory", "execute_active_check_inventory"]


def active_check_inventory(
    hostname: HostName,
    options: dict,
    *,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)
    return error_handling.check_result(
        partial(
            execute_active_check_inventory,
            hostname,
            host_config,
            config.HWSWInventoryParameters.from_raw(options),
        ),
        exit_spec=host_config.exit_code_spec(),
        host_name=hostname,
        service_name="Check_MK HW/SW Inventory",
        plugin_name="check_mk_active-cmk_inv",
        is_cluster=config_cache.is_cluster(hostname),
        is_inline_snmp=(host_config.snmp_config(hostname).snmp_backend is SNMPBackendEnum.INLINE),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )


def execute_active_check_inventory(
    host_name: HostName,
    host_config: HostConfig,
    parameters: config.HWSWInventoryParameters,
) -> ActiveCheckResult:
    tree_or_archive_store = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    )
    old_tree = tree_or_archive_store.load(host_name=host_name)

    result = check_inventory_tree(
        host_name,
        host_config=host_config,
        selected_sections=NO_SELECTION,
        run_plugin_names=EVERYTHING,
        parameters=parameters,
        old_tree=old_tree,
    )

    if result.no_data_or_files:
        AutoQueue(cmk.utils.paths.autoinventory_dir).add(host_name)

    if not (result.processing_failed or result.no_data_or_files):
        _save_inventory_tree(
            hostname=host_name,
            tree_or_archive_store=tree_or_archive_store,
            old_tree=old_tree,
            inventory_tree=result.inventory_tree,
            update_result=result.update_result,
        )

    return result.check_result


def _save_inventory_tree(
    *,
    hostname: HostName,
    tree_or_archive_store: TreeOrArchiveStore,
    old_tree: StructuredDataNode,
    inventory_tree: StructuredDataNode,
    update_result: UpdateResult,
) -> None:
    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        tree_or_archive_store.remove(host_name=hostname)
        return

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
