#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"


# mypy: disable-error-code="arg-type"

import json
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable
from cmk.base.check_legacy_includes.graylog import handle_graylog_messages

check_info = {}

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
        sources_data = json.loads(line[0])

        source_name = sources_data.get("sources")
        if source_name is None:
            continue

        for name, data in source_name.items():
            parsed.setdefault(
                name,
                SourceInfo(
                    num_messages=data.get("messages"),
                    has_since_argument=data["has_since_argument"],
                    timespan=data.get("source_since"),
                    num_messages_in_timespan=data.get("messages_since", 0),
                ),
            )

    return parsed


def _handle_graylog_sources_messages(item_data: SourceInfo, params: Mapping[str, Any]) -> Iterable:
    total_messages, average_messages, total_new_messages = handle_graylog_messages(
        item_data.num_messages, params
    )

    if not item_data.has_since_argument:
        yield from (total_messages, average_messages, total_new_messages)
        return

    yield total_messages
    yield average_messages
    yield check_levels(
        item_data.num_messages_in_timespan,
        "graylog_diff",
        params.get("msgs_diff_upper", (None, None)) + params.get("msgs_diff_lower", (None, None)),
        infoname=f"Total number of messages in the last {render.timespan(item_data.timespan)}",
        human_readable_func=int,
    )


def check_graylog_sources(
    item: str, params: Mapping[str, Any], section: SourceInfoSection
) -> Iterable:
    if (item_data := section.get(item)) is None:
        return

    if item_data.num_messages is None:
        return

    yield from _handle_graylog_sources_messages(item_data, params)


def discover_graylog_sources(section: SourceInfoSection) -> Iterable[tuple[str, dict[str, Any]]]:
    yield from ((item, {}) for item in section)


check_info["graylog_sources"] = LegacyCheckDefinition(
    name="graylog_sources",
    parse_function=parse_graylog_sources,
    service_name="Graylog Source %s",
    discovery_function=discover_graylog_sources,
    check_function=check_graylog_sources,
    check_ruleset_name="graylog_sources",
    check_default_parameters={},
)
