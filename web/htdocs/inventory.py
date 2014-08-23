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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import defaults, re, os

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

def load_host(hostname):
    if '/' in hostname:
        return None # just for security reasons
    path = defaults.var_dir + "/inventory/" + hostname
    try:
        return eval(file(path).read())
    except:
        return {}

def has_inventory(hostname):
    path = defaults.var_dir + "/inventory/" + hostname
    return os.path.exists(path)

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

