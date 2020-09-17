#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Currently this module manages the inventory tree which is built
while the inventory is performed for one host.

In the future all inventory code should be moved to this module."""

import os
from typing import Dict, List, Optional, Sequence, Tuple
from contextlib import suppress

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataTree
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    MetricTuple,
    Result,
    ServiceAdditionalDetails,
    ServiceDetails,
    ServiceState,
    SourceType,
)

from cmk.fetchers.type_defs import Mode

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.checkers as checkers
import cmk.base.decorator
import cmk.base.ip_lookup as ip_lookup
import cmk.base.section as section

from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow, InventoryResult
from cmk.base.checkers import ABCSource, ABCHostSections
from cmk.base.checkers.host_sections import HostKey, MultiHostSections
from cmk.base.checkers.snmp import SNMPHostSections
from cmk.base.discovered_labels import HostLabel

#.
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   | Code for doing the actual inventory                                  |
#   '----------------------------------------------------------------------'


def do_inv(hostnames: List[HostName]) -> None:
    store.makedirs(cmk.utils.paths.inventory_output_dir)
    store.makedirs(cmk.utils.paths.inventory_archive_dir)

    config_cache = config.get_config_cache()

    for hostname in hostnames:
        section.section_begin(hostname)
        try:
            host_config = config.HostConfig.make_host_config(hostname)
            if host_config.is_cluster:
                ipaddress = None
            else:
                ipaddress = ip_lookup.lookup_ip_address(host_config)

            inventory_tree, status_data_tree = _do_inv_for(
                config_cache,
                host_config,
                ipaddress,
                sources=checkers.make_sources(
                    host_config,
                    ipaddress,
                    mode=checkers.Mode.INVENTORY,
                ),
                multi_host_sections=None,
            )[:2]
            _run_inventory_export_hooks(host_config, inventory_tree)
            _show_inventory_results_on_console(inventory_tree, status_data_tree)

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise

            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _show_inventory_results_on_console(inventory_tree: StructuredDataTree,
                                       status_data_tree: StructuredDataTree) -> None:
    section.section_success("Found %s%s%d%s inventory entries" %
                            (tty.bold, tty.yellow, inventory_tree.count_entries(), tty.normal))
    section.section_success("Found %s%s%d%s status entries" %
                            (tty.bold, tty.yellow, status_data_tree.count_entries(), tty.normal))


@cmk.base.decorator.handle_check_mk_check_result("check_mk_active-cmk_inv",
                                                 "Check_MK HW/SW Inventory")
def do_inv_check(
    hostname: HostName, options: Dict[str, int]
) -> Tuple[ServiceState, List[ServiceDetails], List[ServiceAdditionalDetails], List[MetricTuple]]:
    _inv_hw_changes = options.get("hw-changes", 0)
    _inv_sw_changes = options.get("sw-changes", 0)
    _inv_sw_missing = options.get("sw-missing", 0)
    _inv_fail_status = options.get("inv-fail-status", 1)

    config_cache = config.get_config_cache()
    host_config = config.HostConfig.make_host_config(hostname)
    if host_config.is_cluster:
        ipaddress = None
    else:
        ipaddress = ip_lookup.lookup_ip_address(host_config)

    status = 0
    infotexts: List[str] = []
    long_infotexts: List[str] = []

    sources = checkers.make_sources(
        host_config,
        ipaddress,
        mode=checkers.Mode.INVENTORY,
    )
    inventory_tree, status_data_tree, results = _do_inv_for(
        config_cache,
        host_config,
        ipaddress,
        sources=sources,
        multi_host_sections=None,
    )

    #TODO add cluster if and only if all sources do not fail?
    if _all_sources_fail(host_config, ipaddress):
        old_tree, sources_state = None, 1
        status = max(status, sources_state)
        infotexts.append("Cannot update tree%s" % check_api_utils.state_markers[sources_state])
    else:
        old_tree = _save_inventory_tree(hostname, inventory_tree)

    _run_inventory_export_hooks(host_config, inventory_tree)

    if inventory_tree.is_empty() and status_data_tree.is_empty():
        infotexts.append("Found no data")

    else:
        infotexts.append("Found %d inventory entries" % inventory_tree.count_entries())

        # Node 'software' is always there because _do_inv_for creates this node for cluster info
        if not inventory_tree.get_sub_container(['software']).has_edge('packages')\
           and _inv_sw_missing:
            infotexts.append("software packages information is missing" +
                             check_api_utils.state_markers[_inv_sw_missing])
            status = max(status, _inv_sw_missing)

        if old_tree is not None:
            if not old_tree.is_equal(inventory_tree, edges=["software"]):
                infotext = "software changes"
                if _inv_sw_changes:
                    status = max(status, _inv_sw_changes)
                    infotext += check_api_utils.state_markers[_inv_sw_changes]
                infotexts.append(infotext)

            if not old_tree.is_equal(inventory_tree, edges=["hardware"]):
                infotext = "hardware changes"
                if _inv_hw_changes:
                    status = max(status, _inv_hw_changes)
                    infotext += check_api_utils.state_markers[_inv_hw_changes]

                infotexts.append(infotext)

        if not status_data_tree.is_empty():
            infotexts.append("Found %s status entries" % status_data_tree.count_entries())

    for source, host_sections in results:
        source_state, source_output, _source_perfdata = source.summarize(host_sections)
        if source_state != 0:
            # Do not output informational things (state == 0). Also do not use source states
            # which would overwrite "State when inventory fails" in the ruleset
            # "Do hardware/software Inventory".
            # These information and source states are handled by the "Check_MK" service
            status = max(_inv_fail_status, status)
            infotexts.append("[%s] %s" % (source.id, source_output))

    return status, infotexts, long_infotexts, []


def _all_sources_fail(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
) -> bool:
    """We want to check if ALL data sources of a host fail:
    By default a host has the auto-piggyback data source. We remove it if
    it's not a pure piggyback host and there's no piggyback data available
    for this host.
    In this case the piggyback data source never fails (self._exception = None)."""
    if host_config.is_cluster:
        return False

    # TODO(ml): This function makes no sense and is no op anyway.
    #           We could fix it by actually searching for errors in the sources
    #           as it seems that it is what was meant initially.
    exceptions_by_source = {
        source.id: None for source in checkers.make_sources(
            host_config,
            ipaddress,
            mode=checkers.Mode.INVENTORY,
        )
    }
    if "piggyback" in exceptions_by_source and not len(exceptions_by_source) == 1\
       and not host_config.has_piggyback_data:
        del exceptions_by_source["piggyback"]

    return all(exception is not None for exception in exceptions_by_source.values())


def do_inventory_actions_during_checking_for(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    sources: Sequence[ABCSource],
    multi_host_sections: MultiHostSections,
) -> None:
    hostname = host_config.hostname

    if not host_config.do_status_data_inventory:
        _cleanup_status_data(hostname)
        return  # nothing to do here

    _inventory_tree, status_data_tree = _do_inv_for(
        config_cache,
        config.HostConfig.make_host_config(hostname),
        ipaddress,
        sources=sources,
        multi_host_sections=multi_host_sections,
    )[:2]
    _save_status_data_tree(hostname, status_data_tree)


def _cleanup_status_data(hostname: HostName) -> None:
    """Remove empty status data files"""
    filepath = "%s/%s" % (cmk.utils.paths.status_data_dir, hostname)
    with suppress(OSError):
        os.remove(filepath)
    with suppress(OSError):
        os.remove(filepath + ".gz")


def _do_inv_for(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    sources: Sequence[ABCSource],
    multi_host_sections: Optional[MultiHostSections],
) -> Tuple[StructuredDataTree, StructuredDataTree, Sequence[Tuple[ABCSource, Result[ABCHostSections,
                                                                                    Exception]]]]:
    hostname = host_config.hostname

    initialize_inventory_tree()
    inventory_tree = g_inv_tree
    status_data_tree = StructuredDataTree()

    node = inventory_tree.get_dict("software.applications.check_mk.cluster.")
    results: Sequence[Tuple[ABCSource, Result[ABCHostSections, Exception]]] = []
    if host_config.is_cluster:
        node["is_cluster"] = True
        _do_inv_for_cluster(host_config, inventory_tree)
    else:
        node["is_cluster"] = False
        results = _do_inv_for_realhost(
            config_cache,
            host_config,
            sources,
            multi_host_sections,
            hostname,
            ipaddress,
            inventory_tree,
            status_data_tree,
        )

    inventory_tree.normalize_nodes()
    status_data_tree.normalize_nodes()
    return inventory_tree, status_data_tree, results


def _do_inv_for_cluster(host_config: config.HostConfig, inventory_tree: StructuredDataTree) -> None:
    if host_config.nodes is None:
        return

    inv_node = inventory_tree.get_list("software.applications.check_mk.cluster.nodes:")
    for node_name in host_config.nodes:
        inv_node.append({
            "name": node_name,
        })


def _do_inv_for_realhost(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    sources: Sequence[ABCSource],
    multi_host_sections: Optional[MultiHostSections],
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    inventory_tree: StructuredDataTree,
    status_data_tree: StructuredDataTree,
) -> Sequence[Tuple[ABCSource, Result[ABCHostSections, Exception]]]:
    results: List[Tuple[ABCSource, Result[ABCHostSections, Exception]]] = []
    for source in sources:
        if isinstance(source, checkers.snmp.SNMPSource):
            # TODO(ml): This modifies the SNMP fetcher config dynamically.
            source.on_snmp_scan_error = "raise"  # default
            checkers.FileCacheFactory.snmp_disabled = True
            source.use_snmpwalk_cache = False
            source.ignore_check_interval = True
            if multi_host_sections is not None:
                # Status data inventory already provides filled multi_host_sections object.
                # SNMP data source: If 'do_status_data_inv' is enabled there may be
                # sections for inventory plugins which were not fetched yet.
                host_sections = multi_host_sections.setdefault(
                    # TODO(ml): are
                    #    hostname == source.hostname
                    #    ipaddress == source.ipaddress
                    # ?
                    HostKey(hostname, ipaddress, source.source_type),
                    SNMPHostSections(),
                )
                # TODO(ml): This modifies the SNMP fetcher config dynamically.
                #           Can the fetcher handle that on its own?
                source.prefetched_sections = host_sections.sections

                # When executing the structured status inventory, we are in the Mode.CHECKING
                assert source.mode is Mode.INVENTORY or source.mode is Mode.CHECKING

                host_section = source.parse(source.fetch())
                results.append((source, host_section))
                if host_section.is_ok():
                    assert host_section.ok is not None
                    host_sections.update(host_section.ok)

    if multi_host_sections is None:
        multi_host_sections = MultiHostSections()
        hs = checkers.update_host_sections(
            multi_host_sections,
            checkers.make_nodes(
                config_cache,
                host_config,
                ipaddress,
                checkers.Mode.INVENTORY,
                sources,
            ),
            max_cachefile_age=host_config.max_cachefile_age,
            selected_raw_sections=None,
            host_config=host_config,
        )
        results.extend(hs)

    section.section_step("Executing inventory plugins")
    console.verbose("Plugins:")
    for inventory_plugin in agent_based_register.iter_all_inventory_plugins():

        kwargs = multi_host_sections.get_section_kwargs(
            HostKey(hostname, ipaddress, SourceType.HOST),
            inventory_plugin.sections,
        )
        if not kwargs:
            continue

        console.verbose(" %s%s%s%s" % (tty.green, tty.bold, inventory_plugin.name, tty.normal))

        # Inventory functions can optionally have a second argument: parameters.
        # These are configured via rule sets (much like check parameters).
        if inventory_plugin.inventory_ruleset_name is not None:
            kwargs["params"] = host_config.inventory_parameters(
                str(inventory_plugin.inventory_ruleset_name))  # TODO (mo): keep type!

        _aggregate_inventory_results(
            inventory_plugin.inventory_function(**kwargs),
            inventory_tree,
            status_data_tree,
        )

    console.verbose("\n")
    return results


def _aggregate_inventory_results(
    inventory_generator: InventoryResult,
    inventory_tree: StructuredDataTree,
    status_data_tree: StructuredDataTree,
) -> None:

    try:
        inventory_items = list(inventory_generator)
    except Exception as exc:
        if cmk.utils.debug.enabled():
            raise
        console.warning("Error in plugin: %s" % exc)
        return

    for item in inventory_items:
        if isinstance(item, Attributes):
            _integrate_attributes(item, inventory_tree, status_data_tree)
        elif isinstance(item, TableRow):
            _integrate_table_row(item, inventory_tree, status_data_tree)
        else:  # can't happen
            raise NotImplementedError()


def _integrate_attributes(
    attributes: Attributes,
    inventory_tree: StructuredDataTree,
    status_data_tree: StructuredDataTree,
) -> None:

    leg_path = ".".join(attributes.path) + "."
    if attributes.inventory_attributes:
        inventory_tree.get_dict(leg_path).update(attributes.inventory_attributes)
    if attributes.status_attributes:
        status_data_tree.get_dict(leg_path).update(attributes.status_attributes)


def _integrate_table_row(
    table_row: TableRow,
    inventory_tree: StructuredDataTree,
    status_data_tree: StructuredDataTree,
) -> None:
    def _find_matching_row_index(rows, key_columns):
        for index, row in enumerate(rows):
            if all(k in row and row[k] == v for k, v in key_columns.items()):
                return index
        return None

    leg_path = ".".join(table_row.path) + ":"

    inv_rows = inventory_tree.get_list(leg_path)
    idx = _find_matching_row_index(inv_rows, table_row.key_columns)
    if idx is None:
        inv_rows.append({**table_row.key_columns, **table_row.inventory_columns})
    else:
        inv_rows[idx].update(table_row.inventory_columns)

    sd_rows = status_data_tree.get_list(leg_path)
    idx = _find_matching_row_index(sd_rows, table_row.key_columns)
    if idx is None:
        sd_rows.append({**table_row.key_columns, **table_row.status_columns})
    else:
        sd_rows[idx].update(table_row.status_columns)


#.
#   .--Inventory Tree------------------------------------------------------.
#   |  ___                      _                     _____                |
#   | |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _  |_   _| __ ___  ___   |
#   |  | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |   | || '__/ _ \/ _ \  |
#   |  | || | | \ V /  __/ | | | || (_) | |  | |_| |   | || | |  __/  __/  |
#   | |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |   |_||_|  \___|\___|  |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   | Managing the inventory tree of a host                                |
#   '----------------------------------------------------------------------'

g_inv_tree = StructuredDataTree()  # TODO Remove one day. Deprecated with version 1.5.0i3??


def initialize_inventory_tree(tree=None) -> None:
    # TODO (mo):
    # This function has been resurrected in order to facilitate the migration
    # of legacy inventory plugins to the new API.
    # Once the processing of the plugins switched to the new API, we can
    # move this function and all related functionality to
    # cmk.base.api.agent_based.register.inventory_plugins_legacy
    global g_inv_tree
    g_inv_tree = StructuredDataTree() if tree is None else tree


# Dict based
def inv_tree(path: str) -> Dict:  # TODO Remove one day. Deprecated with version 1.5.0i3??
    return g_inv_tree.get_dict(path)


# List based
def inv_tree_list(path: str) -> List:  # TODO Remove one day. Deprecated with version 1.5.0i3??
    return g_inv_tree.get_list(path)


def _save_inventory_tree(hostname: HostName,
                         inventory_tree: StructuredDataTree) -> Optional[StructuredDataTree]:
    store.makedirs(cmk.utils.paths.inventory_output_dir)

    filepath = cmk.utils.paths.inventory_output_dir + "/" + hostname
    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(filepath + ".gz"):
            os.remove(filepath + ".gz")
        return None

    old_tree = StructuredDataTree().load_from(filepath)
    old_tree.normalize_nodes()
    if old_tree.is_equal(inventory_tree):
        console.verbose("Inventory was unchanged\n")
        return None

    if old_tree.is_empty():
        console.verbose("New inventory tree\n")
    else:
        console.verbose("Inventory tree has changed\n")
        old_time = os.stat(filepath).st_mtime
        arcdir = "%s/%s" % (cmk.utils.paths.inventory_archive_dir, hostname)
        store.makedirs(arcdir)
        os.rename(filepath, arcdir + ("/%d" % old_time))
    inventory_tree.save_to(cmk.utils.paths.inventory_output_dir, hostname)
    return old_tree


def _save_status_data_tree(hostname: HostName, status_data_tree: StructuredDataTree) -> None:
    if status_data_tree and not status_data_tree.is_empty():
        store.makedirs(cmk.utils.paths.status_data_dir)
        status_data_tree.save_to(cmk.utils.paths.status_data_dir, hostname)


def _run_inventory_export_hooks(host_config: config.HostConfig,
                                inventory_tree: StructuredDataTree) -> None:
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel
    hooks = host_config.inventory_export_hooks

    if not hooks:
        return

    section.section_step("Execute inventory export hooks")
    for hookname, params in hooks:
        console.verbose("Execute export hook: %s%s%s%s" %
                        (tty.blue, tty.bold, hookname, tty.normal))
        try:
            func = inventory_plugins.inv_export[hookname]["export_function"]
            func(host_config.hostname, params, inventory_tree.get_raw_tree())
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException("Failed to execute export hook %s: %s" % (hookname, e))


#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   +----------------------------------------------------------------------+
#   | Helper API for being used in inventory plugins. Plugins have access  |
#   | to all things defined by the regular Checkmk check API and all the  |
#   | things declared here.                                                |
#   '----------------------------------------------------------------------'


def get_inventory_context() -> config.InventoryContext:
    return {
        "inv_tree_list": inv_tree_list,
        "inv_tree": inv_tree,
        "HostLabel": HostLabel,
    }
