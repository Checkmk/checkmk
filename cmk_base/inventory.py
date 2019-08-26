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

import gzip
import inspect
import os
import pprint
import re
import sys

import cmk
import cmk.paths
import cmk.store
import cmk.tty as tty
from cmk.exceptions import MKGeneralException
from cmk.structured_data import StructuredDataTree

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.rulesets as rulesets
import cmk_base.checks as checks
import cmk_base.check_api as check_api
import cmk_base.snmp as snmp
import cmk_base.checking as checking
import cmk_base.discovery as discovery
import cmk_base.ip_lookup as ip_lookup
import cmk_base.data_sources as data_sources

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
    cmk.store.makedirs(cmk.paths.inventory_output_dir)
    cmk.store.makedirs(cmk.paths.inventory_archive_dir)

    for hostname in hostnames:
        console.section_begin(hostname)
        try:
            if config.is_cluster(hostname):
                ipaddress = None
            else:
                ipaddress = ip_lookup.lookup_ip_address(hostname)

            sources = data_sources.DataSources(hostname, ipaddress)
            _do_inv_for(sources, multi_host_sections=None, hostname=hostname, ipaddress=ipaddress,
                        do_status_data_inv=checks.do_status_data_inventory_for(hostname))
        except Exception, e:
            if cmk.debug.enabled():
                raise

            console.section_error("%s" % e)
        finally:
            cmk_base.utils.cleanup_globals()


@checking.handle_check_mk_check_result("check_mk_active-cmk_inv", "Check_MK HW/SW Inventory")
def do_inv_check(hostname, options):
    _inv_hw_changes  = options.get("hw-changes", 0)
    _inv_sw_changes  = options.get("sw-changes", 0)
    _inv_sw_missing  = options.get("sw-missing", 0)
    _inv_fail_status = options.get("inv-fail-status", 1) # State in case of an error (default: WARN)

    if config.is_cluster(hostname):
        ipaddress = None
    else:
        ipaddress = ip_lookup.lookup_ip_address(hostname)

    status, infotexts, long_infotexts, perfdata = 0, [], [], []

    sources = data_sources.DataSources(hostname, ipaddress)
    old_timestamp, inventory_tree, status_data_tree =\
        _do_inv_for(sources, multi_host_sections=None,
                    hostname=hostname, ipaddress=ipaddress,
                    do_status_data_inv=checks.do_status_data_inventory_for(hostname))

    if inventory_tree.is_empty() and status_data_tree.is_empty():
        infotexts.append("Found no data")

    else:
        infotexts.append("Found %d inventory entries" % inventory_tree.count_entries())

        # Node 'software' is always there because _do_inv_for creates this node for cluster info
        if not inventory_tree.get_sub_container(['software']).has_edge('packages')\
           and _inv_sw_missing:
            infotexts.append("software packages information is missing" +
                             check_api.state_markers[_inv_sw_missing])
            status = max(status, _inv_sw_missing)

        if old_timestamp:
            path = "%s/%s/%d" % (cmk.paths.inventory_archive_dir, hostname, old_timestamp)
            old_tree = StructuredDataTree().load_from(path)

            if not old_tree.is_equal(inventory_tree, edges=["software"]):
                infotext = "software changes"
                if _inv_sw_changes:
                    status = max(status, _inv_sw_changes)
                    infotext += check_api.state_markers[_inv_sw_changes]
                infotexts.append(infotext)

            if not old_tree.is_equal(inventory_tree, edges=["hardware"]):
                infotext = "hardware changes"
                if _inv_hw_changes:
                    status = max(status, _inv_hw_changes)
                    infotext += check_api.state_markers[_inv_hw_changes]

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


def do_status_data_inventory(sources, multi_host_sections, hostname, ipaddress):
    if config.is_cluster(hostname):
        return
    # cmk_base/modes/check_mk.py loads check plugins but not inventory plugins
    import cmk_base.inventory_plugins as inventory_plugins
    inventory_plugins.load()
    _do_inv_for(sources, multi_host_sections=multi_host_sections, hostname=hostname,
                ipaddress=ipaddress, do_status_data_inv=True)


def _do_inv_for(sources, multi_host_sections, hostname, ipaddress, do_status_data_inv):
    _initialize_inventory_tree()
    inventory_tree = g_inv_tree
    status_data_tree = StructuredDataTree()

    node = inventory_tree.get_dict("software.applications.check_mk.cluster.")
    if config.is_cluster(hostname):
        node["is_cluster"] = True
        _do_inv_for_cluster(hostname, inventory_tree)
    else:
        node["is_cluster"] = False
        _do_inv_for_realhost(sources, multi_host_sections, hostname, ipaddress,
                             inventory_tree, status_data_tree)

    inventory_tree.normalize_nodes()
    old_timestamp = _save_inventory_tree(hostname, inventory_tree)

    _run_inventory_export_hooks(hostname, inventory_tree)

    console.section_success("Found %s%s%d%s inventory entries" %
            (tty.bold, tty.yellow, inventory_tree.count_entries(), tty.normal))

    if do_status_data_inv:
        status_data_tree.normalize_nodes()
        _save_status_data_tree(hostname, status_data_tree)

        console.section_success("Found %s%s%d%s status entries" %
                (tty.bold, tty.yellow, status_data_tree.count_entries(), tty.normal))

    return old_timestamp, inventory_tree, status_data_tree


