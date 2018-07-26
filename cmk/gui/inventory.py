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
import json
import ast
import livestatus

import cmk.paths
import cmk.store as store
import cmk.profile
from cmk.structured_data import StructuredDataTree, Container, Numeration, Attributes

import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKException, MKGeneralException, MKAuthException, MKUserError


def get_inventory_data(inventory_tree, tree_path):
    invdata = None
    parsed_path, attributes_key = parse_tree_path(tree_path)
    if attributes_key == []:
        numeration = inventory_tree.get_sub_numeration(parsed_path)
        if numeration is not None:
            invdata = numeration.get_child_data()
    elif attributes_key:
        attributes =  inventory_tree.get_sub_attributes(parsed_path)
        if attributes is not None:
            invdata = attributes.get_child_data().get(attributes_key)
    return invdata


def parse_tree_path(tree_path):
    # tree_path may look like:
    # .                          (ROOT) => path = []                            key = None
    # .hardware.                 (dict) => path = ["hardware"],                 key = None
    # .hardware.cpu.model        (leaf) => path = ["hardware", "cpu"],          key = "model"
    # .hardware.cpu.             (dict) => path = ["hardware", "cpu"],          key = None
    # .software.packages:17.name (leaf) => path = ["software", "packages", 17], key = "name"
    # .software.packages:        (list) => path = ["software", "packages"],     key = []
    if tree_path.endswith(":"):
        path = tree_path[:-1].strip(".").split(".")
        attributes_key = []
    elif tree_path.endswith("."):
        path = tree_path[:-1].strip(".").split(".")
        attributes_key = None
    else:
        path = tree_path.strip(".").split(".")
        attributes_key = path.pop(-1)

    parsed_path = []
    for part in path:
        if ":" in part:
            # Nested numerations, see also lib/structured_data.py
            parts = part.split(":")
        else:
            parts = [part]
        for part in parts:
            if not part:
                continue
            try:
                part = int(part)
            except ValueError:
                pass
            finally:
                parsed_path.append(part)
    return parsed_path, attributes_key


def sort_children(children):
    if not children:
        return []
    ordering = {
        type(Attributes()): 1,
        type(Numeration()): 2,
        type(Container()): 3,
    }
    return sorted(children, key=lambda x: ordering[type(x)])


def load_tree(hostname, merge_trees=True):
    # Load data of a host, cache it in the current HTTP request
    if not hostname:
        return None

    inventory_tree_cache = html.get_cached("inventory")
    if not inventory_tree_cache:
        inventory_tree_cache = {}
        html.set_cache("inventory", inventory_tree_cache)

    if hostname in inventory_tree_cache:
        inventory_tree = inventory_tree_cache[hostname]
    else:
        if '/' in hostname:
            return None # just for security reasons
        cache_path = "%s/inventory/%s" % (cmk.paths.var_dir, hostname)
        inventory_tree = StructuredDataTree().load_from(cache_path)
        inventory_tree_cache[hostname] = inventory_tree

    if merge_trees:
        inventory_tree = _merge_with_status_data_tree(hostname, inventory_tree)

    inventory_tree = inventory_tree.get_filtered_tree(get_permitted_inventory_paths())
    return inventory_tree


def _merge_with_status_data_tree(hostname, inventory_tree):
    filepath = "%s/status_data/%s" % (cmk.paths.tmp_dir, hostname)
    if os.path.exists(filepath):
        status_data_tree = StructuredDataTree().load_from(filepath)
        inventory_tree.merge_with(status_data_tree)
        return inventory_tree
    else:
        return inventory_tree


def load_delta_tree(hostname, timestamp):
    # Timestamp is timestamp of the younger of both trees. For the oldest
    # tree we will just return the complete tree - without any delta
    # computation.
    for old_timestamp, old_tree, new_tree in get_history(hostname):
        if old_timestamp == timestamp:
            _, __, ___, delta = new_tree.compare_with(old_tree)
            return delta
    return None


def get_history(hostname):
    # List of triple: timestamp (old), old tree, new tree
    if '/' in hostname:
        return None # just for security reasons

    history = []
    try:
        inventory_path = "%s/inventory/%s" % (cmk.paths.var_dir, hostname)
        timestamp = int(os.stat(inventory_path).st_mtime)
        inventory_tree = load_tree(hostname, merge_trees=False)
        history.append((timestamp, inventory_tree))
    except:
        # TODO: We should really change this error handling. There is currently
        # no chance to react on issues that occur during processing of
        # inventory data.
        return [] # No inventory for this host

    inventory_archive_dir = "%s/inventory_archive/%s" % (cmk.paths.var_dir, hostname)
    if os.path.exists(inventory_archive_dir):
        for timestamp_str in os.listdir(inventory_archive_dir):
            try:
                timestamp = int(timestamp_str)
                inventory_archive_path = "%s/%d" % (inventory_archive_dir, timestamp)
                inventory_tree = StructuredDataTree().load_from(inventory_archive_path)
            except:
                # TODO: We should really change this error handling. There is currently
                # no chance to react on issues that occur during processing of
                # inventory data.
                pass
            else:
                history.append((timestamp, inventory_tree))

    comparable_trees, previous_tree = [], StructuredDataTree()
    for this_timestamp, inventory_tree in sorted(history, key=lambda x: x[0]):
        comparable_trees.append((this_timestamp, inventory_tree, previous_tree))
        previous_tree = inventory_tree

    return reversed(comparable_trees)


