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


def discover_cmciii_psm_plugs(
    params: DiscoveryParams, section: Section
) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("psm_plugs", params, section)


def check_cmciii_psm_plugs(
    item: str, params: CheckParams, section: Section
) -> type_defs.CheckResult:
    entry = get_sensor(item, params, section["psm_plugs"])
    if not entry:
        return

    state_readable = entry["Status"]
    state = State.OK if state_readable == "OK" else State.CRIT
    yield Result(state=state, summary="Status: %s" % state_readable)


register.check_plugin(
    name="cmciii_psm_plugs",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_psm_plugs,
    check_function=check_cmciii_psm_plugs,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
)
