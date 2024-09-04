#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

# The only reasonable thing to do here is use our own version parsing. It's to big to duplicate.
from cmk.ccc.version import parse_check_mk_version  # pylint: disable=cmk-module-layer-violation

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow
from cmk.plugins.lib.checkmk import Plugin, PluginSection


def _extract_cache_interval(path: str) -> int | None:
    """
    >>> _extract_cache_interval("/123/my_plugin.sh")
    123
    >>> print(_extract_cache_interval("my_plugin.sh"))
    None
    """
    try:
        return int(path.strip("/").split("/", 1)[0])
    except ValueError:
        return None


def _parse_version_int(version_str: str) -> int | None:
    """
    >>> _parse_version_int("2.1.0p12")
    2010050012
    """
    try:
        return parse_check_mk_version(version_str)
    except ValueError:
        return None


def _parse_plugin_lnx(line: str, prefix: str) -> Plugin | None:
    """
    >>> _parse_plugin_lnx(
    ...    '/usr/lib/check_mk_agent/plugins/mk_filestats.py:__version__ = "2.1.0i1"',
    ...    '/usr/lib/check_mk_agent/plugins',
    ... )
    Plugin(name='mk_filestats.py', version='2.1.0i1', version_int=2010010100, cache_interval=None)
    """
    if not line.startswith(prefix):
        return None

    if "__version__" in line:
        raw_path, raw_version = line[len(prefix) :].split(":__version__", 1)
    elif "CMK_VERSION" in line:
        raw_path, raw_version = line[len(prefix) :].split(":CMK_VERSION", 1)
    else:
        return None

    version = raw_version.strip(" ='\"")
    return Plugin(
        name=raw_path.rsplit("/", 1)[-1],
        version=version,
        version_int=_parse_version_int(version),
        cache_interval=_extract_cache_interval(raw_path),
    )


def _parse_plugin_win(line: str, prefix: str) -> Plugin | None:
    """
    >>> _parse_plugin_win(
    ...    'c:\\\\ProgramData\\\\checkmk\\\\agent\\\\plugins\\\\windows_if.py:CMK_VERSION = "2.1.0i1"',
    ...    'c:\\\\ProgramData\\\\checkmk\\\\agent\\\\plugins',
    ... )
    Plugin(name='windows_if.py', version='2.1.0i1', version_int=2010010100, cache_interval=None)
    """
    if not line.startswith(prefix):
        return None

    if "CMK_VERSION" in line:
        raw_path, raw_version = line[len(prefix) :].split(":CMK_VERSION", 1)
    else:
        return None

    version = raw_version.strip(" ='\"")
    return Plugin(
        name=raw_path.rsplit("\\", 1)[-1],
        version=version,
        version_int=_parse_version_int(version),
        cache_interval=_extract_cache_interval(raw_path),
    )


def _parse_checkmk_agent_plugins_core(
    string_table: StringTable, parser: Callable[[str, str], Plugin | None]
) -> PluginSection:
    assert string_table[0][0].startswith("pluginsdir ")
    plugins_dir = string_table[0][0][len("pluginsdir ") :]

    assert string_table[1][0].startswith("localdir ")
    local_dir = string_table[1][0][len("localdir ") :]

    return PluginSection(
        plugins=[
            plugin
            for (line,) in string_table[2:]
            if (plugin := parser(line, plugins_dir)) is not None
        ],
        local_checks=[
            lcheck
            for (line,) in string_table[2:]
            if (lcheck := parser(line, local_dir)) is not None
        ],
    )


def parse_checkmk_agent_plugins_lnx(string_table: StringTable) -> PluginSection:
    return _parse_checkmk_agent_plugins_core(string_table, _parse_plugin_lnx)


def parse_checkmk_agent_plugins_win(string_table: StringTable) -> PluginSection:
    return _parse_checkmk_agent_plugins_core(string_table, _parse_plugin_win)


agent_section_checkmk_agent_plugins_lnx = AgentSection(
    name="checkmk_agent_plugins_lnx",
    parse_function=parse_checkmk_agent_plugins_lnx,
    parsed_section_name="checkmk_agent_plugins",
)

agent_section_checkmk_agent_plugins_win = AgentSection(
    name="checkmk_agent_plugins_win",
    parse_function=parse_checkmk_agent_plugins_win,
    parsed_section_name="checkmk_agent_plugins",
)


def inventory_checkmk_agent_plugins(section: PluginSection) -> InventoryResult:
    for type_, plugins in zip(("plugins", "local_checks"), (section.plugins, section.local_checks)):
        yield from (
            TableRow(
                path=["software", "applications", "checkmk-agent", type_],
                key_columns={
                    "name": plugin.name,
                },
                inventory_columns={
                    "version": plugin.version,
                    "cache_interval": plugin.cache_interval,
                },
            )
            for plugin in plugins
        )


inventory_plugin_checkmk_agent_plugins = InventoryPlugin(
    name="checkmk_agent_plugins",
    inventory_function=inventory_checkmk_agent_plugins,
)
