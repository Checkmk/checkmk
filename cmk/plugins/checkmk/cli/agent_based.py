#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import sys
from collections.abc import Container, Iterable, Mapping

from cmk.ccc.exceptions import MKBailOut
from cmk.checkengine.parser import (
    NO_SELECTION,
    SectionNameCollection,
)
from cmk.checkengine.plugin_backend import (
    filter_relevant_raw_sections,
    load_all_plugins,
)
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    CheckPlugin,
    CheckPluginName,
    InventoryPlugin,
    InventoryPluginName,
    SectionName,
    SNMPSectionPlugin,
)
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console


def load_checks(*, debug: bool) -> AgentBasedPlugins:
    plugins = load_all_plugins(raise_errors=debug)
    if sys.stderr.isatty():
        for error_msg in plugins.errors:
            console.error(error_msg, file=sys.stderr)
    return plugins


def _lookup_plugin[PluginName: (CheckPluginName, InventoryPluginName)](
    plugin_name: PluginName, plugins: Mapping[PluginName, CheckPlugin | InventoryPlugin]
) -> CheckPlugin | InventoryPlugin:
    try:
        return plugins[plugin_name]
    except KeyError as exc:
        raise MKBailOut(f"Unknown check plugin '{plugin_name}'") from exc


def extract_plugin_selection[PluginName: (CheckPluginName, InventoryPluginName)](
    *,
    detect_plugins: frozenset[str] | None,
    detect_sections: frozenset[SectionName] | None,
    selected_plugins: frozenset[PluginName] | None,
    plugins: Mapping[PluginName, CheckPlugin | InventoryPlugin],
    sections: Iterable[AgentSectionPlugin | SNMPSectionPlugin],
    type_: type[PluginName],
) -> tuple[SectionNameCollection, Container[PluginName]]:
    if detect_plugins is None:
        return (
            NO_SELECTION if detect_sections is None else detect_sections,
            EVERYTHING if selected_plugins is None else selected_plugins,
        )

    if detect_sections is not None or selected_plugins is not None:
        raise MKBailOut(
            "Option '--detect-plugins' must not be combined with --detect-sections/--plugins"
        )

    if detect_plugins == {"@all"}:
        # this is the same as ommitting the option entirely.
        # (mo) ... which is weird, because specifiying *all* plugins would do
        # something different. Keeping this for compatibility with old --checks
        return NO_SELECTION, EVERYTHING

    plugin_names = {type_(p) for p in detect_plugins}
    return (
        frozenset(
            filter_relevant_raw_sections(
                consumers=(_lookup_plugin(pn, plugins) for pn in plugin_names),
                sections=sections,
            )
        ),
        plugin_names,
    )
