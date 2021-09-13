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
)


def discover_cmciii_access(params: DiscoveryParams, section: Section) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("access", params, section)


def check_cmciii_access(item: str, params: CheckParams, section: Section) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["access"])
    if not entry:
        return

    state_readable = entry["Status"]
    if state_readable == "Closed":
        state = State.OK
    elif state_readable == "Open":
        state = State.WARN
    else:
        state = State.CRIT

    yield Result(state=state, summary="%s: %s" % (entry["DescName"], state_readable))
    yield Result(state=State.OK, summary="Delay: %s" % entry["Delay"])
    yield Result(state=State.OK, summary="Sensitivity: %s" % entry["Sensitivity"])


register.check_plugin(
    name="cmciii_access",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_access,
    check_function=check_cmciii_access,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
