#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from functools import partial
from typing import Callable, Sequence

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
from cmk.base.agent_based.data_provider import ParsedSectionsBroker
from cmk.base.agent_based.utils import check_parsing_errors, summarize_host_sections
from cmk.base.config import HostConfig

from ._inventory import (
    fetch_real_host_data,
    FetchedDataResult,
    inventorize_cluster,
    inventorize_real_host,
)
from ._retentions import Retentions, RetentionsTracker
from ._tree_aggregator import InventoryTrees

__all__ = ["active_check_inventory"]


def active_check_inventory(
    hostname: HostName,
    options: dict[str, int],
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
    options: dict[str, int],
) -> ActiveCheckResult:
    hw_changes = options.get("hw-changes", 0)
    sw_changes = options.get("sw-changes", 0)
    sw_missing = options.get("sw-missing", 0)
    fail_status = options.get("inv-fail-status", 1)

    if host_config.is_cluster:
        fetched_data_result = FetchedDataResult(
            parsed_sections_broker=ParsedSectionsBroker({}),
            source_results=(),
            parsing_errors=(),
            processing_failed=False,
        )
        trees = inventorize_cluster(host_config=host_config)
        retentions = Retentions(RetentionsTracker([]), do_update=False)
    else:
        fetched_data_result = fetch_real_host_data(
            host_config=host_config,
            selected_sections=NO_SELECTION,
        )
        retentions_tracker = RetentionsTracker(host_config.inv_retention_intervals)
        trees = inventorize_real_host(
            host_config=host_config,
            parsed_sections_broker=fetched_data_result.parsed_sections_broker,
            run_plugin_names=EVERYTHING,
            retentions_tracker=retentions_tracker,
        )
        retentions = Retentions(
            retentions_tracker,
            # If no intervals are configured then remove all known retentions
            do_update=bool(host_config.inv_retention_intervals),
        )

    tree_or_archive_store = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    )
    old_tree = tree_or_archive_store.load(host_name=host_config.hostname)

    if fetched_data_result.processing_failed:
        active_check_result = ActiveCheckResult(fail_status, "Cannot update tree")
    else:
        _save_inventory_tree(
            host_config.hostname,
            tree_or_archive_store,
            trees.inventory,
            old_tree,
            retentions,
        )
        active_check_result = ActiveCheckResult()

    return ActiveCheckResult.from_subresults(
        active_check_result,
        *_check_inventory_tree(trees, old_tree, sw_missing, sw_changes, hw_changes),
        *summarize_host_sections(
            source_results=fetched_data_result.source_results,
            # Do not use source states which would overwrite "State when inventory fails" in the
            # ruleset "Do hardware/software Inventory". These are handled by the "Check_MK" service
            override_non_ok_state=fail_status,
            exit_spec_cb=host_config.exit_code_spec,
            time_settings_cb=lambda hostname: config.get_config_cache().get_piggybacked_hosts_time_settings(
                piggybacked_hostname=hostname,
            ),
            is_piggyback=host_config.is_piggyback_host,
        ),
        *check_parsing_errors(
            errors=fetched_data_result.parsing_errors,
            error_state=fail_status,
        ),
    )


def _check_inventory_tree(
    trees: InventoryTrees,
    old_tree: StructuredDataNode,
    sw_missing: ServiceState,
    sw_changes: ServiceState,
    hw_changes: ServiceState,
) -> Sequence[ActiveCheckResult]:
    if trees.inventory.is_empty() and trees.status_data.is_empty():
        return [ActiveCheckResult(0, "Found no data")]

    subresults = [
        ActiveCheckResult(0, f"Found {trees.inventory.count_entries()} inventory entries")
    ]

    swp_table = trees.inventory.get_table(("software", "packages"))
    if swp_table is not None and swp_table.is_empty() and sw_missing:
        subresults.append(ActiveCheckResult(sw_missing, "software packages information is missing"))

    if not _tree_nodes_are_equal(old_tree, trees.inventory, "software"):
        subresults.append(ActiveCheckResult(sw_changes, "software changes"))

    if not _tree_nodes_are_equal(old_tree, trees.inventory, "hardware"):
        subresults.append(ActiveCheckResult(hw_changes, "hardware changes"))

    if not trees.status_data.is_empty():
        subresults.append(
            ActiveCheckResult(0, f"Found {trees.status_data.count_entries()} status entries")
        )

    return subresults


def _tree_nodes_are_equal(
    old_tree: StructuredDataNode,
    inv_tree: StructuredDataNode,
    edge: str,
) -> bool:
    old_node = old_tree.get_node((edge,))
    inv_node = inv_tree.get_node((edge,))
    if old_node is None:
        return inv_node is None

    if inv_node is None:
        return False

    return old_node.is_equal(inv_node)


def _save_inventory_tree(
    hostname: HostName,
    tree_or_archive_store: TreeOrArchiveStore,
    inventory_tree: StructuredDataNode,
    old_tree: StructuredDataNode,
    retentions: Retentions,
) -> None:
    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        tree_or_archive_store.remove(host_name=hostname)
        return

    update_result = retentions.may_update(int(time.time()), inventory_tree, old_tree)

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
