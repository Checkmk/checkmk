#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import cmk.ccc.debug

import cmk.utils.paths
from cmk.utils.log import console
from cmk.utils.plugin_loader import load_plugins_with_exceptions

from cmk.bakery.v1 import (
    BakeryPlugin,
    create_bakery_plugin,
    FilesFunction,
    ScriptletsFunction,
    WindowsConfigFunction,
)

registered_bakery_plugins: dict[str, BakeryPlugin] = {}


def bakery_plugin(
    *,
    name: str,
    files_function: FilesFunction | None = None,
    scriptlets_function: ScriptletsFunction | None = None,
    windows_config_function: WindowsConfigFunction | None = None,
) -> None:
    """Register a Bakery Plugin (Bakelet) to Checkmk

    This registration function accepts a plug-in name (mandatory) and up to three
    generator functions that may yield different types of artifacts.
    The generator functions will be called with keyword-arguments 'conf' and/or 'aghash'
    while processing the bakery plug-in (Callbacks), thus the specific call depends on the
    argument names of the provided functions.
    For keyword-arg 'conf', the corresponding WATO configuration will be provided.
    For keyword-arg 'aghash', the configuration hash of the resulting agent package
    will be provided.
    Unused arguments can be omitted in the function's signatures.

    Args:
        name: The name of the agent plug-in to be processed. It must be unique, and match
            the name of the corresponding WATO rule. It may only contain ascii
            letters (A-Z, a-z), digits (0-9), and underscores (_).
        files_function: Generator function that yields file artifacts.
            Allowed function argument is 'conf'.
            Yielded artifacts must must be of types 'Plugin', 'PluginConfig',
            'SystemConfig', or 'SystemBinary'.
        scriptlets_function: Generator function that yields scriptlet artifacts.
            Allowed function arguments are 'conf' and 'aghash'.
            Yielded artifacts must be of type 'Scriptlet'.
        windows_config_function: generator function that yields windows config artifacts.
            Allowed function arguments are 'conf' and 'aghash'.
            Yielded artifacts must be of types 'WindowsConfigEntry', 'WindowsGlobalConigEntry',
            'WindowsSystemConfigEntry', 'WindowsConfigItems', or 'WindowsPluginConfig'.
    """

    bakery_plugin_object = create_bakery_plugin(
        name=name,
        files_function=files_function,
        scriptlets_function=scriptlets_function,
        windows_config_function=windows_config_function,
    )

    registered_bakery_plugins[str(bakery_plugin_object.name)] = bakery_plugin_object


def get_bakery_plugins() -> dict[str, BakeryPlugin]:
    for plugin, exception in load_plugins_with_exceptions("cmk.base.cee.plugins.bakery"):
        console.error(f"Error in bakery plug-in {plugin}: {exception}", file=sys.stderr)
        if cmk.ccc.debug.enabled():
            raise exception

    return registered_bakery_plugins
