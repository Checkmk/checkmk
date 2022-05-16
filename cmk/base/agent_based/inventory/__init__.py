#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Currently this module manages the inventory tree which is built
while the inventory is performed for one host.

In the future all inventory code should be moved to this module."""

import time
from pathlib import Path
from typing import Container, Dict, List, NamedTuple, Optional, Sequence, Tuple

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKGeneralException, OnError
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode, StructuredDataStore
from cmk.utils.type_defs import (
    EVERYTHING,
    HostAddress,
    HostKey,
    HostName,
    InventoryPluginName,
    result,
    ServiceState,
    SourceType,
    state_markers,
)

from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.agent_based.decorator as decorator
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.section as section
from cmk.base.agent_based.data_provider import make_broker, ParsedSectionsBroker
from cmk.base.agent_based.utils import check_parsing_errors, check_sources, get_section_kwargs
from cmk.base.sources import Source

from ._retentions import Retentions, RetentionsTracker
from ._tree_aggregator import InventoryTrees, TreeAggregator


class ActiveInventoryResult(NamedTuple):
    trees: InventoryTrees
    source_results: Sequence[Tuple[Source, result.Result[HostSections, Exception]]]
    parsing_errors: Sequence[str]
    processing_failed: bool


#   .--cmk -i--------------------------------------------------------------.
#   |                                   _            _                     |
#   |                     ___ _ __ ___ | | __       (_)                    |
#   |                    / __| '_ ` _ \| |/ /  _____| |                    |
#   |                   | (__| | | | | |   <  |_____| |                    |
#   |                    \___|_| |_| |_|_|\_\       |_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def commandline_inventory(
    hostnames: List[HostName],
    *,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[InventoryPluginName] = EVERYTHING,
) -> None:
    store.makedirs(cmk.utils.paths.inventory_output_dir)
    store.makedirs(cmk.utils.paths.inventory_archive_dir)

    for hostname in hostnames:
        section.section_begin(hostname)
        host_config = config.HostConfig.make_host_config(hostname)
        try:
            _commandline_inventory_on_host(
                host_config=host_config,
                selected_sections=selected_sections,
                run_plugin_names=run_plugin_names,
            )

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _commandline_inventory_on_host(
    *,
    host_config: config.HostConfig,
    run_plugin_names: Container[InventoryPluginName],
    selected_sections: SectionNameCollection,
) -> None:

    section.section_step("Inventorizing")

    inv_result = _inventorize_host(
        host_config=host_config,
        selected_sections=selected_sections,
        run_plugin_names=run_plugin_names,
        retentions_tracker=RetentionsTracker([]),
    )

    for subresult in check_parsing_errors(errors=inv_result.parsing_errors):
        for line in subresult.details:
            console.warning(line)

    # TODO: inv_results.source_results is completely ignored here.
    # We should process the results to make errors visible on the console
    count_i = inv_result.trees.inventory.count_entries()
    count_s = inv_result.trees.status_data.count_entries()
    section.section_success(f"Found {count_i} inventory entries")
    section.section_success(f"Found {count_s} status entries")

    if not host_config.inventory_export_hooks:
        return

    section.section_step("Execute inventory export hooks")

    _run_inventory_export_hooks(host_config, inv_result.trees.inventory)

    count = len(host_config.inventory_export_hooks)
    section.section_success(f"Sucessfully ran {count} export hooks")


# .
#   .--Inventory Check-----------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   |                      ____ _               _                          |
#   |                     / ___| |__   ___  ___| | __                      |
#   |                    | |   | '_ \ / _ \/ __| |/ /                      |
#   |                    | |___| | | |  __/ (__|   <                       |
#   |                     \____|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@decorator.handle_check_mk_check_result("check_mk_active-cmk_inv", "Check_MK HW/SW Inventory")
def active_check_inventory(hostname: HostName, options: Dict[str, int]) -> ActiveCheckResult:
    # TODO: drop '_inv_'
    _inv_hw_changes = options.get("hw-changes", 0)
    _inv_sw_changes = options.get("sw-changes", 0)
    _inv_sw_missing = options.get("sw-missing", 0)
    _inv_fail_status = options.get("inv-fail-status", 1)

    host_config = config.HostConfig.make_host_config(hostname)

    retentions_tracker = RetentionsTracker(host_config.inv_retention_intervals)

    inv_result = _inventorize_host(
        host_config=host_config,
        selected_sections=NO_SELECTION,
        run_plugin_names=EVERYTHING,
        retentions_tracker=retentions_tracker,
    )
    trees = inv_result.trees

    retentions = Retentions(
        retentions_tracker,
        trees.inventory,
        # If no intervals are configured then remove all known retentions
        do_update=bool(host_config.inv_retention_intervals),
    )

    if inv_result.processing_failed:
        old_tree = None
        update_result = ActiveCheckResult(1, "Cannot update tree")
    else:
        old_tree = _save_inventory_tree(hostname, trees.inventory, retentions)
        update_result = ActiveCheckResult()

    _run_inventory_export_hooks(host_config, trees.inventory)

    return ActiveCheckResult.from_subresults(
        update_result,
        *_check_inventory_tree(trees, old_tree, _inv_sw_missing, _inv_sw_changes, _inv_hw_changes),
        *check_sources(
            source_results=inv_result.source_results,
            mode=Mode.INVENTORY,
            # Do not use source states which would overwrite "State when inventory fails" in the
            # ruleset "Do hardware/software Inventory". These are handled by the "Check_MK" service
            override_non_ok_state=_inv_fail_status,
        ),
        *check_parsing_errors(
            errors=inv_result.parsing_errors,
            error_state=_inv_fail_status,
        ),
    )


def _check_inventory_tree(
    trees: InventoryTrees,
    old_tree: Optional[StructuredDataNode],
    sw_missing: ServiceState,
    sw_changes: ServiceState,
    hw_changes: ServiceState,
) -> Sequence[ActiveCheckResult]:
    if trees.inventory.is_empty() and trees.status_data.is_empty():
        return [ActiveCheckResult(0, "Found no data")]

    subresults = [
        ActiveCheckResult(0, f"Found {trees.inventory.count_entries()} inventory entries")
    ]

    swp_table = trees.inventory.get_table(["software", "packages"])
    if swp_table is not None and swp_table.is_empty() and sw_missing:
        subresults.append(ActiveCheckResult(sw_missing, "software packages information is missing"))

    if old_tree is not None:
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
    inv_tree: Optional[StructuredDataNode],
    edge: str,
) -> bool:
    if inv_tree is None:
        return False

    old_node = old_tree.get_node([edge])
    inv_node = inv_tree.get_node([edge])
    if old_node is None:
        return inv_node is None

    if inv_node is None:
        return False

    return old_node.is_equal(inv_node)


def _inventorize_host(
    *,
    host_config: config.HostConfig,
    run_plugin_names: Container[InventoryPluginName],
    selected_sections: SectionNameCollection,
    retentions_tracker: RetentionsTracker,
) -> ActiveInventoryResult:
    if host_config.is_cluster:
        return ActiveInventoryResult(
            trees=_do_inv_for_cluster(host_config),
            source_results=(),
            parsing_errors=(),
            processing_failed=False,
        )

    ipaddress = config.lookup_ip_address(host_config)
    config_cache = config.get_config_cache()

    broker, results, _fetcher_messages = make_broker(
        config_cache=config_cache,
        host_config=host_config,
        ip_address=ipaddress,
        selected_sections=selected_sections,
        mode=(Mode.INVENTORY if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS),
        file_cache_max_age=host_config.max_cachefile_age,
        fetcher_messages=(),
        force_snmp_cache_refresh=False,
        on_scan_error=OnError.RAISE,
    )

    parsing_errors = broker.parsing_errors()
    return ActiveInventoryResult(
        trees=_do_inv_for_realhost(
            host_config,
            parsed_sections_broker=broker,
            run_plugin_names=run_plugin_names,
            retentions_tracker=retentions_tracker,
        ),
        source_results=results,
        parsing_errors=parsing_errors,
        processing_failed=(_sources_failed(results) or bool(parsing_errors)),
    )


def _sources_failed(
    results: Sequence[Tuple[Source, result.Result[HostSections, Exception]]],
) -> bool:
    """Check if data sources of a host failed

    If a data source failed, we may have incomlete data. In that case we
    may not write it to disk because that would result in a flapping state
    of the tree, which would blow up the inventory history (in terms of disk usage).
    """
    # If a result is not OK, that means the corresponding sections have not been added.
    return any(not source_result.is_ok() for _source, source_result in results)


def do_inventory_actions_during_checking_for(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    *,
    parsed_sections_broker: ParsedSectionsBroker,
) -> None:

    status_data_store = StructuredDataStore(Path(cmk.utils.paths.status_data_dir))

    if not host_config.do_status_data_inventory:
        # includes cluster case
        status_data_store.remove_files(host_name=host_config.hostname)
        return  # nothing to do here

    trees = _do_inv_for_realhost(
        host_config=host_config,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=EVERYTHING,
        retentions_tracker=RetentionsTracker([]),
    )
    if trees.status_data and not trees.status_data.is_empty():
        status_data_store.save(host_name=host_config.hostname, tree=trees.status_data)


def _do_inv_for_cluster(host_config: config.HostConfig) -> InventoryTrees:
    inventory_tree = StructuredDataNode()
    _set_cluster_property(inventory_tree, host_config)

    if not host_config.nodes:
        return InventoryTrees(inventory_tree, StructuredDataNode())

    node = inventory_tree.setdefault_node(
        ["software", "applications", "check_mk", "cluster", "nodes"]
    )
    node.table.add_key_columns(["name"])
    node.table.add_rows([{"name": node_name} for node_name in host_config.nodes])

    return InventoryTrees(inventory_tree, StructuredDataNode())


def _do_inv_for_realhost(
    host_config: config.HostConfig,
    *,
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[InventoryPluginName],
    retentions_tracker: RetentionsTracker,
) -> InventoryTrees:
    tree_aggregator = TreeAggregator()

    _set_cluster_property(tree_aggregator.trees.inventory, host_config)

    section.section_step("Executing inventory plugins")
    for inventory_plugin in agent_based_register.iter_all_inventory_plugins():
        if inventory_plugin.name not in run_plugin_names:
            continue

        for host_key in (host_config.host_key, host_config.host_key_mgmt):
            kwargs = get_section_kwargs(
                parsed_sections_broker,
                host_key,
                inventory_plugin.sections,
            )
            if not kwargs:
                console.vverbose(
                    " %s%s%s%s: skipped (no data)\n",
                    tty.yellow,
                    tty.bold,
                    inventory_plugin.name,
                    tty.normal,
                )
                continue

            # Inventory functions can optionally have a second argument: parameters.
            # These are configured via rule sets (much like check parameters).
            if inventory_plugin.inventory_ruleset_name is not None:
                kwargs = {
                    **kwargs,
                    "params": host_config.inventory_parameters(
                        inventory_plugin.inventory_ruleset_name
                    ),
                }

            exception = tree_aggregator.aggregate_results(
                inventory_generator=inventory_plugin.inventory_function(**kwargs),
                retentions_tracker=retentions_tracker,
                raw_cache_info=parsed_sections_broker.get_cache_info(inventory_plugin.sections),
                is_legacy_plugin=inventory_plugin.module is None,
            )

            if exception:
                console.warning(
                    " %s%s%s%s: failed: %s",
                    tty.red,
                    tty.bold,
                    inventory_plugin.name,
                    tty.normal,
                    exception,
                )
            else:
                console.verbose(" %s%s%s%s", tty.green, tty.bold, inventory_plugin.name, tty.normal)
                console.vverbose(": ok\n")

    console.verbose("\n")
    return tree_aggregator.trees


def _set_cluster_property(
    inventory_tree: StructuredDataNode,
    host_config: config.HostConfig,
) -> None:
    node = inventory_tree.setdefault_node(["software", "applications", "check_mk", "cluster"])
    node.attributes.add_pairs({"is_cluster": host_config.is_cluster})


def _save_inventory_tree(
    hostname: HostName,
    inventory_tree: StructuredDataNode,
    retentions: Retentions,
) -> Optional[StructuredDataNode]:

    inventory_store = StructuredDataStore(cmk.utils.paths.inventory_output_dir)

    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        inventory_store.remove_files(host_name=hostname)
        return None

    old_tree = inventory_store.load(host_name=hostname)
    update_result = retentions.may_update(int(time.time()), old_tree)

    if old_tree.is_empty():
        console.verbose("New inventory tree.\n")

    elif not old_tree.is_equal(inventory_tree):
        console.verbose("Inventory tree has changed. Add history entry.\n")
        inventory_store.archive(
            host_name=hostname,
            archive_dir=cmk.utils.paths.inventory_archive_dir,
        )

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
        return None

    inventory_store.save(host_name=hostname, tree=inventory_tree)
    return old_tree


def _run_inventory_export_hooks(
    host_config: config.HostConfig, inventory_tree: StructuredDataNode
) -> None:
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel

    for hookname, params in host_config.inventory_export_hooks:
        console.verbose(
            "Execute export hook: %s%s%s%s" % (tty.blue, tty.bold, hookname, tty.normal)
        )
        try:
            func = inventory_plugins.inv_export[hookname]["export_function"]
            func(host_config.hostname, params, inventory_tree.serialize())
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException("Failed to execute export hook %s: %s" % (hookname, e))
