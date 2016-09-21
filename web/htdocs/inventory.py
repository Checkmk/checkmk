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

import re
import os

try:
    import simplejson as json
except ImportError:
    import json


import config
import sites
import cmk.paths
from lib import MKException, MKGeneralException, MKAuthException, MKUserError, lqencode

# Load data of a host, cache it in the current HTTP request
def host(hostname):
    invcache = html.get_cached("inventory")
    if not invcache:
        invcache = {}
        html.set_cache("inventory", invcache)

    if hostname in invcache:
        return invcache[hostname]
    else:
        invdata = load_host(hostname)
        invcache[hostname] = invdata
        return invdata

def has_inventory(hostname):
    path = cmk.paths.var_dir + "/inventory/" + hostname
    return os.path.exists(path)

def load_host(hostname):
    if '/' in hostname:
        return None # just for security reasons
    path = cmk.paths.var_dir + "/inventory/" + hostname
    try:
        return eval(file(path).read())
    except:
        return {}

# Return a list of timestamps of all inventory snapshost
# of a host.
def get_host_history(hostname):
    if '/' in hostname:
        return None # just for security reasons

    path = cmk.paths.var_dir + "/inventory/" + hostname
    try:
        history = [ int(os.stat(path).st_mtime) ]
    except:
        return [] # No inventory for this host

    arcdir = cmk.paths.var_dir + "/inventory_archive/" + hostname
    if os.path.exists(arcdir):
        for ts in os.listdir(arcdir):
            try:
                history.append(int(ts))
            except:
                pass
    history.sort()
    history.reverse()
    return history

# Timestamp is timestamp of the younger of both trees. For the oldest
# tree we will just return the complete tree - without any delta
# computation.
def load_delta_tree(hostname, timestamp):
    history = get_host_history(hostname)
    prev = None
    for ts in history[::-1]:
        if ts == timestamp:
            tree = load_historic_host(hostname, ts)
            if prev:
                old_tree = load_historic_host(hostname, prev)
            else:
                old_tree = None
            delta_tree = compare_trees(old_tree, tree)[3]
            return delta_tree
        prev = ts


def load_historic_host(hostname, timestamp):
    if '/' in hostname:
        return None # just for security reasons

    path = cmk.paths.var_dir + "/inventory/" + hostname

    # Try current tree
    if int(os.stat(path).st_mtime) == timestamp:
        return host(hostname)

    # TODO: Handle valid cases (missing file) correctly, but don't suppress other exceptions!
    try:
        path = cmk.paths.var_dir + "/inventory_archive/" + hostname + "/%d" % timestamp
        return eval(file(path).read())
    except:
        return {}



# Example for the paths:
# .hardware.cpu.model        (leaf)
# .hardware.cpu.             (dict)
# .software.packages:17.name (leaf)
# .software.packages:        (list)
# Non-existings paths return None for leave nodes,
# {} for dict nodes and [] for list nodes
def get(tree, path):
    if path[0] != '.':
        raise MKGeneralException(_("Invalid inventory path. Must start with dot."))
    path = path[1:]

    node = tree

    # The root node of the tree MUST be dictionary
    # This info is taken from the host_inventory column in a livestatus table
    # Older versions, which do not know this column, report None as fallback value
    # This workaround prevents the inevitable crash
    if node == None:
        node = {}

    current_what = "."
    while path not in ('.', ':', ''):
        parts = re.split("[:.]", path)
        name = parts[0]
        path = path[len(name):]
        if path:
            what = path[0]
            path = path[1:]
        else:
            what = None # leaf node

        if current_what == '.': # node is a dict
            if name not in node:
                if what == '.':
                    node = {}
                elif what == ':':
                    node = []
                else:
                    node = None
            else:
                node = node[name]

        elif current_what == ':': # node is a list
            index = int(name)
            if index >= len(node) or index < 0:
                if what == '.':
                    node = {}
                elif what == ':':
                    node = []
                else:
                    node = None
            else:
                node = node[index]

        current_what = what
        if what == None:
            return node # return leaf node

    return node

# Gets the parent path by dropping the last component
def parent_path(invpath):
    if invpath == ".":
        return None # No parent

    if invpath[-1] in ".:": # drop trailing type specifyer
        invpath = invpath[:-1]

    last_sep = max(invpath.rfind(":"), invpath.rfind("."))
    return invpath[:last_sep+1]

# Compare two inventory trees. Returns a tuple of
# 2. The number of removed nodes
# 1. The number of new nodes
# 3. The number of changed nodes
# 4. A delta tree. The delta tree has the same architecture
#    as the sum of both trees, but:
#    - leaf nodes are replaced with pairs (old_value, new_value)
#    - list nodes are replaced with triples (removed_items, new_items, changed_items)
# keep_identical: if False then remove nodes where old == new
def compare_trees(old, new, keep_identical=False):
    if type(old) == list or type(new) == list:
        return compare_list_nodes(old or [], new or [])
    elif type(old) == dict or type(new) == dict:
        return compare_dict_nodes(old or {}, new or {}, keep_identical=keep_identical)
    else:
        return compare_leaf_nodes(old, new)

