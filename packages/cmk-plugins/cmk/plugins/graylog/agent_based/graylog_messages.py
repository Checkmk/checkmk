#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)
from cmk.plugins.graylog.lib import (
    deserialize_and_merge_json,
    GraylogMessagesParams,
    handle_graylog_messages,
)

# <<<graylog_messages>>>
# {"events": 1268586}


@dataclass(frozen=True)
class Section:
    events: int | float


def parse_graylog_messages(string_table: StringTable) -> Section | None:
    match deserialize_and_merge_json(string_table):
        case {"events": int() | float() as events}:
            return Section(events=events)
        case _:
            return None


def discover_graylog_messages(section: Section) -> DiscoveryResult:
    yield Service()


def check_graylog_messages(params: GraylogMessagesParams, section: Section) -> CheckResult:
    yield from handle_graylog_messages(section.events, params, include_diff=True)


agent_section_graylog_messages = AgentSection(
    name="graylog_messages",
    parse_function=parse_graylog_messages,
)


check_plugin_graylog_messages = CheckPlugin(
    name="graylog_messages",
    service_name="Graylog Messages",
    discovery_function=discover_graylog_messages,
    check_function=check_graylog_messages,
    check_ruleset_name="graylog_messages",
    check_default_parameters={
        "msgs_upper": ("no_levels", None),
        "msgs_lower": ("no_levels", None),
        "msgs_avg": 30,
        "msgs_avg_upper": ("no_levels", None),
        "msgs_avg_lower": ("no_levels", None),
        "msgs_diff": 1800.0,
        "msgs_diff_upper": ("no_levels", None),
        "msgs_diff_lower": ("no_levels", None),
    },
)
