#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json, handle_graylog_messages

Section = dict[str, Any]

# <<<graylog_messages>>>
# {"events": 1268586}


def discover_graylog_messages(section: Section) -> DiscoveryResult:
    if section.get("events") is not None:
        yield Service()


def check_graylog_messages(params: Mapping[str, Any], section: Section) -> CheckResult:
    messages = section.get("events")
    if messages is None:
        return

    yield from handle_graylog_messages(messages, params, include_diff=True)


def _get_value_diff(diff_name: str, svc_value: float, timespan: float) -> float:
    this_time = time.time()
    value_store = get_value_store()

    if (old_state := value_store.get(diff_name)) is None:
        value_store[diff_name] = this_time, svc_value
        return 0

    last_time, last_val = old_state
    timedif = max(this_time - last_time, 0)
    if timedif < float(timespan):
        return float(svc_value - last_val)
    value_store[diff_name] = this_time, svc_value
    return 0


agent_section_graylog_messages = AgentSection(
    name="graylog_messages",
    parse_function=deserialize_and_merge_json,
)


check_plugin_graylog_messages = CheckPlugin(
    name="graylog_messages",
    service_name="Graylog Messages",
    discovery_function=discover_graylog_messages,
    check_function=check_graylog_messages,
    check_ruleset_name="graylog_messages",
    check_default_parameters={},
)
