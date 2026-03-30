#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm_mq.lib import ibm_mq_check_version

# <<<ibm_mq_plugin:sep(58)>>>
# version|2.0.4
# dspmq|OK
# runmqsc|Not executable


def parse_ibm_mq_plugin(string_table: StringTable) -> dict[str, str]:
    parsed = {}
    for line in string_table:
        key = line[0].strip()
        value = line[1].strip()
        parsed[key] = value
    return parsed


def discover_ibm_mq_plugin(section: dict[str, str]) -> DiscoveryResult:
    if section:
        yield Service()


def check_tool(tool_name: str, parsed: dict[str, str]) -> Result:
    if tool_name not in parsed:
        return Result(state=State.UNKNOWN, summary=f"{tool_name}: No agent info")

    text = parsed[tool_name]
    state = State.OK if text == "OK" else State.CRIT
    return Result(state=state, summary=f"{tool_name}: {text}")


def check_ibm_mq_plugin(params: Mapping[str, Any], section: dict[str, str]) -> CheckResult:
    if not section:
        return

    actual_version = section.get("version")
    version_state, version_summary = ibm_mq_check_version(actual_version, params, "Plugin version")
    yield Result(state=State(version_state), summary=version_summary)
    yield check_tool("dspmq", section)
    yield check_tool("runmqsc", section)


agent_section_ibm_mq_plugin = AgentSection(
    name="ibm_mq_plugin",
    parse_function=parse_ibm_mq_plugin,
)


check_plugin_ibm_mq_plugin = CheckPlugin(
    name="ibm_mq_plugin",
    service_name="IBM MQ Plugin",
    discovery_function=discover_ibm_mq_plugin,
    check_function=check_ibm_mq_plugin,
    check_ruleset_name="ibm_mq_plugin",
    check_default_parameters={},
)
