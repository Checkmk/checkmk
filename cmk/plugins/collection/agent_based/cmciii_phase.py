#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, RuleSetType
from cmk.plugins.lib.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)
from cmk.plugins.lib.elphase import check_elphase


def discover_cmciii_phase(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    yield from discover_cmciii_sensors("phase", params, section)


def check_cmciii_phase(item: str, params: CheckParams, section: Section) -> CheckResult:
    sensor = get_sensor(item, params, section["phase"])
    if not sensor:
        return
    yield from check_elphase(item, params, {item: sensor})


check_plugin_cmciii_phase = CheckPlugin(
    name="cmciii_phase",
    sections=["cmciii"],
    service_name="Input %s",
    discovery_function=discover_cmciii_phase,
    check_function=check_cmciii_phase,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
    check_ruleset_name="el_inphase",
)
