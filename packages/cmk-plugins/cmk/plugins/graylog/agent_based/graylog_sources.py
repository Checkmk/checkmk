#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)
from cmk.plugins.graylog.lib import GraylogMessagesParams, handle_graylog_messages

# <<<graylog_sources>>>
# {"sources": {"172.18.0.1": {"messages": 457, "has_since": false}}}

# <<<graylog_sources>>>
# {"sources": {"172.18.0.1": {"messages": 457, "has_since": true, "messages_since": 5, "source_since": 1800}}}


@dataclass
class SourceInfo:
    num_messages: int | None
    has_since_argument: bool
    timespan: int | None
    num_messages_in_timespan: int


SourceInfoSection = Mapping[str, SourceInfo]


def parse_graylog_sources(string_table: StringTable) -> SourceInfoSection:
    parsed: MutableMapping[str, SourceInfo] = {}

    for line in string_table:
        match json.loads(line[0]):
            case {"sources": dict() as source_name}:
                pass
            case _:
                continue

        for name, data in source_name.items():
            # Graylog only reports "messages_since"/"source_since" when a "since"
            # argument was used (has_since_argument); otherwise they are absent.
            match data:
                case {
                    "has_since_argument": True,
                    "messages": int(num_messages),
                    "messages_since": int(messages_since),
                    "source_since": int(timespan),
                }:
                    parsed.setdefault(
                        name,
                        SourceInfo(
                            num_messages=num_messages,
                            has_since_argument=True,
                            timespan=timespan,
                            num_messages_in_timespan=messages_since,
                        ),
                    )
                case {
                    "has_since_argument": bool(has_since_argument),
                    "messages": int(num_messages),
                }:
                    parsed.setdefault(
                        name,
                        SourceInfo(
                            num_messages=num_messages,
                            has_since_argument=has_since_argument,
                            timespan=None,
                            num_messages_in_timespan=0,
                        ),
                    )
                case _:
                    continue

    return parsed


def discover_graylog_sources(section: SourceInfoSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _handle_graylog_sources_messages(
    num_messages: int, item_data: SourceInfo, params: GraylogMessagesParams
) -> CheckResult:
    yield from handle_graylog_messages(
        num_messages, params, include_diff=not item_data.has_since_argument
    )

    if item_data.has_since_argument and item_data.timespan is not None:
        yield from check_levels(
            item_data.num_messages_in_timespan,
            metric_name="graylog_diff",
            levels_upper=params["msgs_diff_upper"],
            levels_lower=params["msgs_diff_lower"],
            label=f"Total number of messages in the last {render.timespan(item_data.timespan)}",
            render_func=str,
        )


def check_graylog_sources(
    item: str, params: GraylogMessagesParams, section: SourceInfoSection
) -> CheckResult:
    if (item_data := section.get(item)) is None:
        return

    if item_data.num_messages is None:
        return

    yield from _handle_graylog_sources_messages(item_data.num_messages, item_data, params)


agent_section_graylog_sources = AgentSection(
    name="graylog_sources",
    parse_function=parse_graylog_sources,
)


check_plugin_graylog_sources = CheckPlugin(
    name="graylog_sources",
    service_name="Graylog Source %s",
    discovery_function=discover_graylog_sources,
    check_function=check_graylog_sources,
    check_ruleset_name="graylog_sources",
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
