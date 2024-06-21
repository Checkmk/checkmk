#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, RuleSetType, State
from cmk.plugins.lib.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)


def discover_cmciii_status(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    yield from discover_cmciii_sensors("status", params, section)


def check_cmciii_status(item: str, params: CheckParams, section: Section) -> CheckResult:
    entry = get_sensor(item, params, section["status"])
    if not entry:
        return

    status = entry["Status"]
    yield Result(state=State.CRIT if status != "OK" else State.OK, summary="Status: %s" % status)


check_plugin_cmciii_status = CheckPlugin(
    name="cmciii_status",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_status,
    check_function=check_cmciii_status,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
)
