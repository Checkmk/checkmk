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

import cmk.tty as tty
import cmk.paths
import cmk.defines as defines

import cmk_base.console as console
import cmk_base.checks as checks
import cmk_base.inventory as inventory
import cmk_base.inventory_plugins as inventory_plugins


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
    ensure_directory(inventory.inventory_output_dir)
    ensure_directory(inventory.inventory_archive_dir)

    # No hosts specified: do all hosts and force caching
    if hostnames == None:
        hostnames = config.all_active_hosts()
        set_use_cachefile()

    errors = []
    for hostname in hostnames:
        try:
            console.verbose("Doing HW/SW-Inventory for %s..." % hostname)
            do_inv_for(hostname)
            console.verbose("..OK\n")
        except Exception, e:
            if cmk.debug.enabled():
                raise
            console.verbose("Failed: %s\n" % e)
            errors.append("Failed to inventorize %s: %s" % (hostname, e))
        cleanup_globals()

    if errors:
        raise MKGeneralException("\n".join(errors))


def do_inv_check(hostname):
    try:
        inv_tree, old_timestamp = do_inv_for(hostname)
        num_entries = inventory.count_nodes()
        if not num_entries:
            console.output("OK - Found no data\n")
            sys.exit(0)

        infotext = "found %d entries" % num_entries
        state = 0
        if not inv_tree.get("software") and opt_inv_sw_missing:
            infotext += ", software information is missing"
            state = opt_inv_sw_missing
            infotext += checks.state_markers[opt_inv_sw_missing]

        if old_timestamp:
            path = inventory.inventory_archive_dir + "/" + hostname + "/%d" % old_timestamp
            old_tree = eval(file(path).read())

            if inv_tree.get("software") != old_tree.get("software"):
                infotext += ", software changes"
                if opt_inv_sw_changes:
                    state = opt_inv_sw_changes
                    infotext += checks.state_markers[opt_inv_sw_changes]

            if inv_tree.get("hardware") != old_tree.get("hardware"):
                infotext += ", hardware changes"
                if state == 2 or opt_inv_hw_changes == 2:
                    state = 2
                else:
                    state = max(state, opt_inv_sw_changes)
                if opt_inv_hw_changes:
                    infotext += checks.state_markers[opt_inv_hw_changes]

        console.output(defines.short_service_state_name(state) + " - " + infotext + "\n")
        sys.exit(state)

    except Exception, e:
        if cmk.debug.enabled():
            raise
        console.output("Inventory failed: %s\n" % e)
        sys.exit(opt_inv_fail_status)


def do_inv_for(hostname):
    inventory.initialize_inventory_tree()

    node = inventory.inv_tree("software.applications.check_mk.cluster.")

    if is_cluster(hostname):
        node["is_cluster"] = True
        do_inv_for_cluster(hostname)
    else:
        node["is_cluster"] = False
        do_inv_for_realhost(hostname)

    # Remove empty paths
    inventory.cleanup_inventory_tree()
    old_timestamp = inventory.save_inventory_tree(hostname)

    console.verbose("..%s%s%d%s entries" %
            (tty.bold, tty.yellow, inventory.count_nodes(), tty.normal))

    inventory.run_inventory_export_hooks(hostname)
    return inventory.get_inventory_tree(), old_timestamp


def do_inv_for_cluster(hostname):
    inv_node = inventory.inv_tree_list("software.applications.check_mk.cluster.nodes:")
    for node_name in nodes_of(hostname):
        inv_node.append({
            "name" : node_name,
        })


def do_inv_for_realhost(hostname):
    try:
        ipaddress = lookup_ip_address(hostname)
    except:
        raise MKGeneralException("Cannot resolve hostname '%s'." % hostname)

    # If this is an SNMP host then determine the SNMP sections
    # that this device supports.
    if is_snmp_host(hostname):
        snmp_check_types = snmp_scan(hostname, ipaddress, for_inv=True)
    else:
        snmp_check_types = []

    import cmk_base.inventory_plugins
    for info_type, plugin in cmk_base.inventory_plugins.inv_info.items():
        # Skip SNMP sections that are not supported by this device
        use_caches = True
        if check_uses_snmp(info_type):
            use_caches = False
            if info_type not in snmp_check_types:
                continue

        try:
            info = get_info_for_discovery(hostname, ipaddress, info_type, use_caches=use_caches)
        except Exception, e:
            if str(e):
                raise # Otherwise simply ignore missing agent section
            continue

        if not info: # section not present (None or [])
            # Note: this also excludes existing sections without info..
            continue

        console.verbose(tty.green + tty.bold + info_type + " " + tty.normal)

        # Inventory functions can optionally have a second argument: parameters.
        # These are configured via rule sets (much like check parameters).
        inv_function = plugin["inv_function"]
        if len(inspect.getargspec(inv_function).args) == 2:
            params = get_inv_params(hostname, info_type)
            inv_function(info, params)
        else:
            inv_function(info)


def get_inv_params(hostname, info_type):
    return rulesets.host_extra_conf_merged(hostname, config.inv_parameters.get(info_type, []))