def _do_inv_for_cluster(hostname, inventory_tree):
    inv_node = inventory_tree.get_list("software.applications.check_mk.cluster.nodes:")
    for node_name in config.nodes_of(hostname):
        inv_node.append({
            "name" : node_name,
        })


def _do_inv_for_realhost(sources, multi_host_sections, hostname, ipaddress,
                         inventory_tree, status_data_tree):
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
                host_sections = multi_host_sections.add_or_get_host_sections(hostname, ipaddress)
                source.set_fetched_check_plugin_names(host_sections.sections.keys())
                host_sections_from_source = source.run()
                host_sections.update(host_sections_from_source)

    if multi_host_sections is None:
        multi_host_sections = sources.get_host_sections()

    console.step("Executing inventory plugins")
    import cmk_base.inventory_plugins as inventory_plugins
    console.verbose("Plugins:")

    for section_name, plugin in inventory_plugins.sorted_inventory_plugins():
        section_content = multi_host_sections.get_section_content(hostname, ipaddress,
                                                                  section_name, for_discovery=False)
        if section_content is None: # No data for this check type
            continue

        # TODO: Don't we need to take checks.check_info[check_plugin_name]["handle_empty_info"]:
        #       like it is done in checking.execute_check()? Standardize this!
        if not section_content: # section not present (None or [])
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
        inv_function_args = inspect.getargspec(inv_function).args

        kwargs = {}
        if 'inventory_tree' in inv_function_args:
            inv_function_args.remove('inventory_tree')
            kwargs["inventory_tree"] = inventory_tree
        if 'status_data_tree' in inv_function_args:
            inv_function_args.remove('status_data_tree')
            kwargs["status_data_tree"] = status_data_tree

        if len(inv_function_args) == 2:
            params = _get_inv_params(hostname, section_name)
            args = [section_content, params]
        else:
            args = [section_content]
        inv_function(*args, **kwargs)
    console.verbose("\n")


def _gather_snmp_check_plugin_names_inventory(access_data, on_error, do_snmp_scan, for_mgmt_board=False):
    return discovery.gather_snmp_check_plugin_names(access_data, on_error, do_snmp_scan,
                                                    for_inventory=True, for_mgmt_board=for_mgmt_board)


def _get_inv_params(hostname, section_name):
    return rulesets.host_extra_conf_merged(hostname, config.inv_parameters.get(section_name, []))

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


g_inv_tree = StructuredDataTree() # TODO Remove one day. Deprecated with version 1.5.0i3??


def _initialize_inventory_tree(): # TODO Remove one day. Deprecated with version 1.5.0i3??
    global g_inv_tree
    g_inv_tree = StructuredDataTree()


# Dict based
def inv_tree(path): # TODO Remove one day. Deprecated with version 1.5.0i3??
    return g_inv_tree.get_dict(path)


# List based
def inv_tree_list(path): # TODO Remove one day. Deprecated with version 1.5.0i3??
    return g_inv_tree.get_list(path)


def _save_inventory_tree(hostname, inventory_tree):
    cmk.store.makedirs(cmk.paths.inventory_output_dir)

    old_time = None
    filepath = cmk.paths.inventory_output_dir + "/" + hostname
    if not inventory_tree.is_empty():
        old_tree = StructuredDataTree().load_from(filepath)
        old_tree.normalize_nodes()
        if old_tree.is_equal(inventory_tree):
            console.verbose("Inventory was unchanged\n")
        else:
            if old_tree.is_empty():
                console.verbose("New inventory tree\n")
            else:
                console.verbose("Inventory tree has changed\n")
                old_time = os.stat(filepath).st_mtime
                arcdir = "%s/%s" % (cmk.paths.inventory_archive_dir, hostname)
                cmk.store.makedirs(arcdir)
                os.rename(filepath, arcdir + ("/%d" % old_time))
            inventory_tree.save_to(cmk.paths.inventory_output_dir, hostname)

    else:
        if os.path.exists(filepath): # Remove empty inventory files. Important for host inventory icon
            os.remove(filepath)
        if os.path.exists(filepath + ".gz"):
            os.remove(filepath + ".gz")

    return old_time


def _save_status_data_tree(hostname, status_data_tree):
    if status_data_tree and not status_data_tree.is_empty():
        cmk.store.makedirs(cmk.paths.status_data_dir)
        status_data_tree.save_to(cmk.paths.status_data_dir, hostname)


def _run_inventory_export_hooks(hostname, inventory_tree):
    import cmk_base.inventory_plugins as inventory_plugins
    hooks = []
    for hookname, ruleset in config.inv_exports.items():
        entries = rulesets.host_extra_conf(hostname, ruleset)
        if entries:
            hooks.append((hookname, entries[0]))

    if not hooks:
        return

    console.step("Execute inventory export hooks")
    for hookname, params in hooks:
        console.verbose("Execute export hook: %s%s%s%s" %
                            (tty.blue, tty.bold, hookname, tty.normal))
        try:
            func = inventory_plugins.inv_export[hookname]["export_function"]
            func(hostname, params, inventory_tree.get_raw_tree())
        except Exception, e:
            if cmk.debug.enabled():
                raise
            raise MKGeneralException("Failed to execute export hook %s: %s" % (
                hookname, e))
