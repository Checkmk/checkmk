#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from dataclasses import dataclass
from typing import Container, Iterable, Mapping, TypedDict

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class DiscoveryParams(TypedDict):
    states_discover: Container[str]


class CheckParams(TypedDict):
    state_mapping: Mapping[str, int]
    tags_to_show: Iterable[str]


@dataclass
class Monitor:
    state: str
    message: str
    thresholds: Mapping[str, float]
    tags: Iterable[str]


Section = Mapping[str, Monitor]

_DEFAULT_DATADOG_AND_CHECKMK_STATES = (
    ("Alert", 2),
    ("Ignored", 3),
    ("No Data", 0),
    ("OK", 0),
    ("Skipped", 3),
    ("Unknown", 3),
    ("Warn", 1),
)


def parse_datadog_monitors(string_table: StringTable) -> Section:
    return {
        monitor_dict["name"]: Monitor(
            state=monitor_dict["overall_state"],
            message=monitor_dict["message"],
            thresholds=monitor_dict.get("options", {},).get(
                "thresholds",
                {},
            ),
            tags=monitor_dict.get(
                "tags",
                [],
            ),
        )  #
        for line in string_table  #
        for monitor_dict in [json.loads(line[0])]
    }


register.agent_section(
    name="datadog_monitors",
    parse_function=parse_datadog_monitors,
)


def discover_datadog_monitors(
    params: DiscoveryParams,
    section: Section,
) -> DiscoveryResult:
    yield from (
        Service(item=name)
        for name, monitor in section.items()
        if monitor.state in params["states_discover"]
    )


def check_datadog_monitors(
    item: str,
    params: CheckParams,
    section: Section,
) -> CheckResult:
    if not (monitor := section.get(item)):
        return
    yield Result(
        state=State(
            params["state_mapping"].get(
                monitor.state,
                State.UNKNOWN,
            )
        ),
        summary=f"Overall state: {monitor.state}",
        details=monitor.message,
    )
    if datadog_thresholds := ", ".join(f"{k}: {v}" for k, v in sorted(monitor.thresholds.items())):
        yield Result(
            state=State.OK,
            summary=f"Datadog thresholds: {datadog_thresholds}",
        )
    if datadog_tags := ", ".join(  #
        tag
        for tag in monitor.tags  #
        if any(re.match(tag_regex, tag) for tag_regex in params["tags_to_show"])
    ):
        yield Result(
            state=State.OK,
            summary=f"Datadog tags: {datadog_tags}",
        )


register.check_plugin(
    name="datadog_monitors",
    service_name="Datadog Monitor %s",
    discovery_function=discover_datadog_monitors,
    discovery_default_parameters={
        "states_discover": [
            datadog_state for datadog_state, _checkmk_state in _DEFAULT_DATADOG_AND_CHECKMK_STATES
        ],
    },
    discovery_ruleset_name="datadog_monitors_discovery",
    check_function=check_datadog_monitors,
    check_default_parameters={
        "tags_to_show": [],
        "state_mapping": dict(_DEFAULT_DATADOG_AND_CHECKMK_STATES),
    },
    check_ruleset_name="datadog_monitors_check",
)
