#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
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

# <<<graylog_streams:sep(0)>>>
# {"total": 5, "streams": [{"remove_matches_from_default_stream": false,
# "is_default": false, "index_set_id": "5da58758e2847e0602771f2a",
# "description": "logins", "alert_conditions": [], "rules": [], "outputs": [],
# "created_at": "2019-10-21T11:32:54.371Z", "title": "Logins", "disabled":
# false, "content_pack": null, "matching_type": "AND", "creator_user_id":
# "admin", "alert_receivers": {"emails": [], "users": []}, "id":
# "5dad97665bc77407a731e7dc"}, {"remove_matches_from_default_stream": false,
# "is_default": false, "index_set_id": "5d64cceecaba8d12890fdf47",
# "description": "dfh", "alert_conditions": [], "rules": [], "outputs": [],
# "created_at": "2019-10-30T19:45:31.792Z", "title": "shsdfhg", "disabled":
# false, "content_pack": null, "matching_type": "AND", "creator_user_id":
# "admin", "alert_receivers": {"emails": [], "users": []}, "id":
# "5db9e85b9a74aa6ccbb8e1b0"}, {"remove_matches_from_default_stream": false,
# "is_default": true, "index_set_id": "5d64cceecaba8d12890fdf47",
# "description": "Stream containing all messages", "alert_conditions": [],
# "rules": [], "outputs": [], "created_at": "2019-08-27T06:25:50.570Z",
# "title": "All messages", "disabled": false, "content_pack": null,
# "matching_type": "AND", "creator_user_id": "local:admin", "alert_receivers":
# {"emails": [], "users": []}, "id": "000000000000000000000001"},
# {"remove_matches_from_default_stream": true, "is_default": false,
# "index_set_id": "5da58758e2847e0602771f28", "description": "Stream containing
# all events created by Graylog", "alert_conditions": [], "rules":
# [{"description": "", "stream_id": "000000000000000000000002", "value": ".*",
# "inverted": false, "field": ".*", "type": 2, "id":
# "5dad59d65bc77407a731a2fc"}], "outputs": [], "created_at":
# "2019-10-15T08:46:16.321Z", "title": "All events", "disabled": false,
# "content_pack": null, "matching_type": "AND", "creator_user_id": "admin",
# "alert_receivers": {"emails": [], "users": []}, "id":
# "000000000000000000000002"}, {"remove_matches_from_default_stream": true,
# "is_default": false, "index_set_id": "5da58758e2847e0602771f2a",
# "description": "Stream containing all system events created by Graylog",
# "alert_conditions": [], "rules": [], "outputs": [], "created_at":
# "2019-10-15T08:46:16.327Z", "title": "All system events", "disabled": false,
# "content_pack": null, "matching_type": "AND", "creator_user_id": "admin",
# "alert_receivers": {"emails": [], "users": []}, "id":
# "000000000000000000000003"}]}

Section = Mapping


def parse_graylog_streams(string_table: StringTable) -> Section:
    section: dict = {}

    for (word,) in string_table:
        streams = json.loads(word)

        stream_data = streams.get("streams")
        if stream_data is None:
            continue

        for stream in stream_data:
            stream_title = stream.get("title")
            if stream_title is None:
                continue

            section.setdefault(
                stream_title,
                {
                    "disabled": stream.get("disabled", False),
                    "is_default": stream.get("is_default", False),
                },
            )

    return section


def discovery_graylog_streams(section: Section) -> DiscoveryResult:
    yield Service()


def check_graylog_streams(params: Mapping, section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.WARN, summary="Number of streams: 0")
        return

    yield from check_levels_v1(
        len(section),
        metric_name="num_streams",
        levels_lower=params.get("stream_count_lower"),
        levels_upper=params.get("stream_count_upper"),
        render_func=str,
        label="Number of streams",
    )

    for stream, values in sorted(section.items()):
        if values["is_default"]:
            yield Result(state=State.OK, summary=f"Stream: {stream} (default)")
        elif values["disabled"]:
            yield Result(
                state=State(params["stream_disabled"]),
                notice=f"Stream: {stream} (disabled)",
            )
        else:
            yield Result(state=State.OK, notice=f"Stream: {stream}")


agent_section_graylog_streams = AgentSection(
    name="graylog_streams",
    parse_function=parse_graylog_streams,
)


check_plugin_graylog_streams = CheckPlugin(
    name="graylog_streams",
    service_name="Graylog Streams",
    discovery_function=discovery_graylog_streams,
    check_function=check_graylog_streams,
    check_default_parameters={
        "stream_disabled": 1,
    },
    check_ruleset_name="graylog_streams",
)
