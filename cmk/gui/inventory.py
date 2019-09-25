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

import ast
import json
import os
import shutil
import time
import xml.dom.minidom

import dicttoxml
from pathlib2 import Path

import livestatus

import cmk.utils.paths
from cmk.utils.structured_data import StructuredDataTree, Container, Numeration, Attributes

import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html, current_app
from cmk.gui.exceptions import MKException, MKGeneralException, MKAuthException, MKUserError, RequestTimeout


def get_inventory_data(inventory_tree, tree_path):
    invdata = None
    parsed_path, attribute_keys = parse_tree_path(tree_path)
    if attribute_keys == []:
        numeration = inventory_tree.get_sub_numeration(parsed_path)
        if numeration is not None:
            invdata = numeration.get_child_data()
    elif attribute_keys:
        attributes = inventory_tree.get_sub_attributes(parsed_path)
        if attributes is not None:
            # In paint_host_inventory_tree we parse invpath and get
            # a path and attribute_keys which may be either None, [], or ["KEY"].
            invdata = attributes.get_child_data().get(attribute_keys[-1])
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
        attribute_keys = []
    elif tree_path.endswith("."):
        path = tree_path[:-1].strip(".").split(".")
        attribute_keys = None
    else:
        path = tree_path.strip(".").split(".")
        attribute_keys = [path.pop(-1)]

    parsed_path = []
    for part in path:
        if ":" in part:
            # Nested numerations, see also lib/structured_data.py
            parts = part.split(":")
        else:
            parts = [part]

        for part_ in parts:
            if not part_:
                continue
            try:
                part_ = int(part_)
            except ValueError:
                pass
            finally:
                parsed_path.append(part_)
    return parsed_path, attribute_keys


def sort_children(children):
    if not children:
        return []
    ordering = {
        type(Attributes()): 1,
        type(Numeration()): 2,
        type(Container()): 3,
    }
    return sorted(children, key=lambda x: ordering[type(x)])


def load_filtered_inventory_tree(hostname):
    """Loads the host inventory tree from the current file and returns the filtered tree"""
    return _filter_tree(_load_inventory_tree(hostname))


def load_filtered_and_merged_tree(row):
    """Load inventory tree from file, status data tree from row,
    merge these trees and returns the filtered tree"""
    inventory_tree = _load_inventory_tree(row.get("host_name"))
    status_data_tree = _create_tree_from_raw_tree(row.get("host_structured_status"))

    merged_tree = _merge_inventory_and_status_data_tree(inventory_tree, status_data_tree)
    return _filter_tree(merged_tree)


def get_status_data_via_livestatus(site, hostname):
    query = "GET hosts\nColumns: host_structured_status\nFilter: host_name = %s\n" % livestatus.lqencode(
        hostname)
    try:
        sites.live().set_only_sites([site] if site else None)
        result = sites.live().query(query)
    finally:
        sites.live().set_only_sites()

    row = {"host_name": hostname}
    if result and result[0]:
        row["host_structured_status"] = result[0][0]
    return row


def load_delta_tree(hostname, timestamp):
    """Load inventory history and compute delta tree of a specific timestamp"""
    # Timestamp is timestamp of the younger of both trees. For the oldest
    # tree we will just return the complete tree - without any delta
    # computation.
    delta_history = get_history_deltas(hostname, search_timestamp=str(timestamp))
    if not delta_history:
        return
    return delta_history[0][1][3]


