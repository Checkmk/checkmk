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
import os
import pprint
import re

import cmk
import cmk.tty as tty
import cmk.paths
from cmk.exceptions import MKGeneralException

import cmk_base.console as console
import cmk_base.config as config
import cmk_base.rulesets as rulesets

inventory_output_dir  = cmk.paths.var_dir + "/inventory"
inventory_archive_dir = cmk.paths.var_dir + "/inventory_archive"
# TODO: This is not configurable. Drop the flag?
inventory_pprint_output = True

g_inv_tree = {}

def initialize_inventory_tree():
    global g_inv_tree
    g_inv_tree = {}


def get_inventory_tree():
    return g_inv_tree


# This is just a small wrapper for the inv_tree() function which makes
# it clear that the requested tree node is treated as a list.
def inv_tree_list(path):
    # The [] is needed to tell pylint that a list is returned
    return inv_tree(path, [])


# Function for accessing the inventory tree of the current host
# Example: path = "software.packages:17."
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
def cleanup_inventory_tree(tree=None):
    if tree == None:
        tree = g_inv_tree

    if type(tree) == dict:
        for key, value in tree.items():
            if cleanup_inventory_tree(value):
                del tree[key]
        return not tree

    elif type(tree) == list:
        to_delete = []
        for nr, entry in enumerate(tree):
            if cleanup_inventory_tree(entry):
                to_delete.append(nr)
        for nr in to_delete[::-1]:
            del tree[nr]
        return not tree

    else:
        return False # cannot clean non-container nodes


def count_nodes(tree=None):
    if tree == None:
        tree = g_inv_tree

    if type(tree) == dict:
        return len(tree) + sum([count_nodes(v) for v in tree.values()])
    elif type(tree) == list:
        return len(tree) + sum([count_nodes(v) for v in tree])
    elif tree == None:
        return 0
    else:
        return 1


# Returns the time stamp of the previous inventory with different
# outcome or None.
def save_inventory_tree(hostname):
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


def run_inventory_export_hooks(hostname):
    import cmk_base.inventory_plugins
    for hookname, ruleset in config.inv_exports.items():
        entries = rulesets.host_extra_conf(hostname, ruleset)
        if entries:
            console.verbose(", running %s%s%s%s..." % (tty.blue, tty.bold, hookname, tty.normal))
            params = entries[0]
            try:
                cmk_base.inventory_plugins.inv_export[hookname]["export_function"](hostname, params, g_inv_tree)
            except Exception, e:
                if cmk.debug.enabled():
                    raise
                raise MKGeneralException("Failed to execute export hook %s: %s" % (
                    hookname, e))
