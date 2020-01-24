#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Currently this module manages the inventory tree which is built
while the inventory is performed for one host.

In the future all inventory code should be moved to this module."""

import os
from typing import Set, Tuple, Optional, List, Dict, Text  # pylint: disable=unused-import

import cmk
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.structured_data import StructuredDataTree
import cmk.utils.debug

import cmk.base.utils
import cmk.base.console as console
import cmk.base.config as config
import cmk.base.check_api_utils as check_api_utils
import cmk.base.snmp_scan as snmp_scan
import cmk.base.ip_lookup as ip_lookup
import cmk.base.data_sources as data_sources
import cmk.base.cleanup
import cmk.base.decorator
import cmk.base.check_api as check_api
from cmk.base.data_sources.snmp import SNMPHostSections

from cmk.base.utils import HostName, HostAddress, CheckPluginName  # pylint: disable=unused-import
from cmk.base.snmp_utils import SNMPHostConfig  # pylint: disable=unused-import
from cmk.base.check_utils import (  # pylint: disable=unused-import
    ServiceState, ServiceDetails, ServiceAdditionalDetails, Metric,
)

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


def do_inv(hostnames):
    # type: (List[HostName]) -> None
    store.makedirs(cmk.utils.paths.inventory_output_dir)
    store.makedirs(cmk.utils.paths.inventory_archive_dir)

    for hostname in hostnames:
        console.section_begin(hostname)
        try:
            config_cache = config.get_config_cache()
            host_config = config_cache.get_host_config(hostname)

            if host_config.is_cluster:
                ipaddress = None
            else:
                ipaddress = ip_lookup.lookup_ip_address(hostname)

            sources = data_sources.DataSources(hostname, ipaddress)
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

            console.section_error("%s" % e)
        finally:
            cmk.base.cleanup.cleanup_globals()


def _show_inventory_results_on_console(inventory_tree, status_data_tree):
    # type: (StructuredDataTree, StructuredDataTree) -> None
    console.section_success("Found %s%s%d%s inventory entries" %
                            (tty.bold, tty.yellow, inventory_tree.count_entries(), tty.normal))
    console.section_success("Found %s%s%d%s status entries" %
                            (tty.bold, tty.yellow, status_data_tree.count_entries(), tty.normal))


@cmk.base.decorator.handle_check_mk_check_result("check_mk_active-cmk_inv",
                                                 "Check_MK HW/SW Inventory")
def do_inv_check(hostname, options):
    # type: (HostName, Dict[str, int]) -> Tuple[ServiceState, List[ServiceDetails], List[ServiceAdditionalDetails], Metric]
    _inv_hw_changes = options.get("hw-changes", 0)
    _inv_sw_changes = options.get("sw-changes", 0)
    _inv_sw_missing = options.get("sw-missing", 0)
    _inv_fail_status = options.get("inv-fail-status",
                                   1)  # State in case of an error (default: WARN)

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)  # type: config.HostConfig

    if host_config.is_cluster:
        ipaddress = None
    else:
        ipaddress = ip_lookup.lookup_ip_address(hostname)

    status = 0
    infotexts = []  # type: List[Text]
    long_infotexts = []  # type: List[Text]
    perfdata = []  # type: List[Tuple]

    sources = data_sources.DataSources(hostname, ipaddress)
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

    for source in sources.get_data_sources():
        source_state, source_output, _source_perfdata = source.get_summary_result_for_inventory()
        # Do not output informational (state = 0) things. These information are shown by the "Check_MK" service
        if source_state != 0:
            status = max(source_state, status)
            infotexts.append("[%s] %s" % (source.id(), source_output))

    return status, infotexts, long_infotexts, perfdata


def _all_sources_fail(host_config, sources):
    # type: (config.HostConfig, data_sources.DataSources) -> bool
    """We want to check if ALL data sources of a host fail:
    By default a host has the auto-piggyback data source. We remove it if
    it's not a pure piggyback host and there's no piggyback data available
    for this host.
    In this case the piggyback data source never fails (self._exception = None)."""
    if host_config.is_cluster:
        return False

    exceptions_by_source = {
        source.id(): source.exception() for source in sources.get_data_sources()
    }
    if "piggyback" in exceptions_by_source and not len(exceptions_by_source) == 1\
       and not host_config.has_piggyback_data:
        del exceptions_by_source["piggyback"]

    return all(exception is not None for exception in exceptions_by_source.values())


def do_inventory_actions_during_checking_for(sources, multi_host_sections, host_config, ipaddress):
    # type: (data_sources.DataSources, data_sources.MultiHostSections, config.HostConfig, Optional[HostAddress]) -> None
    hostname = host_config.hostname
    do_status_data_inventory = not host_config.is_cluster and host_config.do_status_data_inventory

    if not do_status_data_inventory:
        _cleanup_status_data(hostname)

    if not do_status_data_inventory:
        return  # nothing to do here

    # This is called during checking, but the inventory plugins are not loaded yet
    import cmk.base.inventory_plugins as inventory_plugins
    inventory_plugins.load_plugins(check_api.get_check_api_context, get_inventory_context)

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    _inventory_tree, status_data_tree = _do_inv_for(
        sources,
        multi_host_sections=multi_host_sections,
        host_config=host_config,
        ipaddress=ipaddress,
    )
    _save_status_data_tree(hostname, status_data_tree)


def _cleanup_status_data(hostname):
    # type: (HostName) -> None
    filepath = "%s/%s" % (cmk.utils.paths.status_data_dir, hostname)
    if os.path.exists(filepath):  # Remove empty status data files.
        os.remove(filepath)
    if os.path.exists(filepath + ".gz"):
        os.remove(filepath + ".gz")


def _do_inv_for(sources, multi_host_sections, host_config, ipaddress):
    # type: (data_sources.DataSources, Optional[data_sources.MultiHostSections], config.HostConfig, Optional[HostAddress]) -> Tuple[StructuredDataTree, StructuredDataTree]
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


def _do_inv_for_cluster(host_config, inventory_tree):
    # type: (config.HostConfig, StructuredDataTree) -> None
    if host_config.nodes is None:
        return

    inv_node = inventory_tree.get_list("software.applications.check_mk.cluster.nodes:")
    for node_name in host_config.nodes:
        inv_node.append({
            "name": node_name,
        })


def _do_inv_for_realhost(host_config, sources, multi_host_sections, hostname, ipaddress,
                         inventory_tree, status_data_tree):
    # type: (config.HostConfig, data_sources.DataSources, Optional[data_sources.MultiHostSections], HostName, Optional[HostAddress], StructuredDataTree, StructuredDataTree) -> None
    for source in sources.get_data_sources():
        if isinstance(source, data_sources.SNMPDataSource):
            source.set_on_error("raise")
            source.set_do_snmp_scan(True)
            source.disable_data_source_cache()
            source.set_use_snmpwalk_cache(False)
            source.set_ignore_check_interval(True)
            source.set_check_plugin_name_filter(_gather_snmp_check_plugin_names_inventory)
            if multi_host_sections is not None:
                # Status data inventory already provides filled multi_host_sections object.
                # SNMP data source: If 'do_status_data_inv' is enabled there may be
                # sections for inventory plugins which were not fetched yet.
                source.enforce_check_plugin_names(None)
                host_sections = multi_host_sections.add_or_get_host_sections(
                    hostname, ipaddress, deflt=SNMPHostSections())
                source.set_fetched_check_plugin_names(set(host_sections.sections.keys()))
                host_sections_from_source = source.run()
                host_sections.update(host_sections_from_source)

    if multi_host_sections is None:
        multi_host_sections = sources.get_host_sections()

    console.step("Executing inventory plugins")
    import cmk.base.inventory_plugins as inventory_plugins
    console.verbose("Plugins:")
    for section_name, plugin in inventory_plugins.sorted_inventory_plugins():
        section_content = multi_host_sections.get_section_content(hostname,
                                                                  ipaddress,
                                                                  section_name,
                                                                  for_discovery=False)
        # TODO: Don't we need to take config.check_info[check_plugin_name]["handle_empty_info"]:
        #       like it is done in checking.execute_check()? Standardize this!
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
        non_kwargs = set(cmk.utils.misc.getfuncargs(inv_function)) - set(kwargs.keys())
        args = [section_content]
        if len(non_kwargs) == 2:
            args += [host_config.inventory_parameters(section_name)]
        inv_function(*args, **kwargs)
    console.verbose("\n")


def _gather_snmp_check_plugin_names_inventory(snmp_host_config,
                                              on_error,
                                              do_snmp_scan,
                                              for_mgmt_board=False):
    # type: (SNMPHostConfig, str, bool, bool) -> Set[CheckPluginName]
    return snmp_scan.gather_snmp_check_plugin_names(snmp_host_config,
                                                    on_error,
                                                    do_snmp_scan,
                                                    for_inventory=True,
                                                    for_mgmt_board=for_mgmt_board)


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


def _initialize_inventory_tree():  # TODO Remove one day. Deprecated with version 1.5.0i3??
    # type: () -> None
    global g_inv_tree
    g_inv_tree = StructuredDataTree()


# Dict based
def inv_tree(path):  # TODO Remove one day. Deprecated with version 1.5.0i3??
    # type: (str) -> Dict
    return g_inv_tree.get_dict(path)


# List based
def inv_tree_list(path):  # TODO Remove one day. Deprecated with version 1.5.0i3??
    # type: (str) -> List
    return g_inv_tree.get_list(path)


def _save_inventory_tree(hostname, inventory_tree):
    # type: (HostName, StructuredDataTree) -> Optional[StructuredDataTree]
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


def _save_status_data_tree(hostname, status_data_tree):
    # type: (HostName, StructuredDataTree) -> None
    if status_data_tree and not status_data_tree.is_empty():
        store.makedirs(cmk.utils.paths.status_data_dir)
        status_data_tree.save_to(cmk.utils.paths.status_data_dir, hostname)


def _run_inventory_export_hooks(host_config, inventory_tree):
    # type: (config.HostConfig, StructuredDataTree) -> None
    import cmk.base.inventory_plugins as inventory_plugins
    hooks = host_config.inventory_export_hooks

    if not hooks:
        return

    console.step("Execute inventory export hooks")
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

from cmk.base.discovered_labels import HostLabel


def get_inventory_context():
    # type: () -> config.InventoryContext
    return {
        "inv_tree_list": inv_tree_list,
        "inv_tree": inv_tree,
        "HostLabel": HostLabel,
    }
