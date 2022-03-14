#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, type_defs
from .utils.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)
from .utils.elphase import check_elphase


def discover_cmciii_phase(params: DiscoveryParams, section: Section) -> type_defs.DiscoveryResult:
    yield from discover_cmciii_sensors("phase", params, section)


def check_cmciii_phase(item: str, params: CheckParams, section: Section) -> type_defs.CheckResult:
    sensor = get_sensor(item, params, section["phase"])
    if not sensor:
        return
    yield from check_elphase(item, params, {item: sensor})


register.check_plugin(
    name="cmciii_phase",
    sections=["cmciii"],
    service_name="Input %s",
    discovery_function=discover_cmciii_phase,
    check_function=check_cmciii_phase,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=register.RuleSetType.MERGED,
    check_default_parameters={},
    check_ruleset_name="el_inphase",
)
