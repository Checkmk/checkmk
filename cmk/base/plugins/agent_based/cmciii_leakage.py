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


def discover_cmciii_leakage(params: DiscoveryParams, section: Section) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("leakage", params, section)


def check_cmciii_leakage(item: str, params: CheckParams, section: Section) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["leakage"])
    if not entry:
        return

    # We do not take entry["Position"] into account. It detects leaks but does
    # not account for the delay. The delay is the time after which the status
    # message changes.
    # The leakage status is a readable text for notAvail(1), ok(4), alarm(5),
    # probeOpen(24). All numeric values are defined in cmcIIIMsgStatus.
    status = entry["Status"]
    yield Result(state=State.CRIT if status != "OK" else State.OK, summary="Status: %s" % status)
    yield Result(state=State.OK, summary="Delay: %s" % entry["Delay"])


register.check_plugin(
    name="cmciii_leakage",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_leakage,
    check_function=check_cmciii_leakage,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
