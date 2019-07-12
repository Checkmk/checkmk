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

from typing import Optional, List  # pylint: disable=unused-import
import os
import sys
import ast

import six

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.console
from cmk_base.check_utils import DiscoveredService, Item  # pylint: disable=unused-import


# Read automatically discovered checks of one host.
# Returns a table with three columns:
# 1. check_plugin_name
# 2. item
# 3. parameters evaluated!
# TODO: use store.load_data_from_file()
# TODO: Common code with parse_autochecks_file? Cleanup.
def read_autochecks_of(hostname):
    basedir = cmk.utils.paths.autochecks_dir
    filepath = basedir + '/' + hostname + '.mk'

    if not os.path.exists(filepath):
        return []

    check_config = config.get_check_variables()
    try:
        cmk_base.console.vverbose("Loading autochecks from %s\n", filepath)
        autochecks_raw = eval(file(filepath).read(), check_config, check_config)
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
            entry = entry[1:]
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