def get_history_deltas(hostname, search_timestamp=None):
    if '/' in hostname:
        return None  # just for security reasons

    inventory_path = "%s/inventory/%s" % (cmk.utils.paths.var_dir, hostname)
    if not os.path.exists(inventory_path):
        return []

    latest_timestamp = str(int(os.stat(inventory_path).st_mtime))
    inventory_archive_dir = "%s/inventory_archive/%s" % (cmk.utils.paths.var_dir, hostname)
    try:
        archived_timestamps = sorted(os.listdir(inventory_archive_dir))
    except OSError:
        return []

    all_timestamps = archived_timestamps + [latest_timestamp]
    previous_timestamp = None

    if not search_timestamp:
        required_timestamps = all_timestamps
    else:
        new_timestamp_idx = all_timestamps.index(search_timestamp)
        if new_timestamp_idx == 0:
            required_timestamps = [search_timestamp]
        else:
            previous_timestamp = all_timestamps[new_timestamp_idx - 1]
            required_timestamps = [search_timestamp]

    tree_lookup = {}

    def get_tree(timestamp):
        if timestamp is None:
            return StructuredDataTree()

        if timestamp in tree_lookup:
            return tree_lookup[timestamp]

        if timestamp == latest_timestamp:
            inventory_tree = load_filtered_inventory_tree(hostname)
            if inventory_tree is None:
                return
            tree_lookup[timestamp] = inventory_tree
        else:
            inventory_archive_path = "%s/%s" % (inventory_archive_dir, timestamp)
            tree_lookup[timestamp] = _filter_tree(
                StructuredDataTree().load_from(inventory_archive_path))
        return tree_lookup[timestamp]

    delta_history = []
    for _idx, timestamp in enumerate(required_timestamps):
        cached_delta_path = os.path.join(cmk.utils.paths.var_dir, "inventory_delta_cache", hostname,
                                         "%s_%s" % (previous_timestamp, timestamp))

        cached_data = None
        try:
            cached_data = cmk.utils.store.load_data_from_file(cached_delta_path)
        except MKGeneralException:
            pass

        if cached_data:
            new, changed, removed, delta_tree_data = cached_data
            delta_tree = StructuredDataTree()
            delta_tree.create_tree_from_raw_tree(delta_tree_data)
            delta_history.append((timestamp, (new, changed, removed, delta_tree)))
            previous_timestamp = timestamp
            continue

        try:
            previous_tree = get_tree(previous_timestamp)
            current_tree = get_tree(timestamp)
            delta_data = current_tree.compare_with(previous_tree)
            new, changed, removed, delta_tree = delta_data
            if new or changed or removed:
                cmk.utils.store.save_file(cached_delta_path,
                                          repr((new, changed, removed, delta_tree.get_raw_tree())))
                delta_history.append((timestamp, delta_data))
        except RequestTimeout:
            raise
        except Exception:
            return []  # No inventory for this host

        previous_timestamp = timestamp

    return delta_history


def parent_path(invpath):
    # Gets the parent path by dropping the last component
    if invpath == ".":
        return None  # No parent

    if invpath[-1] in ".:":  # drop trailing type specifyer
        invpath = invpath[:-1]

    last_sep = max(invpath.rfind(":"), invpath.rfind("."))
    return invpath[:last_sep + 1]


#.
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _load_inventory_tree(hostname):
    # Load data of a host, cache it in the current HTTP request
    if not hostname:
        return

    inventory_tree_cache = current_app.g.setdefault("inventory", {})
    if hostname in inventory_tree_cache:
        inventory_tree = inventory_tree_cache[hostname]
    else:
        if '/' in hostname:
            # just for security reasons
            return
        cache_path = "%s/inventory/%s" % (cmk.utils.paths.var_dir, hostname)
        inventory_tree = StructuredDataTree().load_from(cache_path)
        inventory_tree_cache[hostname] = inventory_tree
    return inventory_tree


def _create_tree_from_raw_tree(raw_tree):
    if raw_tree:
        return StructuredDataTree().create_tree_from_raw_tree(ast.literal_eval(raw_tree))
    return


def _merge_inventory_and_status_data_tree(inventory_tree, status_data_tree):
    if inventory_tree is None and status_data_tree is None:
        return

    if inventory_tree is None:
        inventory_tree = StructuredDataTree()

    if status_data_tree is not None:
        inventory_tree.merge_with(status_data_tree)
    return inventory_tree


def _filter_tree(struct_tree):
    if struct_tree is None:
        return
    return struct_tree.get_filtered_tree(_get_permitted_inventory_paths())


def _get_permitted_inventory_paths():
    """
    Returns either a list of permitted paths or
    None in case the user is allowed to see the whole tree.
    """
    cache_varname = "permitted_inventory_paths"
    if cache_varname in current_app.g:
        return current_app.g[cache_varname]

    user_groups = userdb.contactgroups_of_user(config.user.id)

    if not user_groups:
        current_app.g[cache_varname] = None
        return None

    forbid_whole_tree = False
    permitted_paths = []
    for user_group in user_groups:
        inventory_paths = config.multisite_contactgroups.get(user_group, {}).get('inventory_paths')
        if inventory_paths is None:
            # Old configuration: no paths configured means 'allow_all'
            current_app.g[cache_varname] = None
            return None

        if inventory_paths == "allow_all":
            current_app.g[cache_varname] = None
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
        current_app.g[cache_varname] = []
        return []

    current_app.g[cache_varname] = permitted_paths
    return permitted_paths


