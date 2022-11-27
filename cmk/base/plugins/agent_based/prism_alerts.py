#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
from datetime import datetime
from typing import Any, Dict, List, Mapping, Tuple

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.prism import load_json

Section = List[Dict[Any, Any]]
StringMap = Mapping[str, str]


def parse_prism_alerts(string_table: StringTable) -> Section:
    parsed = []
    data = load_json(string_table)

    for entity in data.get("entities", {}):
        full_context = dict(zip(entity["context_types"], entity["context_values"]))

        try:
            message = entity["message"].format(**full_context)
        except KeyError:
            message = entity["message"]

        full_context["timestamp"] = entity["created_time_stamp_in_usecs"]
        full_context["severity"] = entity["severity"]
        full_context["message"] = message

        parsed.append(full_context)

    return parsed


register.agent_section(
    name="prism_alerts",
    parse_function=parse_prism_alerts,
)


def severity(name: str) -> Tuple[int, int]:
    # first value is for sorting second is the nagios status codes
    return {
        "kInfo": (0, 0),
        "kWarning": (1, 1),
        "kCritical": (3, 2),
    }.get(name, (2, 3))


def discovery_prism_alerts(section: Section) -> DiscoveryResult:
    """We cannot guess items from alerts, since an empty list of alerts does not mean there are
    no items to monitor"""
    yield Service()


def to_string(timestamp: str) -> str:
    """Turn a textual timestamp in microseconds into a readable format"""
    return datetime.fromtimestamp(int(timestamp) // 1000000).strftime("%c")


def check_prism_alerts(params: StringMap, section: Section) -> CheckResult:
    valid_alerts = (
        [e for e in section if e.get("context", {}).get("vm_type") == "Prism Central VM"]  #
        if params.get("prism_central_only")
        else section
    )

    if not valid_alerts:
        yield Result(state=State.OK, summary="No alerts")
        return

    valid_alerts = sorted(valid_alerts, key=lambda d: d["timestamp"], reverse=True)
    # find the newest alert among those with the highest severity
    immediate_alert = max(valid_alerts, key=lambda x: (severity(x["severity"])[0], x["timestamp"]))

    yield Result(
        state=State(severity(immediate_alert["severity"])[1]),
        summary="%d alerts" % len(valid_alerts),
    )

    message = immediate_alert["message"]
    state = 1 if "has the following problems" in message else 0  # see werk #7203
    yield Result(
        state=State(state),
        summary="Last worst on %s: %r" % (to_string(immediate_alert["timestamp"]), message),
    )

    yield Result(state=State.OK, notice="\nLast 10 Alerts\n")
    for i in valid_alerts[:10]:
        yield Result(state=State.OK, notice="%s\t%s" % (to_string(i["timestamp"]), i["message"]))


register.check_plugin(
    name="prism_alerts",
    service_name="NTNX Alerts",
    discovery_function=discovery_prism_alerts,
    check_function=check_prism_alerts,
    check_ruleset_name="prism_alerts",
    check_default_parameters={
        "prism_central_only": False,
    },
)
