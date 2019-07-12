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
"""Caring about persistance of the discovered services (aka autochecks)

This is a sub module of cmk_base.discovery.
"""

from typing import Tuple, Optional, List  # pylint: disable=unused-import
import os
import sys
import ast
from pathlib2 import Path
import six

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.console
from cmk_base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName, CheckParameters, DiscoveredService, Item,
)


# TODO: use store.load_data_from_file()
# TODO: Common code with parse_autochecks_file? Cleanup.
def read_autochecks_of(hostname):
    # type: (str) -> List[Tuple[CheckPluginName, Item, CheckParameters]]
    """Read automatically discovered checks of one host.

    Returns a table with three columns:
    1. check_plugin_name
    2. item
    3. parameters (evaluated!)
    """
    basedir = cmk.utils.paths.autochecks_dir
    filepath = basedir + '/' + hostname + '.mk'

    if not os.path.exists(filepath):
        return []

    check_config = config.get_check_variables()
    try:
        cmk_base.console.vverbose("Loading autochecks from %s\n", filepath)
        autochecks_raw = eval(
            file(filepath).read(), check_config,
            check_config)  # type: List[Tuple[CheckPluginName, Item, CheckParameters]]
    except SyntaxError as e:
        cmk_base.console.verbose("Syntax error in file %s: %s\n", filepath, e, stream=sys.stderr)
        if cmk.utils.debug.enabled():
            raise
        return []
    except Exception as e:
        cmk_base.console.verbose("Error in file %s:\n%s\n", filepath, e, stream=sys.stderr)
        if cmk.utils.debug.enabled():
            raise
        return []

    # Exchange inventorized check parameters with those configured by
    # the user. Also merge with default levels for modern dictionary based checks.
    autochecks = []
    for entry in autochecks_raw:
        if len(entry) == 4:  # old format where hostname is at the first place
            entry = entry[1:]  # type: ignore
        check_plugin_name, item, parameters = entry

        # With Check_MK 1.2.7i3 items are now defined to be unicode strings. Convert
        # items from existing autocheck files for compatibility. TODO remove this one day
        if isinstance(item, str):
            item = config.decode_incoming_string(item)

        if not isinstance(check_plugin_name, six.string_types):
            raise MKGeneralException("Invalid entry '%r' in check table of host '%s': "
                                     "The check type must be a string." % (entry, hostname))

        autochecks.append((check_plugin_name, item,
                           config.compute_check_parameters(hostname, check_plugin_name, item,
                                                           parameters)))
    return autochecks


def parse_autochecks_file(hostname):
    # type: (str) -> List[DiscoveredService]
    """Read autochecks, but do not compute final check parameters"""
    path = "%s/%s.mk" % (cmk.utils.paths.autochecks_dir, hostname)
    if not os.path.exists(path):
        return []

    services = []  # type: List[DiscoveredService]

    try:
        tree = ast.parse(open(path).read())
    except SyntaxError:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Unable to parse autochecks file %s" % (path))

    for child in ast.iter_child_nodes(tree):
        # Mypy is wrong about this: [mypy:] "AST" has no attribute "value"
        if not isinstance(child, ast.Expr) and isinstance(child.value, ast.List):  # type: ignore
            continue  # We only care about top level list

        # Mypy is wrong about this: [mypy:] "AST" has no attribute "value"
        for entry in child.value.elts:  # type: ignore
            if not isinstance(entry, ast.Tuple):
                continue

            service = _parse_autocheck_entry(hostname, entry)
            if service:
                services.append(service)

    return services


def _parse_autocheck_entry(hostname, entry):
    # type: (str, ast.Tuple) -> Optional[DiscoveredService]
    # drop hostname, legacy format with host in first column
    parts = entry.elts[1:] if len(entry.elts) == 4 else entry.elts

    if len(parts) != 3:
        raise Exception("Invalid autocheck: Wrong length %d instead of 3" % len(parts))
    ast_check_plugin_name, ast_item, ast_paramstr = parts

    if not isinstance(ast_check_plugin_name, ast.Str):
        raise Exception("Invalid autocheck: Wrong check plugin type: %r" % ast_check_plugin_name)
    check_plugin_name = ast_check_plugin_name.s

    item = None  # type: Item
    if isinstance(ast_item, ast.Str):
        item = ast_item.s
    elif isinstance(ast_item, ast.Num):
        item = int(ast_item.n)
    elif isinstance(ast_item, ast.Name) and ast_item.id == "None":
        item = None
    else:
        raise Exception("Invalid autocheck: Wrong item type: %r" % ast_item)

    # With Check_MK 1.2.7i3 items are now defined to be unicode
    # strings. Convert items from existing autocheck files for
    # compatibility.
    if isinstance(item, str):
        item = config.decode_incoming_string(item)

    if isinstance(ast_paramstr, ast.Name):
        # Keep check variable names as they are: No evaluation of check parameters
        paramstr = ast_paramstr.id
    else:
        # Other structures, like dicts, lists and so on should also be loaded as repr() str
        # instead of an interpreted structure
        paramstr = repr(eval(compile(ast.Expression(ast_paramstr), filename="<ast>", mode="eval")))

    try:
        description = config.service_description(hostname, check_plugin_name, item)
    except Exception:
        return None  # ignore

    return DiscoveredService(check_plugin_name, item, description, paramstr)


