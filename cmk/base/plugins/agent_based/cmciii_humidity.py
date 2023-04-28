#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
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
from .utils.humidity import check_humidity


def discover_cmciii_humidity(
    params: DiscoveryParams, section: Section
) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("humidity", params, section)


def check_cmciii_humidity(
    item: str, params: CheckParams, section: Section
) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["humidity"])
    if not entry:
        return

    state_readable = entry["Status"]
    state = State.OK if state_readable == "OK" else State.CRIT
    yield Result(state=state, summary="Status: %s" % state_readable)
    yield from check_humidity(entry["Value"], params)


register.check_plugin(
    name="cmciii_humidity",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_humidity,
    check_function=check_cmciii_humidity,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
    check_ruleset_name="humidity",
)
