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

import gzip

import cmk.tty as tty
import cmk.paths

import cmk_base.console as console
import cmk_base.checks as checks

inventory_output_dir = cmk.paths.var_dir + "/inventory"
inventory_archive_dir = cmk.paths.var_dir + "/inventory_archive"
inventory_pprint_output = True

#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Code for reading the inventory plugins, help functions that are      |
#   | called by the plugins.
#   '----------------------------------------------------------------------'

# Plugins register here
inv_info = {}   # Inventory plugins
inv_export = {} # Inventory export hooks

# Read all inventory plugins right now
filelist = checks.plugin_pathnames_in_directory(cmk.paths.inventory_dir) \
         + checks.plugin_pathnames_in_directory(cmk.paths.local_inventory_dir)


# read include files always first, but still in the sorted
# order with local ones last (possibly overriding variables)
filelist = [ f for f in filelist if f.endswith(".include") ] + \
           [ f for f in filelist if not f.endswith(".include") ]

for f in filelist:
    if not f.endswith("~"): # ignore emacs-like backup files
        try:
            execfile(f)
        except Exception, e:
            console.output("Error in inventory plugin file %s: %s\n", f, e, stream=sys.stderr)
            if cmk.debug.enabled():
                raise
            sys.exit(5)


# This is just a small wrapper for the inv_tree() function which makes
# it clear that the requested tree node is treated as a list.
def inv_tree_list(path):
    # The [] is needed to tell pylint that a list is returned
    return inv_tree(path, [])


# Function for accessing the inventory tree of the current host
# Example: path = "software.packages:17."
# The path must end with : or .
# -> software is a dict
# -> packages is a list
def inv_tree(path, default_value=None):
    if default_value != None:
        node = default_value
    else:
        node = {}

    current_what = "."
    current_path = ""

    while path:
        if current_path == "":
            node = g_inv_tree

        parts = re.split("[:.]", path)
        name = parts[0]
        what = path[len(name)]
        path = path[1 + len(name):]
        current_path += what + name

        if current_what == '.': # node is a dict
            if name not in node:
                if what == '.':
                    node[name] = {}
                else:
                    node[name] = []
            node = node[name]

        else: # node is a list
            try:
                index = int(name)
            except:
                raise MKGeneralException("Cannot convert index %s of path %s into int" % (name, current_path))

            if type(node) != list:
                raise MKGeneralException("Path %s is exptected to by of type list, but is dict" % current_path)

            if index < 0 or index >= len(node):
                raise MKGeneralException("Index %d not existing in list node %s" % (index, current_path))
            node = node[index]

        current_what = what

    return node


# Removes empty nodes from a (sub)-tree. Returns
# True if the tree itself is empty
def inv_cleanup_tree(tree):

    if type(tree) == dict:
        for key, value in tree.items():
            if inv_cleanup_tree(value):
                del tree[key]
        return not tree

    elif type(tree) == list:
        to_delete = []
        for nr, entry in enumerate(tree):
            if inv_cleanup_tree(entry):
                to_delete.append(nr)
        for nr in to_delete[::-1]:
            del tree[nr]
        return not tree

    else:
        return False # cannot clean non-container nodes

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
    ensure_directory(inventory_output_dir)
    ensure_directory(inventory_archive_dir)

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
        num_entries = count_nodes(g_inv_tree)
        if not num_entries:
            console.output("OK - Found no data\n")
            sys.exit(0)

        infotext = "found %d entries" % num_entries
        state = 0
        if not inv_tree.get("software") and opt_inv_sw_missing:
            infotext += ", software information is missing"
            state = opt_inv_sw_missing
            infotext += state_markers[opt_inv_sw_missing]

        if old_timestamp:
            path = inventory_archive_dir + "/" + hostname + "/%d" % old_timestamp
            old_tree = eval(file(path).read())

            if inv_tree.get("software") != old_tree.get("software"):
                infotext += ", software changes"
                if opt_inv_sw_changes:
                    state = opt_inv_sw_changes
                    infotext += state_markers[opt_inv_sw_changes]

            if inv_tree.get("hardware") != old_tree.get("hardware"):
                infotext += ", hardware changes"
                if state == 2 or opt_inv_hw_changes == 2:
                    state = 2
                else:
                    state = max(state, opt_inv_sw_changes)
                if opt_inv_hw_changes:
                    infotext += state_markers[opt_inv_hw_changes]

        console.output(core_state_names[state] + " - " + infotext + "\n")
        sys.exit(state)

    except Exception, e:
        if cmk.debug.enabled():
            raise
        console.output("Inventory failed: %s\n" % e)
        sys.exit(opt_inv_fail_status)


