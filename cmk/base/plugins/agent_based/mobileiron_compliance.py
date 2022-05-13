#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mobileiron import Section


def check_mobileiron_compliance(params: Mapping[str, Any], section: Section) -> CheckResult:

    count = section.policyViolationCount or 0
    yield from check_levels(
        label="Policy violation count",
        value=count,
        levels_upper=params.get("policy_violation_levels"),
        metric_name="mobileiron_policyviolationcount",
        render_func=lambda v: str(int(v)),
    )

    yield Result(
        state=State.OK if section.complianceState else State.CRIT,
        summary=f"Compliance state: {section.complianceState}",
    )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="mobileiron_compliance",
    sections=["mobileiron_section"],
    service_name="Mobileiron compliance",
    discovery_function=discover_single,
    check_function=check_mobileiron_compliance,
    check_ruleset_name="mobileiron_compliance",
    check_default_parameters={"policy_violation_levels": (2, 3)},
)
