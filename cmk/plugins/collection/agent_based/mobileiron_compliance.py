#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.lib.mobileiron import Section


def check_mobileiron_compliance(params: Mapping[str, Any], section: Section) -> CheckResult:
    count = section.policy_violation_count or 0
    yield from check_levels_v1(
        label="Policy violation count",
        value=count,
        levels_upper=params.get("policy_violation_levels"),
        metric_name="mobileiron_policyviolationcount",
        render_func=lambda v: str(int(v)),
    )

    if not params["ignore_compliance"]:
        yield Result(
            state=State.OK if section.compliance_state else State.CRIT,
            summary=f"Compliant: {section.compliance_state}",
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"Compliant: {section.compliance_state} (ignored)",
        )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


check_plugin_mobileiron_compliance = CheckPlugin(
    name="mobileiron_compliance",
    sections=["mobileiron_section"],
    service_name="Mobileiron compliance",
    discovery_function=discover_single,
    check_function=check_mobileiron_compliance,
    check_ruleset_name="mobileiron_compliance",
    check_default_parameters={"policy_violation_levels": (2, 3), "ignore_compliance": False},
)