def compare_list_nodes(old, new):
    # Try two algorithms and choose the one with the least
    # changes. First one only works if the lists have the
    # same length.
    r, n, c, dt = compare_list_nodes_variable(old, new)
    if len(old) == len(new):
        r2, n2, c2, dt2 = compare_list_nodes_fixed(old, new)
        if r2 + n2 + c2 <= r + n + c:
            r, n, c, dt = r2, n2, c2, dt2

    return r, n, c, dt


def compare_list_nodes_variable(old, new):
    removed_items = []
    new_items = []
    for entry in old:
        if entry not in new:
            removed_items.append(entry)
    for entry in new:
        if entry not in old:
            new_items.append(entry)
    return len(removed_items), len(new_items), 0, \
           (removed_items, new_items)


def compare_list_nodes_fixed(old, new):
    num_removed = 0
    num_new = 0
    num_changed = 0
    delta_tree = []

    for old_item, new_item in zip(old, new):
        r, n, c, dt = compare_trees(old_item, new_item, keep_identical=True)
        num_removed += r
        num_new += n
        num_changed += c
        if dt not in ([], {}) and old_item != new_item:
            delta_tree.append(dt)

    return num_removed, num_new, num_changed, delta_tree


def compare_dict_nodes(old, new, keep_identical=False):
    num_removed = 0
    num_new = 0
    num_changed = 0
    delta_tree = {}

    # Find vanished paths
    for key, value in old.items():
        if key not in new:
            r,n,u,dt = compare_trees(value, None)
            delta_tree[key] = dt
            num_removed += r
            num_new += n

    # Find new and prevailing paths
    for key, value in new.items():
        if key not in old:
            r,n,u,dt = compare_trees(None, value)
            num_new += n
            if dt not in ([], {}):
                delta_tree[key] = dt
        else:
            if value != old[key] or keep_identical: # omit unchanged paths
                r, n, c, dt = compare_trees(old[key], value)
                num_removed += r
                num_new += n
                num_changed += c
                if dt not in ([], {}):
                    delta_tree[key] = dt

    return num_removed, num_new, num_changed, delta_tree

def compare_leaf_nodes(old, new):
    if old == None and new != None:
        return 0, 1, 0, (old, new)
    elif old != None and new == None:
        return 1, 0, 1, (old, new)
    if old == new:
        return 0, 0, 0, (old, new)
    else:
        return 0, 0, 1, (old, new)

def count_items(tree):
    if type(tree) == dict:
        return sum(map(count_items, tree.values()))
    elif type(tree) == list:
        return sum(map(count_items, tree))
    else:
        return 1


# The response is always a top level dict with two elements:
# a) result_code - This is 0 for expected processing and 1 for an error
# b) result      - In case of an error this is the error message, a UTF-8 encoded string.
#                  In case of success this is a dictionary containing the host inventory.
def page_host_inv_api():
    try:
        request = html.get_request()

        # The user can either specify a single host or provide a list of host names. In case
        # multiple hosts are handled, there is a top level dict added with "host > invdict" pairs
        hosts = request.get("hosts")
        if hosts:
            result = {}
            for host_name in hosts:
                result[host_name] = inventory_of_host(host_name, request)

        else:
            host_name = request.get("host")
            if host_name == None:
                raise MKUserError("host", _("You need to provide a \"host\"."))

            result = inventory_of_host(host_name, request)

            if not result and not has_inventory(host_name):
                raise MKGeneralException(_("Found no inventory data for this host."))

        response = { "result_code": 0, "result": result }

    except MKException, e:
        response = { "result_code": 1, "result": "%s" % e }

    except Exception, e:
        if config.debug:
            raise
        response = { "result_code": 1, "result": "%s" % e }

    if html.output_format == "json":
        write_json(response)
    elif html.output_format == "xml":
        write_xml(response)
    else:
        write_python(response)


def inventory_of_host(host_name, request):
    if not may_see(host_name, site=request.get("site")):
        raise MKAuthException(_("Sorry, you are not allowed to access the host %s.") % host_name)

    host_inv = host(host_name)

    if "paths" in request:
        host_inv = filter_tree_by_paths(host_inv, request["paths"])

    return host_inv


def filter_tree_by_paths(tree, paths):
    filtered = {}

    for path in paths:
        node = get(tree, path)

        parts = path.split(".")
        this_tree = filtered
        while True:
            key = parts.pop(0)
            if parts:
                this_tree = this_tree.setdefault(key, {})
            else:
                this_tree[key] = node
                break

    return filtered


def may_see(host_name, site=None):
    if config.may("general.see_all"):
        return True


    query = "GET hosts\nStats: state >= 0\nFilter: name = %s\n" % lqencode(host_name)

    if site:
        sites.live().set_only_sites([site])

    result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")

    if site:
        sites.live().set_only_sites()

    if not result:
        return False
    else:
        return result[0] > 0


def write_xml(response):
    try:
        import dicttoxml
    except ImportError:
        raise MKGeneralException(_("You need to have the \"dicttoxml\" python module installed to "
                                   "be able to use the XML format."))

    unformated_xml = dicttoxml.dicttoxml(response)

    from xml.dom.minidom import parseString
    dom = parseString(unformated_xml)

    html.write(dom.toprettyxml())


def write_json(response):
    html.write(json.dumps(response,
                          sort_keys=True, indent=4, separators=(',', ': ')))


def write_python(response):
    html.write(repr(response))
