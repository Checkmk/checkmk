#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, Result, State, type_defs
from .utils.cmciii import (
    DiscoveryParams,
    CheckParams,
    discover_cmciii_sensors,
    get_sensor,
    discovery_default_parameters,
    Section,
)


def discover_cmciii_io(params: DiscoveryParams, section: Section) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("io", params, section)


def check_cmciii_io(item: str, params: CheckParams, section: Section) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["io"])
    if not entry:
        return

    state_readable = entry["Status"]

    summary = "Status: %s" % state_readable
    for key in ["Logic", "Delay", "Relay"]:
        if key in entry:
            summary += ", %s: %s" % (key, entry[key])

    if state_readable in ["Open", "Closed"]:
        # Some door sensors have been mapped to Input instead of Access
        # by the vendor
        yield Result(state=State({"Open": 1, "Closed": 0}[state_readable]), summary=summary)
        return

    if "Relay" in entry:
        if state_readable == "OK":
            yield Result(state=State.OK, summary=summary)
            return
        yield Result(state=State.CRIT, summary=summary)
        return

    if state_readable in ["OK", "Off"]:
        yield Result(state=State.OK, summary=summary)
        return

    if state_readable == "On":
        yield Result(state=State.WARN, summary=summary)
        return

    yield Result(state=State.CRIT, summary=summary)


register.check_plugin(
    name="cmciii_io",
    sections=['cmciii'],
    service_name="%s",
    discovery_function=discover_cmciii_io,
    check_function=check_cmciii_io,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
