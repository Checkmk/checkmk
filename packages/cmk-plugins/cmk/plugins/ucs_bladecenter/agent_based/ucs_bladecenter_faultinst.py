#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.ucs_bladecenter import lib as ucs_bladecenter

# <<<ucs_bladecenter_faultinst:sep(9)>>>
# faultInst   Dn sys/chassis-2/bl...ault-F1256 Descr Local disk 2 missing on server 2/3    Severity info
# faultInst   Dn sys/chassis-2/bl...ault-F1256 Descr Local disk 1 missing on server 2/3    Severity info
# faultInst   Dn sys/chassis-1/bl...ault-F1256 Descr Local disk 2 missing on server 1/3    Severity info


def discover_ucs_bladecenter_faultinst(section: ucs_bladecenter.GenericSection) -> DiscoveryResult:
    yield Service()


def check_ucs_bladecenter_faultinst(
    params: Mapping[str, Any],
    section: ucs_bladecenter.GenericSection,
) -> CheckResult:
    severities = dict[str, list[dict[str, str]]]()
    for values in section.get("faultInst", {}).values():
        entry_sev = values["Severity"].lower()
        severities.setdefault(entry_sev, [])
        severities[entry_sev].append(values)

    if not severities:
        yield Result(state=State.OK, summary="No fault instances found")
        return

    for sev, instances in severities.items():
        sev_state = params.get(sev)
        if sev_state is not None:
            sev_state = State(sev_state)
        else:
            sev_state = ucs_bladecenter.UCS_FAULTINST_SEVERITY_TO_STATE.get(sev, State.UNKNOWN)

        # Right now, OK instances are also reported in detail
        # If required we can increase the state level here, so that only WARN+ messages are shown
        if sev_state != State.OK:
            extra_info = []
            for instance in instances:
                extra_info.append("%s" % instance["Descr"])
            extra_info_str = ": " + ", ".join(extra_info)
        else:
            extra_info_str = ""

        yield Result(
            state=sev_state, summary=f"{len(instances)} {sev.upper()} Instances{extra_info_str}"
        )


agent_section_ucs_bladecenter_faultinst = AgentSection(
    name="ucs_bladecenter_faultinst",
    parse_function=ucs_bladecenter.generic_parse,
)

check_plugin_ucs_bladecenter_faultinst = CheckPlugin(
    name="ucs_bladecenter_faultinst",
    service_name="Fault Instances Blade",
    discovery_function=discover_ucs_bladecenter_faultinst,
    check_function=check_ucs_bladecenter_faultinst,
    check_ruleset_name="ucs_bladecenter_faultinst",
    check_default_parameters={},
)
