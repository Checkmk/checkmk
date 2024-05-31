#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.checkmk import CachedPlugin, CachedPluginsSection, CachedPluginType


def _split_plugin_descr(plugin_descr: str) -> tuple[CachedPluginType | None, str]:
    try:
        plugin_type, plugin_name = plugin_descr.split("_", maxsplit=1)
        return CachedPluginType(plugin_type), plugin_name
    except ValueError:
        return None, plugin_descr


def parse_checkmk_cached_plugins(string_table: StringTable) -> CachedPluginsSection:
    # "killfailed" has been removed from the agent in 2.4
    # Currently it is still used by mk_oracle
    fail_types = ("timeout", "killfailed")
    temp_section: dict[str, list[CachedPlugin]] = {
        fail_type: [
            CachedPlugin(*_split_plugin_descr(plugin), int(timeout), int(pid))
            for key, plugin, timeout, pid in string_table
            if key.lower() == fail_type
        ]
        for fail_type in fail_types
    }

    return CachedPluginsSection(
        timeout=temp_section["timeout"] or None,
        killfailed=temp_section["killfailed"] or None,
    )


agent_section_checkmk_cached_plugins = AgentSection(
    name="checkmk_cached_plugins",
    parse_function=parse_checkmk_cached_plugins,
)
