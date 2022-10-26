#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from functools import partial
from typing import Callable

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode, TreeOrArchiveStore
from cmk.utils.type_defs import EVERYTHING, HostName, ServiceState

from cmk.core_helpers.type_defs import NO_SELECTION

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config
from cmk.base.agent_based.utils import check_parsing_errors, summarize_host_sections
from cmk.base.config import HostConfig

from ._inventory import (
    check_trees,
    fetch_real_host_data,
    inventorize_cluster,
    inventorize_real_host,
)
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
    parameters = config.HWSWInventoryParameters.from_raw(options)

    tree_or_archive_store = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    )
    old_tree = tree_or_archive_store.load(host_name=host_config.hostname)

    if host_config.is_cluster:
        tree_aggregator = inventorize_cluster(host_config=host_config)
        _save_inventory_tree(
            host_config.hostname,
            tree_or_archive_store,
            tree_aggregator,
            old_tree,
        )
        return ActiveCheckResult.from_subresults(
            *check_trees(
                parameters=parameters,
                inventory_tree=tree_aggregator.trees.inventory,
                status_data_tree=tree_aggregator.trees.status_data,
                old_tree=old_tree,
            ),
        )

    fetched_data_result = fetch_real_host_data(
        host_config=host_config,
        selected_sections=NO_SELECTION,
    )
    tree_aggregator = inventorize_real_host(
        host_config=host_config,
        parsed_sections_broker=fetched_data_result.parsed_sections_broker,
        run_plugin_names=EVERYTHING,
    )

    if fetched_data_result.processing_failed:
        active_check_result = ActiveCheckResult(parameters.fail_status, "Cannot update tree")
    else:
        _save_inventory_tree(
            host_config.hostname,
            tree_or_archive_store,
            tree_aggregator,
            old_tree,
        )
        active_check_result = ActiveCheckResult()

    return ActiveCheckResult.from_subresults(
        active_check_result,
        *check_trees(
            parameters=parameters,
            inventory_tree=tree_aggregator.trees.inventory,
            status_data_tree=tree_aggregator.trees.status_data,
            old_tree=old_tree,
        ),
        *summarize_host_sections(
            source_results=fetched_data_result.source_results,
            # Do not use source states which would overwrite "State when inventory fails" in the
            # ruleset "Do hardware/software Inventory". These are handled by the "Check_MK" service
            override_non_ok_state=parameters.fail_status,
            exit_spec_cb=host_config.exit_code_spec,
            time_settings_cb=lambda hostname: config.get_config_cache().get_piggybacked_hosts_time_settings(
                piggybacked_hostname=hostname,
            ),
            is_piggyback=host_config.is_piggyback_host,
        ),
        *check_parsing_errors(
            errors=fetched_data_result.parsing_errors,
            error_state=parameters.fail_status,
        ),
    )


def _save_inventory_tree(
    hostname: HostName,
    tree_or_archive_store: TreeOrArchiveStore,
    tree_aggregator: TreeAggregator,
    old_tree: StructuredDataNode,
) -> None:
    inventory_tree = tree_aggregator.trees.inventory

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
