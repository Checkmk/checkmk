#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Currently this module manages the inventory tree which is built
while the inventory is performed for one host.

In the future all inventory code should be moved to this module."""

import functools
import os
from typing import Dict, List, Optional, Tuple

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
    Metric,
    ServiceAdditionalDetails,
    ServiceDetails,
    ServiceState,
)

import cmk.snmplib.snmp_scan as snmp_scan

import cmk.base.check_api as check_api
import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.data_sources as data_sources
import cmk.base.decorator
import cmk.base.ip_lookup as ip_lookup
import cmk.base.section as section
from cmk.base.data_sources.host_sections import MultiHostSections
from cmk.base.data_sources.snmp import SNMPHostSections
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

    for hostname in hostnames:
        section.section_begin(hostname)
        try:
            host_config = config.HostConfig.make_host_config(hostname)
            if host_config.is_cluster:
                ipaddress = None
            else:
                ipaddress = ip_lookup.lookup_ip_address(hostname)

            sources = data_sources.DataSources(
                hostname,
                ipaddress,
                sources=data_sources.make_sources(host_config, ipaddress),
            )
            inventory_tree, status_data_tree = _do_inv_for(
                sources,
                multi_host_sections=None,
                host_config=host_config,
                ipaddress=ipaddress,
            )
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
) -> Tuple[ServiceState, List[ServiceDetails], List[ServiceAdditionalDetails], Metric]:
    _inv_hw_changes = options.get("hw-changes", 0)
    _inv_sw_changes = options.get("sw-changes", 0)
    _inv_sw_missing = options.get("sw-missing", 0)
    _inv_fail_status = options.get("inv-fail-status", 1)

    host_config = config.HostConfig.make_host_config(hostname)
    if host_config.is_cluster:
        ipaddress = None
    else:
        ipaddress = ip_lookup.lookup_ip_address(hostname)

    status = 0
    infotexts: List[str] = []
    long_infotexts: List[str] = []
    perfdata: List[Tuple] = []

    sources = data_sources.DataSources(
        hostname,
        ipaddress,
        sources=data_sources.make_sources(host_config, ipaddress),
    )
    inventory_tree, status_data_tree = _do_inv_for(
        sources,
        multi_host_sections=None,
        host_config=host_config,
        ipaddress=ipaddress,
    )

    #TODO add cluster if and only if all sources do not fail?
    if _all_sources_fail(host_config, sources):
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

    for source in sources:
        source_state, source_output, _source_perfdata = source.get_summary_result_for_inventory()
        if source_state != 0:
            # Do not output informational things (state == 0). Also do not use source states
            # which would overwrite "State when inventory fails" in the ruleset
            # "Do hardware/software Inventory".
            # These information and source states are handled by the "Check_MK" service
            status = max(_inv_fail_status, status)
            infotexts.append("[%s] %s" % (source.id(), source_output))

    return status, infotexts, long_infotexts, perfdata


def _all_sources_fail(host_config: config.HostConfig, sources: data_sources.DataSources) -> bool:
    """We want to check if ALL data sources of a host fail:
    By default a host has the auto-piggyback data source. We remove it if
    it's not a pure piggyback host and there's no piggyback data available
    for this host.
    In this case the piggyback data source never fails (self._exception = None)."""
    if host_config.is_cluster:
        return False

    exceptions_by_source = {source.id(): source.exception() for source in sources}
    if "piggyback" in exceptions_by_source and not len(exceptions_by_source) == 1\
       and not host_config.has_piggyback_data:
        del exceptions_by_source["piggyback"]

    return all(exception is not None for exception in exceptions_by_source.values())


def do_inventory_actions_during_checking_for(sources: data_sources.DataSources,
                                             multi_host_sections: MultiHostSections,
                                             host_config: config.HostConfig,
                                             ipaddress: Optional[HostAddress]) -> None:
    hostname = host_config.hostname
    do_status_data_inventory = not host_config.is_cluster and host_config.do_status_data_inventory

    if not do_status_data_inventory:
        _cleanup_status_data(hostname)

    if not do_status_data_inventory:
        return  # nothing to do here

    # This is called during checking, but the inventory plugins are not loaded yet
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel
    inventory_plugins.load_plugins(check_api.get_check_api_context, get_inventory_context)

    _inventory_tree, status_data_tree = _do_inv_for(
        sources,
        multi_host_sections=multi_host_sections,
        host_config=config.HostConfig.make_host_config(hostname),
        ipaddress=ipaddress,
    )
    _save_status_data_tree(hostname, status_data_tree)


def _cleanup_status_data(hostname: HostName) -> None:
    filepath = "%s/%s" % (cmk.utils.paths.status_data_dir, hostname)
    if os.path.exists(filepath):  # Remove empty status data files.
        os.remove(filepath)
    if os.path.exists(filepath + ".gz"):
        os.remove(filepath + ".gz")


def _do_inv_for(sources: data_sources.DataSources, multi_host_sections: Optional[MultiHostSections],
                host_config: config.HostConfig,
                ipaddress: Optional[HostAddress]) -> Tuple[StructuredDataTree, StructuredDataTree]:
    hostname = host_config.hostname

    _initialize_inventory_tree()
    inventory_tree = g_inv_tree
    status_data_tree = StructuredDataTree()

    node = inventory_tree.get_dict("software.applications.check_mk.cluster.")
    if host_config.is_cluster:
        node["is_cluster"] = True
        _do_inv_for_cluster(host_config, inventory_tree)
    else:
        node["is_cluster"] = False
        _do_inv_for_realhost(host_config, sources, multi_host_sections, hostname, ipaddress,
                             inventory_tree, status_data_tree)

    inventory_tree.normalize_nodes()
    status_data_tree.normalize_nodes()
    return inventory_tree, status_data_tree


def _do_inv_for_cluster(host_config: config.HostConfig, inventory_tree: StructuredDataTree) -> None:
    if host_config.nodes is None:
        return

    inv_node = inventory_tree.get_list("software.applications.check_mk.cluster.nodes:")
    for node_name in host_config.nodes:
        inv_node.append({
            "name": node_name,
        })


def _do_inv_for_realhost(host_config: config.HostConfig, sources: data_sources.DataSources,
                         multi_host_sections: Optional[MultiHostSections], hostname: HostName,
                         ipaddress: Optional[HostAddress], inventory_tree: StructuredDataTree,
                         status_data_tree: StructuredDataTree) -> None:
    for source in sources:
        if isinstance(source, data_sources.snmp.SNMPDataSource):
            source.set_on_error("raise")
            source.set_do_snmp_scan(True)
            data_sources.snmp.SNMPDataSource.disable_data_source_cache()
            source.set_use_snmpwalk_cache(False)
            source.set_ignore_check_interval(True)
            source.set_check_plugin_name_filter(functools.partial(
                snmp_scan.gather_available_raw_section_names,
                for_mgmt_board=False,
            ),
                                                inventory=True)
            if multi_host_sections is not None:
                # Status data inventory already provides filled multi_host_sections object.
                # SNMP data source: If 'do_status_data_inv' is enabled there may be
                # sections for inventory plugins which were not fetched yet.
                host_sections = multi_host_sections.setdefault(
                    (hostname, ipaddress, source.source_type),
                    SNMPHostSections(),
                )
                source.set_fetched_raw_section_names(set(host_sections.sections))
                host_sections.update(source.run())

    if multi_host_sections is None:
        nodes = sources.make_nodes(host_config)
        multi_host_sections = sources.get_host_sections(
            nodes, max_cachefile_age=host_config.max_cachefile_age)

    section.section_step("Executing inventory plugins")
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel
    console.verbose("Plugins:")
    for section_name, plugin in inventory_plugins.sorted_inventory_plugins():
        section_content = multi_host_sections.get_section_content(
            hostname,
            ipaddress,
            check_api_utils.HOST_PRECEDENCE,
            section_name,
            for_discovery=False,
        )
        if not section_content:  # section not present (None or [])
            # Note: this also excludes existing sections without info..
            continue

        if all([x in [[], {}, None] for x in section_content]):
            # Inventory plugins which get parsed info from related
            # check plugin may have more than one return value, eg
            # parse function of oracle_tablespaces returns ({}, {})
            continue

        console.verbose(" %s%s%s%s" % (tty.green, tty.bold, section_name, tty.normal))

        # Inventory functions can optionally have a second argument: parameters.
        # These are configured via rule sets (much like check parameters).
        inv_function = plugin["inv_function"]
        kwargs = cmk.utils.misc.make_kwargs_for(inv_function,
                                                inventory_tree=inventory_tree,
                                                status_data_tree=status_data_tree)
        non_kwargs = set(cmk.utils.misc.getfuncargs(inv_function)) - set(kwargs)
        args = [section_content]
        if len(non_kwargs) == 2:
            args += [host_config.inventory_parameters(section_name)]
        inv_function(*args, **kwargs)
    console.verbose("\n")


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


def _initialize_inventory_tree() -> None:  # TODO Remove one day. Deprecated with version 1.5.0i3??
    global g_inv_tree
    g_inv_tree = StructuredDataTree()


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
#   | to all things defined by the regular Check_MK check API and all the  |
#   | things declared here.                                                |
#   '----------------------------------------------------------------------'


def get_inventory_context() -> config.InventoryContext:
    return {
        "inv_tree_list": inv_tree_list,
        "inv_tree": inv_tree,
        "HostLabel": HostLabel,
    }
