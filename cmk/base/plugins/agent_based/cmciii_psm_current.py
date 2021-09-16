#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import Metric, register, Result, State, type_defs
from .utils.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)


def discover_cmciii_psm_current(
    params: DiscoveryParams, section: Section
) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("psm_current", params, section)


def check_cmciii_psm_current(
    item: str, params: CheckParams, section: Section
) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["psm_current"])
    if not entry:
        return

    current = entry["Value"]
    min_current = entry["SetPtHighAlarm"]
    max_current = entry["SetPtLowAlarm"]
    state = State.OK if entry["Status"] == "OK" else State.CRIT
    yield Result(state=state, summary="Current: %s (%s/%s), " % (current, min_current, max_current))
    yield Metric("current", current, levels=(min_current, max_current))

    yield Result(state=State.OK, summary="Type: %s" % entry["Unit Type"])
    yield Result(state=State.OK, summary="Serial: %s" % entry["Serial Number"])
    yield Result(state=State.OK, summary="Position: %s" % entry["Mounting Position"])


register.check_plugin(
    name="cmciii_psm_current",
    sections=["cmciii"],
    service_name="Current %s",
    discovery_function=discover_cmciii_psm_current,
    check_function=check_cmciii_psm_current,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
