#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Iterable, Mapping, Optional, Tuple

# The only reasonable thing to do here is use our own version parsing. It's to big to duplicate.
from cmk.utils.version import parse_check_mk_version  # pylint: disable=cmk-module-layer-violation

from .agent_based_api.v1 import check_levels, regex, register, Result, Service, State, TableRow
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, InventoryResult, StringTable
from .utils.checkmk import Plugin, PluginSection


def _extract_cache_interval(path: str) -> Optional[int]:
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


def _parse_version_int(version_str: str) -> Optional[int]:
    """
    >>> _parse_version_int("2.1.0p12")
    2010050012
    """
    try:
        return parse_check_mk_version(version_str)
    except ValueError:
        return None


def _parse_plugin(line: str, prefix: str) -> Optional[Plugin]:
    """
    >>> _parse_plugin(
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


def parse_checkmk_agent_plugins_lnx(string_table: StringTable) -> PluginSection:

    assert string_table[0][0].startswith("pluginsdir ")
    plugins_dir = string_table[0][0][len("pluginsdir ") :]

    assert string_table[1][0].startswith("localdir ")
    local_dir = string_table[1][0][len("localdir ") :]

    return PluginSection(
        plugins=[
            plugin
            for line, in string_table[2:]
            if (plugin := _parse_plugin(line, plugins_dir)) is not None
        ],
        local_checks=[
            lcheck
            for line, in string_table[2:]
            if (lcheck := _parse_plugin(line, local_dir)) is not None
        ],
    )


register.agent_section(
    name="checkmk_agent_plugins_lnx",
    parse_function=parse_checkmk_agent_plugins_lnx,
    parsed_section_name="checkmk_agent_plugins",
)


def discover_checkmk_agent_plugins(section: PluginSection) -> DiscoveryResult:
    if section.plugins or section.local_checks:
        yield Service()


def check_checkmk_agent_plugins(params: Mapping[str, Any], section: PluginSection) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Agent plugins: {len(section.plugins)}",
    )
    yield Result(
        state=State.OK,
        summary=f"Local checks: {len(section.local_checks)}",
    )

    if (min_versions := params.get("min_versions")) is None:
        return

    if (exclude_pattern := params.get("exclude_pattern")) is None:
        plugins = section.plugins
        lchecks = section.local_checks
    else:
        comp = regex(exclude_pattern)
        plugins = [p for p in section.plugins if not comp.search(p.name)]
        lchecks = [p for p in section.local_checks if not comp.search(p.name)]

    yield from _check_min_version(plugins, min_versions, "Agent plugin")
    yield from _check_min_version(lchecks, min_versions, "Local check")


def _check_min_version(
    plugins: Iterable[Plugin], levels_str: Tuple[str, str], type_: str
) -> Iterable[Result]:
    levels = (parse_check_mk_version(levels_str[0]), parse_check_mk_version(levels_str[1]))

    render_info = {p.version_int: p.version for p in plugins}
    render_info.update(zip(levels, levels_str))

    for plugin in plugins:
        if plugin.version_int is None:
            yield Result(
                state=State.UNKNOWN,
                summary=f"{type_} {plugin.name!r}: unable to parse version {plugin.version!r}",
            )
        else:
            (result,) = check_levels(
                plugin.version_int,
                levels_lower=levels,
                render_func=lambda v: render_info[int(v)],
                label=f"{type_} {plugin.name!r}",
            )
            if result.state is not State.OK:
                yield result


register.check_plugin(
    name="checkmk_agent_plugins",
    service_name="Checkmk agent plugins",
    discovery_function=discover_checkmk_agent_plugins,
    check_function=check_checkmk_agent_plugins,
    check_default_parameters={},
    check_ruleset_name="checkmk_agent_plugins",
)


def inventory_checkmk_agent_plugins(section: PluginSection) -> InventoryResult:
    path = ("software", "applications", "checkmk-agent")
    for type_, plugins in zip(("plugins", "local_checks"), (section.plugins, section.local_checks)):
        yield from (
            TableRow(
                path=[*path, type_],
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


register.inventory_plugin(
    name="checkmk_agent_plugins",
    inventory_function=inventory_checkmk_agent_plugins,
)
