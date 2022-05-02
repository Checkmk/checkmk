#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Load legacy inventory plugins

The only public function of this file loads all inventory plugins that are
programmed against the legacy (inv_info-dict) API.
They are auto-migrated immediately, and become available via the regular
exposed cmk.base.api.agent_based.register API functions.

This file is an outlier with respect to how the code is organized in files.
It must be considered the inventory specific extension of cmk.base.config.

Once we have migrated all inventory plugins programmed against the new API
all that this file deals with are inventory export hooks, which should be
handeled somewhere else entirely.
"""
import os
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Sequence, Set

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import SectionName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_utils
import cmk.base.config as config
from cmk.base.api.agent_based.register.inventory_plugins_legacy import (
    create_inventory_plugin_from_legacy,
)
from cmk.base.api.agent_based.register.section_plugins_legacy import (
    create_snmp_section_plugin_from_legacy,
)
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin

InventoryInfo = Dict[str, Any]
GetInventoryApiContext = config.GetInventoryApiContext

# Inventory plugins used to have dependencies to check plugins and the inventory
# plugins need the check API. This is the easiest solution to get this
# working at the moment.
# Once the old API is no longer supported, this file can be removed entirely.

# Inventory plugins
_inv_info: Dict[str, InventoryInfo] = {}
# Inventory export hooks
inv_export: Dict[str, Dict[str, Any]] = {}
# The checks are loaded into this dictionary. Each check
_plugin_contexts: Dict[str, Dict[str, Any]] = {}
# becomes a separate sub-dictionary, named by the check name
# These are the contexts of the check include files
_include_contexts: Dict[str, Any] = {}

# This is needed for the auto-migration to the new check API.
# For some reason, inspect.getsourcefile fails to find the
# right file, so we pass a list of candidates.
_plugin_file_lookup: Dict[str, str] = {}


def load_legacy_inventory_plugins(
    get_check_api_context: config.GetCheckApiContext,
    get_inventory_context: GetInventoryApiContext,
) -> Sequence[str]:
    """load all old-school inventory plugins into the modern agent based registry"""
    errors = []
    loaded_files: Set[str] = set()
    file_list = config.get_plugin_paths(
        str(cmk.utils.paths.local_inventory_dir), cmk.utils.paths.inventory_dir
    )

    with suppress(FileNotFoundError):
        if local_plugins := list(cmk.utils.paths.local_inventory_dir.iterdir()):
            errors.append(
                f"WARNING: {len(local_plugins)} depracted plugins will be ignored in Checkmk "
                f"version 2.2 (see werk #14084): {', '.join(f.name for f in local_plugins)}\n"
            )

    for f in file_list:
        if f[0] == "." or f[-1] == "~":
            continue  # ignore editor backup / temp files

        file_name = os.path.basename(f)
        if file_name in loaded_files:
            continue  # skip already loaded files (e.g. from local)

        try:
            plugin_context = _new_inv_context(get_check_api_context, get_inventory_context)

            _load_plugin_includes(f, plugin_context)

            exec(Path(f).read_text(), plugin_context)
            loaded_files.add(file_name)
        except Exception as exc:
            errors.append(f"Error in inventory plugin file {f}: {exc}\n")
            if cmk.utils.debug.enabled():
                raise
            continue

        # Now store the check context for all plugins found in this file
        for check_plugin_name in _inv_info:
            _plugin_contexts.setdefault(check_plugin_name, plugin_context)
            _plugin_file_lookup.setdefault(check_plugin_name, f)

    errors.extend(_extract_snmp_sections(_inv_info, _plugin_file_lookup))
    errors.extend(_extract_inventory_plugins(_inv_info))

    return errors


def _extract_snmp_sections(
    inv_info: Dict[str, InventoryInfo],
    plugin_file_lookup: Dict[str, str],
) -> Sequence[str]:
    errors = []
    for plugin_name, plugin_info in sorted(inv_info.items()):
        if "snmp_info" not in plugin_info:
            continue
        section_name = section_name_of(plugin_name)
        if isinstance(
            agent_based_register.get_section_plugin(SectionName(section_name)), SNMPSectionPlugin
        ):
            continue

        fallback_files = [_include_file_path(i) for i in plugin_info.get("includes", [])] + [
            plugin_file_lookup[plugin_name]
        ]

        try:
            agent_based_register.add_section_plugin(
                create_snmp_section_plugin_from_legacy(
                    section_name,
                    {},
                    plugin_info["snmp_scan_function"],
                    plugin_info["snmp_info"],
                    scan_function_fallback_files=fallback_files,
                    # We have to validate, because we read inventory plugin files
                    # directly, and do not know whether they changed.
                    validate_creation_kwargs=True,
                )
            )
        except (NotImplementedError, KeyError, AssertionError, ValueError):
            msg = config.AUTO_MIGRATION_ERR_MSG % ("section", plugin_name)
            if cmk.utils.debug.enabled():
                raise MKGeneralException(msg)
            errors.append(msg)

    return errors


def _extract_inventory_plugins(
    inv_info: Dict[str, InventoryInfo],
) -> Sequence[str]:
    errors = []
    for plugin_name, plugin_info in sorted(inv_info.items()):
        try:
            agent_based_register.add_inventory_plugin(
                create_inventory_plugin_from_legacy(
                    plugin_name,
                    plugin_info,
                )
            )
        except NotImplementedError:
            msg = config.AUTO_MIGRATION_ERR_MSG % ("inventory", plugin_name)
            if cmk.utils.debug.enabled():
                raise MKGeneralException(msg)
            errors.append(msg)

    return errors


def _new_inv_context(
    get_check_api_context: config.GetCheckApiContext,
    get_inventory_context: GetInventoryApiContext,
) -> Dict:
    # Add the data structures where the inventory plugins register with Checkmk
    context = {
        "inv_info": _inv_info,
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
            exec(Path(path).read_text(), plugin_context)
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