def parent_path(invpath):
    # Gets the parent path by dropping the last component
    if invpath == ".":
        return None # No parent

    if invpath[-1] in ".:": # drop trailing type specifyer
        invpath = invpath[:-1]

    last_sep = max(invpath.rfind(":"), invpath.rfind("."))
    return invpath[:last_sep+1]


def get_permitted_inventory_paths():
    """
Returns either a list of permitted paths or
None in case the user is allowed to see the whole tree.
"""
    contact_groups = userdb.load_group_information().get("contact", {})
    user_groups = userdb.contactgroups_of_user(config.user.id)
    if not user_groups:
        return None

    forbid_whole_tree = False
    permitted_paths = []
    for user_group in user_groups:
        inventory_paths = contact_groups.get(user_group, {}).get('inventory_paths')
        if inventory_paths is None:
            # Old configuration: no paths configured means 'allow_all'
            return None

        if inventory_paths == "allow_all":
            return None

        elif inventory_paths == "forbid_all":
            forbid_whole_tree = True
            continue

        for entry in inventory_paths[1]:
            parsed = []
            for part in entry["path"].split("."):
                try:
                    parsed.append(int(part))
                except ValueError:
                    parsed.append(part)
            permitted_paths.append((parsed, entry.get("attributes")))

    if forbid_whole_tree and not permitted_paths:
        return []
    return permitted_paths


@cmk.gui.pages.register("host_inv_api")
def page_host_inv_api():
    # The response is always a top level dict with two elements:
    # a) result_code - This is 0 for expected processing and 1 for an error
    # b) result      - In case of an error this is the error message, a UTF-8 encoded string.
    #                  In case of success this is a dictionary containing the host inventory.
    try:
        request = html.get_request()
        # The user can either specify a single host or provide a list of host names. In case
        # multiple hosts are handled, there is a top level dict added with "host > invdict" pairs
        hosts = request.get("hosts")
        if hosts:
            result = {}
            for host_name in hosts:
                result[host_name] = _inventory_of_host(host_name, request)

        else:
            host_name = request.get("host")
            if host_name == None:
                raise MKUserError("host", _("You need to provide a \"host\"."))

            result = _inventory_of_host(host_name, request)

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
        _write_json(response)
    elif html.output_format == "xml":
        _write_xml(response)
    else:
        _write_python(response)


def has_inventory(hostname):
    if not hostname:
        return False
    inventory_path = "%s/inventory/%s" % (cmk.paths.var_dir, hostname)
    return os.path.exists(inventory_path)


def _inventory_of_host(host_name, request):
    if not _may_see(host_name, site=request.get("site")):
        raise MKAuthException(_("Sorry, you are not allowed to access the host %s.") % host_name)

    inventory_tree = load_tree(host_name)
    if not inventory_tree:
        return {}
    if "paths" in request:
        parsed_paths = []
        for path in request["paths"]:
            parsed_path, _key = parse_tree_path(path)
            parsed_paths.append(parsed_path)
        inventory_tree = inventory_tree.get_filtered_tree(parsed_paths)
    return inventory_tree.get_raw_tree()


def _may_see(host_name, site=None):
    if config.user.may("general.see_all"):
        return True

    query = "GET hosts\nStats: state >= 0\nFilter: name = %s\n" % livestatus.lqencode(host_name)
    if site:
        sites.live().set_only_sites([site])

    result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")
    if site:
        sites.live().set_only_sites()

    if not result:
        return False
    else:
        return result[0] > 0


def _write_xml(response):
    try:
        import dicttoxml
    except ImportError:
        raise MKGeneralException(_("You need to have the \"dicttoxml\" python module installed "
                                   "to be able to use the XML format."))

    unformated_xml = dicttoxml.dicttoxml(response)

    from xml.dom.minidom import parseString
    dom = parseString(unformated_xml)

    html.write(dom.toprettyxml())


def _write_json(response):
    html.write(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))


def _write_python(response):
    html.write(repr(response))
