#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from itertools import chain

import cmk.ccc.debug
from cmk.bakery.v1 import (
    BakeryPlugin,
    create_bakery_plugin,
    FilesFunction,
    ScriptletsFunction,
    WindowsConfigFunction,
)
from cmk.utils.log import console
from cmk.utils.plugin_loader import load_plugins_with_exceptions

registered_bakery_plugins: dict[str, BakeryPlugin] = {}


def bakery_plugin(
    *,
    name: str,
    files_function: FilesFunction | None = None,
    scriptlets_function: ScriptletsFunction | None = None,
    windows_config_function: WindowsConfigFunction | None = None,
) -> None:
    # Register a bakery plugin; doc is maintained in the rst files of the sphinx doc
    bakery_plugin_object = create_bakery_plugin(
        name=name,
        files_function=files_function,
        scriptlets_function=scriptlets_function,
        windows_config_function=windows_config_function,
    )

    registered_bakery_plugins[str(bakery_plugin_object.name)] = bakery_plugin_object


def get_bakery_plugins() -> dict[str, BakeryPlugin]:
    for plugin, exception in chain(
        # This is where our unmigrated shipped bakery plugins reside:
        load_plugins_with_exceptions("cmk.base.nonfree.plugins.bakery"),
        # This is where third party bakery plugins likely reside, as this is the
        # path we advertised previous to our edition renaming.
        # Let's be as undisruptive as possible, we're in the process of replacing the
        # registration approach completely anyway (see Werk #18600 for a timeline)
        load_plugins_with_exceptions("cmk.base.cee.plugins.bakery"),
        # We are in the process of deprecating cmk.base.api.bakery.register,
        # and migrate our plugins to the new cmk.bakery.v2 API.
        # For the time being, we also load this namespace, to allow to separate the
        # migration into two steps ("going public" and using the new API)).
        # CMK-31432
        load_plugins_with_exceptions("cmk.base.plugins.bakery"),
    ):
        console.error(f"Error in bakery plug-in {plugin}: {exception}", file=sys.stderr)
        if cmk.ccc.debug.enabled():
            raise exception

    return registered_bakery_plugins