def count_nodes(tree):
    if type(tree) == dict:
        return len(tree) + sum([count_nodes(v) for v in tree.values()])
    elif type(tree) == list:
        return len(tree) + sum([count_nodes(v) for v in tree])
    elif tree == None:
        return 0
    else:
        return 1


def do_inv_for(hostname):
    global g_inv_tree
    g_inv_tree = {}

    node = inv_tree("software.applications.check_mk.cluster.")

    if is_cluster(hostname):
        node["is_cluster"] = True
        do_inv_for_cluster(hostname)
    else:
        node["is_cluster"] = False
        do_inv_for_realhost(hostname)

    # Remove empty paths
    inv_cleanup_tree(g_inv_tree)
    old_timestamp = save_inv_tree(hostname)

    console.verbose("..%s%s%d%s entries" % (tty.bold, tty.yellow, count_nodes(g_inv_tree), tty.normal))

    run_inv_export_hooks(hostname, g_inv_tree)
    return g_inv_tree, old_timestamp


def do_inv_for_cluster(hostname):
    inv_node = inv_tree_list("software.applications.check_mk.cluster.nodes:")
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

    for info_type, plugin in inv_info.items():
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
    return host_extra_conf_merged(hostname, config.inv_parameters.get(info_type, []))


# Returns the time stamp of the previous inventory with different
# outcome or None.
def save_inv_tree(hostname):
    if not os.path.exists(inventory_output_dir):
        os.makedirs(inventory_output_dir)

    old_time = None

    if inventory_pprint_output:
        r = pprint.pformat(g_inv_tree)
    else:
        r = repr(g_inv_tree)

    path = inventory_output_dir + "/" + hostname
    if g_inv_tree:
        old_tree = None
        if os.path.exists(path):
            try:
                old_tree = eval(file(path).read())
            except:
                pass

        if old_tree != g_inv_tree:
            if old_tree:
                console.verbose("..changed")
                old_time = os.stat(path).st_mtime
                arcdir = "%s/%s" % (inventory_archive_dir, hostname)
                if not os.path.exists(arcdir):
                    os.makedirs(arcdir)
                os.rename(path, arcdir + ("/%d" % old_time))
            else:
                console.verbose("..new")

            file(path, "w").write(r + "\n")
            gzip.open(path + ".gz", "w").write(r + "\n")
            # Inform Livestatus about the latest inventory update
            file(inventory_output_dir + "/.last", "w")
        else:
            console.verbose("..unchanged")

    else:
        if os.path.exists(path): # Remove empty inventory files. Important for host inventory icon
            os.remove(path)
        if os.path.exists(path + ".gz"):
            os.remove(path + ".gz")

    return old_time


def run_inv_export_hooks(hostname, tree):
    for hookname, ruleset in config.inv_exports.items():
        entries = host_extra_conf(hostname, ruleset)
        if entries:
            console.verbose(", running %s%s%s%s..." % (tty.blue, tty.bold, hookname, tty.normal))
            params = entries[0]
            try:
                inv_export[hookname]["export_function"](hostname, params, tree)
            except Exception, e:
                if cmk.debug.enabled():
                    raise
                raise MKGeneralException("Failed to execute export hook %s: %s" % (
                    hookname, e))


