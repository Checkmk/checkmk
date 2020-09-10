#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Any, Dict, Set

import cmk.utils.paths
import cmk.utils.debug
from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import SectionName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.check_utils

from cmk.base.api.agent_based.register.inventory_plugins_legacy import (
    create_inventory_plugin_from_legacy,)
from cmk.base.api.agent_based.register.section_plugins_legacy import (
    create_snmp_section_plugin_from_legacy,)
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin

InventoryPluginNameStr = str
InventoryInfo = Dict[str, Any]

# Inventory plugins have dependencies to check plugins and the inventory
# plugins need the check API. This is the easiest solution to get this
# working at the moment. In future some kind of OOP approach would be better.
# TODO: Clean this up!
#from cmk.base.config import *

# Inventory plugins
inv_info: Dict[InventoryPluginNameStr, InventoryInfo] = {}
# Inventory export hooks
inv_export: Dict[str, Dict[str, Any]] = {}
# The checks are loaded into this dictionary. Each check
_plugin_contexts: Dict[str, Dict[str, Any]] = {}
# becomes a separat sub-dictionary, named by the check name
# These are the contexts of the check include files
_include_contexts: Dict[str, Any] = {}

# This is needed for the auto-migration to the new check API.
# For some reason, inspect.getsourcefile fails to find the
# right file, so we pass a list of candidates.
_plugin_file_lookup: Dict[str, str] = {}


def load_legacy_inventory_plugins(
    get_check_api_context: config.GetCheckApiContext,
    get_inventory_context: config.GetInventoryApiContext,
) -> None:
    loaded_files: Set[str] = set()
    filelist = config.get_plugin_paths(str(cmk.utils.paths.local_inventory_dir),
                                       cmk.utils.paths.inventory_dir)

    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue  # ignore editor backup / temp files

        file_name = os.path.basename(f)
        if file_name in loaded_files:
            continue  # skip already loaded files (e.g. from local)

        try:
            plugin_context = _new_inv_context(get_check_api_context, get_inventory_context)

            _load_plugin_includes(f, plugin_context)

            exec(open(f).read(), plugin_context)  # yapf: disable
            loaded_files.add(file_name)
        except Exception as e:
            console.error("Error in inventory plugin file %s: %s\n", f, e)
            if cmk.utils.debug.enabled():
                raise
            continue

        # Now store the check context for all plugins found in this file
        for check_plugin_name in inv_info:
            _plugin_contexts.setdefault(check_plugin_name, plugin_context)
            _plugin_file_lookup.setdefault(check_plugin_name, f)

    _extract_snmp_sections(inv_info, _plugin_file_lookup)
    _extract_inventory_plugins(inv_info)


def _extract_snmp_sections(
    inf_info: Dict[InventoryPluginNameStr, InventoryInfo],
    plugin_file_lookup: Dict[str, str],
) -> None:
    for plugin_name, plugin_info in sorted(inv_info.items()):
        if 'snmp_info' not in plugin_info:
            continue
        section_name = section_name_of(plugin_name)
        if isinstance(agent_based_register.get_section_plugin(SectionName(section_name)),
                      SNMPSectionPlugin):
            continue

        fallback_files = ([_include_file_path(i) for i in plugin_info.get('includes', [])] +
                          [plugin_file_lookup[plugin_name]])

        try:
            agent_based_register.add_section_plugin(
                create_snmp_section_plugin_from_legacy(
                    section_name,
                    {},
                    plugin_info['snmp_scan_function'],
                    plugin_info['snmp_info'],
                    scan_function_fallback_files=fallback_files,
                ))
        except (NotImplementedError, KeyError, AssertionError, ValueError):
            msg = config.AUTO_MIGRATION_ERR_MSG % ('section', plugin_name)
            if cmk.utils.debug.enabled():
                raise MKGeneralException(msg)
            console.warning(msg)


def _extract_inventory_plugins(inf_info: Dict[InventoryPluginNameStr, InventoryInfo],) -> None:
    for plugin_name, plugin_info in sorted(inv_info.items()):
        try:
            agent_based_register.add_inventory_plugin(
                create_inventory_plugin_from_legacy(
                    plugin_name,
                    plugin_info,
                    # count inherited extra sections from check plugin:
                    len(config.check_info.get(plugin_name, {}).get("extra_sections", [])),
                ))
        except NotImplementedError:
            msg = config.AUTO_MIGRATION_ERR_MSG % ('inventory', plugin_name)
            if cmk.utils.debug.enabled():
                raise MKGeneralException(msg)
            console.warning(msg)


def _new_inv_context(get_check_api_context: config.GetCheckApiContext,
                     get_inventory_context: config.GetInventoryApiContext) -> Dict:
    # Add the data structures where the inventory plugins register with Checkmk
    context = {
        "inv_info": inv_info,
        "inv_export": inv_export,
    }
    # NOTE: For better separation it would be better to copy the values, but
    # this might consume too much memory, so we simply reference them.
    # NOTE: It is possible that check includes are included, so we need the
    # usual check context here, too.
    context.update(config.new_check_context(get_check_api_context))
    context.update(get_inventory_context())
    return context


# Load the definitions of the required include files for this check
# Working with imports when specifying the includes would be much cleaner,
# sure. But we need to deal with the current check API.
def _load_plugin_includes(check_file_path: str, plugin_context: Dict) -> None:
    for name in config.includes_of_plugin(check_file_path):
        path = _include_file_path(name)
        try:
            exec(open(path).read(), plugin_context)  # yapf: disable
        except Exception as e:
            console.error("Error in include file %s: %s\n", path, e)
            if cmk.utils.debug.enabled():
                raise


def _include_file_path(name: str) -> str:
    local_path = cmk.utils.paths.local_inventory_dir / name
    if local_path.exists():
        return str(local_path)

    shared_path = os.path.join(cmk.utils.paths.inventory_dir, name)
    if os.path.exists(shared_path):
        return shared_path
    return config.check_include_file_path(name)
