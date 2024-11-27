#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import collections
from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.lib import ucs_bladecenter

check_info = {}


def check_ucs_c_rack_server_faultinst(
    _item: None,
    _params: dict,
    parsed: dict[str, list[str]],
) -> Iterable[tuple[int, str]]:
    if not parsed:
        yield 0, "No fault instances found"
        return

    states = [
        ucs_bladecenter.UCS_FAULTINST_SEVERITY_TO_STATE.get(severity, 3)
        for severity in parsed["Severity"]
    ]
    if 2 in states:
        overall_state = 2
    else:
        overall_state = max(states)

    # report overall state and summary of fault instances
    severity_counter = collections.Counter(parsed["Severity"])
    yield (
        overall_state,
        "Found faults: "
        + ", ".join(
            [
                f"{severity_counter[severity]} with severity '{severity}'"
                for severity in sorted(severity_counter.keys())
            ]
        ),
    )

    # report individual faults sorted by monitoring state
    start_str = "\n\nIndividual faults:\n"
    for index in sorted(range(len(states)), key=lambda idx: states[idx]):
        yield (
            states[index],
            start_str
            + ", ".join(
                [
                    f"{key}: {parsed[key][index]}"
                    for key in ["Severity", "Description", "Cause", "Code", "Affected DN"]
                ]
            ),
        )
        start_str = ""


def discover_ucs_c_rack_server_faultinst(p):
    return [(None, {})]


check_info["ucs_c_rack_server_faultinst"] = LegacyCheckDefinition(
    name="ucs_c_rack_server_faultinst",
    service_name="Fault Instances Rack",
    discovery_function=discover_ucs_c_rack_server_faultinst,
    check_function=check_ucs_c_rack_server_faultinst,
)
