#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_mq import ibm_mq_check_version

check_info = {}

# <<<ibm_mq_plugin:sep(58)>>>
# version|2.0.4
# dspmq|OK
# runmqsc|Not executable


def parse_ibm_mq_plugin(string_table):
    parsed = {}
    for line in string_table:
        key = line[0].strip()
        value = line[1].strip()
        parsed[key] = value
    return parsed


def discover_ibm_mq_plugin(parsed):
    if parsed:
        return [(None, {})]
    return []


def check_tool(tool_name, parsed):
    if tool_name not in parsed:
        return 3, "%s: No agent info" % tool_name

    status, text = 0, parsed[tool_name]
    if text != "OK":
        status = 2
    return status, f"{tool_name}: {text}"


def check_ibm_mq_plugin(_no_item, params, parsed):
    if not parsed:
        return

    actual_version = parsed.get("version")
    yield ibm_mq_check_version(actual_version, params, "Plugin version")
    yield check_tool("dspmq", parsed)
    yield check_tool("runmqsc", parsed)


check_info["ibm_mq_plugin"] = LegacyCheckDefinition(
    name="ibm_mq_plugin",
    parse_function=parse_ibm_mq_plugin,
    service_name="IBM MQ Plugin",
    discovery_function=discover_ibm_mq_plugin,
    check_function=check_ibm_mq_plugin,
    check_ruleset_name="ibm_mq_plugin",
)