def set_autochecks_of(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    """Merge existing autochecks with the given autochecks for a host and save it"""
    if host_config.is_cluster:
        _set_autochecks_of_cluster(host_config, new_items)
    else:
        _set_autochecks_of_real_hosts(host_config, new_items)


def _set_autochecks_of_real_hosts(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    new_autochecks = []  # type: List[DiscoveredService]

    # write new autochecks file, but take paramstrings from existing ones
    # for those checks which are kept
    for existing_service in parse_autochecks_file(host_config.hostname):
        # TODO: Need to implement a list class that realizes in / not in correctly
        if existing_service in new_items:
            new_autochecks.append(existing_service)

    for discovered_service in new_items:
        if discovered_service not in new_autochecks:
            new_autochecks.append(discovered_service)

    # write new autochecks file for that host
    save_autochecks_file(host_config.hostname, new_autochecks)


def _set_autochecks_of_cluster(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    if not host_config.nodes:
        return

    config_cache = config.get_config_cache()

    new_autochecks = []  # type: List[DiscoveredService]
    for node in host_config.nodes:
        for existing_service in parse_autochecks_file(node):
            if host_config.hostname != config_cache.host_of_clustered_service(
                    node, existing_service.description):
                new_autochecks.append(existing_service)

        for discovered_service in new_items:
            new_autochecks.append(discovered_service)

        # write new autochecks file for that host
        save_autochecks_file(node, new_autochecks)

    # Check whether or not the cluster host autocheck files are still existant.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    remove_autochecks_file(host_config.hostname)


def has_autochecks(hostname):
    # type: (str) -> bool
    return os.path.exists(cmk.utils.paths.autochecks_dir + "/" + hostname + ".mk")


def save_autochecks_file(hostname, items):
    # type: (str, List[DiscoveredService]) -> None
    if not os.path.exists(cmk.utils.paths.autochecks_dir):
        os.makedirs(cmk.utils.paths.autochecks_dir)

    filepath = Path(cmk.utils.paths.autochecks_dir) / ("%s.mk" % hostname)
    content = []
    content.append("[")
    for discovered_service in sorted(items, key=lambda s: (s.check_plugin_name, s.item)):
        content.append("  (%r, %r, %s)," % (discovered_service.check_plugin_name,
                                            discovered_service.item, discovered_service.paramstr))
    content.append("]\n")
    store.save_file(str(filepath), "\n".join(content))


def remove_autochecks_file(hostname):
    # type: (str) -> None
    filepath = cmk.utils.paths.autochecks_dir + "/" + hostname + ".mk"
    try:
        os.remove(filepath)
    except OSError:
        pass


def remove_autochecks_of(host_config):
    # type: (config.HostConfig) -> int
    """Remove all autochecks of a host while being cluster-aware

    Cluster aware means that the autocheck files of the nodes are handled. Instead
    of removing the whole file the file is loaded and only the services associated
    with the given cluster are removed."""
    removed = 0
    if host_config.nodes:
        for node_name in host_config.nodes:
            removed += _remove_autochecks_of_host(node_name)
    else:
        removed += _remove_autochecks_of_host(host_config.hostname)

    return removed


def _remove_autochecks_of_host(hostname):
    # type: (str) -> int
    removed = 0
    new_items = []  # type: List[DiscoveredService]
    config_cache = config.get_config_cache()

    old_items = parse_autochecks_file(hostname)
    for existing_service in old_items:
        if hostname != config_cache.host_of_clustered_service(hostname,
                                                              existing_service.description):
            new_items.append(existing_service)
        else:
            removed += 1
    save_autochecks_file(hostname, new_items)
    return removed