#.
#   .--Inventory API-------------------------------------------------------.
#   |   ___                      _                        _    ____ ___    |
#   |  |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _     / \  |  _ \_ _|   |
#   |   | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |   / _ \ | |_) | |    |
#   |   | || | | \ V /  __/ | | | || (_) | |  | |_| |  / ___ \|  __/| |    |
#   |  |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, | /_/   \_\_|  |___|   |
#   |                                          |___/                       |
#   '----------------------------------------------------------------------'


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
                result[host_name] = inventory_of_host(host_name, request)

        else:
            host_name = request.get("host")
            if host_name is None:
                raise MKUserError("host", _("You need to provide a \"host\"."))

            result = inventory_of_host(host_name, request)

            if not result and not has_inventory(host_name):
                raise MKGeneralException(_("Found no inventory data for this host."))

        response = {"result_code": 0, "result": result}

    except MKException as e:
        response = {"result_code": 1, "result": "%s" % e}

    except Exception as e:
        if config.debug:
            raise
        response = {"result_code": 1, "result": "%s" % e}

    if html.output_format == "json":
        _write_json(response)
    elif html.output_format == "xml":
        _write_xml(response)
    else:
        _write_python(response)


def has_inventory(hostname):
    if not hostname:
        return False
    inventory_path = "%s/inventory/%s" % (cmk.utils.paths.var_dir, hostname)
    return os.path.exists(inventory_path)


def inventory_of_host(host_name, request):
    site = request.get("site")
    if not _may_see(host_name, site):
        raise MKAuthException(_("Sorry, you are not allowed to access the host %s.") % host_name)

    row = get_status_data_via_livestatus(site, host_name)
    merged_tree = load_filtered_and_merged_tree(row)
    if not merged_tree:
        return {}

    if "paths" in request:
        parsed_paths = []
        for path in request["paths"]:
            parsed_paths.append(parse_tree_path(path))
        merged_tree = merged_tree.get_filtered_tree(parsed_paths)

    return merged_tree.get_raw_tree()


def _may_see(host_name, site):
    if config.user.may("general.see_all"):
        return True

    query = "GET hosts\nStats: state >= 0\nFilter: name = %s\n" % livestatus.lqencode(host_name)
    if site:
        sites.live().set_only_sites([site])
    try:
        result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")
    finally:
        if site:
            sites.live().set_only_sites()

    if not result:
        return False
    return result[0] > 0


def _write_xml(response):
    unformated_xml = dicttoxml.dicttoxml(response)
    dom = xml.dom.minidom.parseString(unformated_xml)
    html.write(dom.toprettyxml())


def _write_json(response):
    html.write(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))


def _write_python(response):
    html.write(repr(response))


class InventoryHousekeeping(object):
    def __init__(self):
        super(InventoryHousekeeping, self).__init__()
        self._inventory_path = Path(cmk.utils.paths.var_dir) / "inventory"
        self._inventory_archive_path = Path(cmk.utils.paths.var_dir) / "inventory_archive"
        self._inventory_delta_cache_path = Path(cmk.utils.paths.var_dir) / "inventory_delta_cache"

    def run(self):
        if not self._inventory_delta_cache_path.exists() or not self._inventory_archive_path.exists(  # pylint: disable=no-member
        ):
            return

        last_cleanup = self._inventory_delta_cache_path / "last_cleanup"
        # TODO: remove with pylint 2
        if last_cleanup.exists() and time.time() - last_cleanup.stat().st_mtime < 3600 * 12:  # pylint: disable=no-member
            return

        # TODO: remove with pylint 2
        inventory_archive_hosts = set(
            [x.name for x in self._inventory_archive_path.iterdir() if x.is_dir()])  # pylint: disable=no-member
        inventory_delta_cache_hosts = set(
            [x.name for x in self._inventory_delta_cache_path.iterdir() if x.is_dir()])  # pylint: disable=no-member

        folders_to_delete = inventory_delta_cache_hosts - inventory_archive_hosts
        for foldername in folders_to_delete:
            shutil.rmtree(str(self._inventory_delta_cache_path / foldername))

        inventory_delta_cache_hosts -= folders_to_delete
        for hostname in inventory_delta_cache_hosts:
            available_timestamps = self._get_timestamps_for_host(hostname)
            for filename in [
                    x.name
                    for x in (self._inventory_delta_cache_path / hostname).iterdir()
                    if not x.is_dir()
            ]:
                delete = False
                try:
                    first, second = filename.split("_")
                    if first not in available_timestamps or second not in available_timestamps:
                        delete = True
                except ValueError:
                    delete = True
                if delete:
                    (self._inventory_delta_cache_path / hostname / filename).unlink()

        # TODO: remove with pylint 2
        last_cleanup.touch()  # pylint: disable=no-member

    def _get_timestamps_for_host(self, hostname):
        timestamps = set(["None"])  # 'None' refers to the histories start
        try:
            timestamps.add("%d" % (self._inventory_path / hostname).stat().st_mtime)
        except OSError:
            pass

        for filename in [
                x for x in (self._inventory_archive_path / hostname).iterdir() if not x.is_dir()
        ]:
            timestamps.add(filename.name)
        return timestamps
