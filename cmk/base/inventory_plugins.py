#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Any, Dict, Set, Iterator, Tuple, Optional

import cmk.utils.paths
import cmk.utils.debug
from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import SectionName

import cmk.base.config as config
import cmk.base.check_utils

from cmk.base.api.agent_based.register.section_plugins_legacy import (
    create_snmp_section_plugin_from_legacy,)

from cmk.utils.type_defs import CheckPluginNameStr, InventoryPluginName
InventoryInfo = Dict[str, Any]

# Inventory plugins have dependencies to check plugins and the inventory
# plugins need the check API. This is the easiest solution to get this
# working at the moment. In future some kind of OOP approach would be better.
# TODO: Clean this up!
#from cmk.base.config import *

# Inventory plugins
inv_info: Dict[InventoryPluginName, InventoryInfo] = {}
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


def load_plugins(get_check_api_context: config.GetCheckApiContext,
                 get_inventory_context: config.GetInventoryApiContext) -> None:
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

    _extract_snmp_sections()


def _extract_snmp_sections() -> None:
    for plugin_name, plugin_info in sorted(inv_info.items()):
        if 'snmp_info' not in plugin_info:
            continue
        section_name = section_name_of(plugin_name)
        if config.get_registered_section_plugin(SectionName(section_name)):
            continue

        fallback_files = ([_include_file_path(i) for i in plugin_info.get('includes', [])] +
                          [_plugin_file_lookup[plugin_name]])

        try:
            snmp_section_plugin = create_snmp_section_plugin_from_legacy(
                section_name,
                {},
                plugin_info['snmp_scan_function'],
                plugin_info['snmp_info'],
                scan_function_fallback_files=fallback_files,
            )
        except (NotImplementedError, KeyError, AssertionError, ValueError):
            msg = config.AUTO_MIGRATION_ERR_MSG % ('section', plugin_name)
            if cmk.utils.debug.enabled():
                raise MKGeneralException(msg)
            # TODO (mo): bring this back:
            #console.warning(msg)
        else:
            config.registered_snmp_sections[snmp_section_plugin.name] = snmp_section_plugin


def _new_inv_context(get_check_api_context: config.GetCheckApiContext,
                     get_inventory_context: config.GetInventoryApiContext) -> Dict:
    # Add the data structures where the inventory plugins register with Check_MK
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


def is_snmp_plugin(check_plugin_name: str) -> bool:
    section_name = section_name_of(check_plugin_name)
    return SectionName(section_name) in config.registered_snmp_sections


def sorted_inventory_plugins() -> Iterator[Tuple[CheckPluginNameStr, InventoryInfo]]:
    # First resolve *all* dependencies. This ensures that there
    # are no cyclic dependencies, and that the 'depends on'
    # relation is transitive.
    resolved_dependencies: Dict[str, Set[str]] = {}

    def resolve_plugin_dependencies(
            plugin_name: CheckPluginNameStr,
            known_dependencies: Optional[Set[CheckPluginNameStr]] = None
    ) -> Set[CheckPluginNameStr]:
        '''recursively aggregate all plugin dependencies'''
        if known_dependencies is None:
            known_dependencies = set()
        if plugin_name in resolved_dependencies:
            known_dependencies.update(resolved_dependencies[plugin_name])
            return known_dependencies

        try:
            direct_dependencies = set(inv_info[plugin_name].get('depends_on', []))
        except KeyError:
            raise MKGeneralException("unknown plugin dependency: %r" % plugin_name)

        new_dependencies = direct_dependencies - known_dependencies
        known_dependencies.update(new_dependencies)
        for dependency in new_dependencies:
            known_dependencies = resolve_plugin_dependencies(dependency, known_dependencies)
        return known_dependencies

    for plugin_name in inv_info:
        resolved_dependencies[plugin_name] = resolve_plugin_dependencies(plugin_name)
        if plugin_name in resolved_dependencies[plugin_name]:
            raise MKGeneralException("cyclic plugin dependencies for %r" % plugin_name)

    # The plugins are now a partially ordered set with respect to
    # the 'depends on' relation. That means we can iteratively
    # yield the minimal elements
    remaining_plugins = set(inv_info)
    yielded_plugins: Set[str] = set()
    while remaining_plugins:
        for plugin_name in sorted(remaining_plugins):
            dependencies = resolved_dependencies[plugin_name]
            if dependencies <= yielded_plugins:
                yield plugin_name, inv_info[plugin_name]
                yielded_plugins.add(plugin_name)
                remaining_plugins.remove(plugin_name)
