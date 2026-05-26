#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.graylog.lib import deserialize_and_merge_json, handle_graylog_messages

check_info = {}

# <<<graylog_messages>>>
# {"events": 1268586}


def discover_graylog_messages(parsed):
    events = parsed.get("events")
    if events is not None:
        return [(None, {})]
    return []


def check_graylog_messages(_no_item, params, parsed):
    messages = parsed.get("events")
    if messages is None:
        return None

    return handle_graylog_messages(messages, params, include_diff=True)


check_info["graylog_messages"] = LegacyCheckDefinition(
    name="graylog_messages",
    parse_function=deserialize_and_merge_json,
    service_name="Graylog Messages",
    discovery_function=discover_graylog_messages,
    check_function=check_graylog_messages,
    check_ruleset_name="graylog_messages",
)
