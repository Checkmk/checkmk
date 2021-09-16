#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, Result, State, type_defs
from .utils.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
    Sensor,
)


def discover_cmciii_io(params: DiscoveryParams, section: Section) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("io", params, section)


def state(entry: Sensor) -> State:
    state_readable = entry["Status"]
    if state_readable == "Open":
        # Some door sensors have been mapped to Input instead of Access
        # by the vendor
        return State.WARN
    if state_readable == "Closed":
        return State.OK
    if "Relay" in entry:
        if state_readable == "OK":
            return State.OK
        return State.CRIT
    if state_readable in ["OK", "Off"]:
        return State.OK
    if state_readable == "On":
        return State.WARN
    return State.CRIT


def check_cmciii_io(item: str, params: CheckParams, section: Section) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["io"])
    if not entry:
        return

    yield Result(state=state(entry), summary="Status: %s" % entry["Status"])

    for key in ["Logic", "Delay", "Relay"]:
        if key in entry:
            yield Result(state=State.OK, summary="%s: %s" % (key, entry[key]))


register.check_plugin(
    name="cmciii_io",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_io,
    check_function=check_cmciii_io,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
