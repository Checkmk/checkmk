#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<hyperv_vmstatus>>>
# Integration_Services Ok
# Replica_Health None


from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

Section = Mapping[str, str]


def parse_hyperv_vmstatus(string_table):
    return {line[0]: " ".join(line[1:]) for line in string_table}


def discover_hyperv_vmstatus(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_hyperv_vmstatus(_no_item, _no_params, parsed):
    int_state = parsed.get("Integration_Services")
    # According to microsoft 'Protocol_Mismatch' is OK:
    #   The secondary status [...] includes an error string that sounds alarming
    #   but that you can safely ignore. [...] This behavior is by design.
    state = 0 if int_state in ("Ok", "Protocol_Mismatch") else 2
    return state, "Integration Service State: %s" % int_state


check_info["hyperv_vmstatus"] = LegacyCheckDefinition(
    name="hyperv_vmstatus",
    parse_function=parse_hyperv_vmstatus,
    service_name="HyperV Status",
    discovery_function=discover_hyperv_vmstatus,
    check_function=check_hyperv_vmstatus,
)
