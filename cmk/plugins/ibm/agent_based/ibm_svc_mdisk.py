#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm.lib_svc import parse_ibm_svc_with_header

# Example output from agent:
# <<<ibm_svc_mdisk:sep(58)>>>
# 0:stp5_300G_01-01:online:managed:16:stp5_300G_01:1.1TB:0000000000000000:BLUBB5:600a0b80006e1dbc0000f6f9513026a000000000000000000000000000000000:generic_hdd
# 1:Quorum_BLUBB3:online:managed:0:Quorum_2:1.0GB:0000000000000000:BLUBB3:600a0b8000293eb800001f264c3e8a1f00000000000000000000000000000000:generic_hdd
# 2:stp6_300G_01-01:online:managed:15:stp6_300G_01:1.1TB:0000000000000000:BLUBB6:600a0b80006e8e3c00000f1651302b8800000000000000000000000000000000:generic_hdd
# 3:Quorum_blubb5:online:managed:18:Quorum_0:1.0GB:0000000000000001:BLUBB5:600a0b80006e1dcc0000f6905130225800000000000000000000000000000000:generic_hdd
# 4:Quorum_blubb6:online:managed:17:Quorum_1:1.0GB:0000000000000001:BLUBB6:600a0b80006e1d5e00000dcb5130228700000000000000000000000000000000:generic_hdd
# 5:stp5_300G_01-02:online:managed:16:stp5_300G_01:1.1TB:0000000000000002:BLUBB5:600a0b80006e1dbc0000f6fc51304bfc00000000000000000000000000000000:generic_hdd
# 6:stp6_300G_01-02:online:managed:15:stp6_300G_01:1.1TB:0000000000000002:BLUBB6:600a0b80006e8e3c00000f1951304f9a00000000000000000000000000000000:generic_hdd
# 7:stp5_300G_01-03:online:managed:16:stp5_300G_01:1.1TB:0000000000000003:BLUBB5:600a0b80006e1dcc0000f76951305bc000000000000000000000000000000000:generic_hdd
# 8:stp6_300G_01-03:online:managed:15:stp6_300G_01:1.1TB:0000000000000003:BLUBB6:600a0b80006e1d5e00000e9a51305a3200000000000000000000000000000000:generic_hdd
# 9:stp5_300G_01-04:online:managed:16:stp5_300G_01:1.1TB:0000000000000004:BLUBB5:600a0b80006e1dbc0000f7d051341cc000000000000000000000000000000000:generic_hdd


@dataclass(frozen=True)
class Mdisk:
    status: str
    mode: str


Section = Mapping[str, Mdisk]


class IbmSvcMdiskParams(TypedDict):
    online_state: State
    degraded_state: State
    offline_state: State
    excluded_state: State
    managed_mode: State
    array_mode: State
    image_mode: State
    unmanaged_mode: State


def parse_ibm_svc_mdisk(string_table: StringTable) -> Section:
    dflt_header = [
        "id",
        "name",
        "status",
        "mode",
        "mdisk_grp_id",
        "mdisk_grp_name",
        "capacity",
        "ctrl_LUN_#",
        "controller_name",
        "UID",
        "tier",
        "encrypt",
        "site_id",
        "site_name",
        "distributed",
        "dedupe",
    ]
    parsed: dict[str, Mdisk] = {}
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        try:
            data = rows[0]
            parsed.setdefault(data["name"], Mdisk(status=data["status"], mode=data["mode"]))
        except KeyError, IndexError:
            continue
    return parsed


def discover_ibm_svc_mdisk(section: Section) -> DiscoveryResult:
    yield from (Service(item=mdisk_name) for mdisk_name in section)


def check_ibm_svc_mdisk(item: str, params: IbmSvcMdiskParams, section: Section) -> CheckResult:
    if (mdisk := section.get(item)) is None:
        return

    # Unknown status/mode values default to WARN, matching the previous behavior.
    status_state = {
        "online": params["online_state"],
        "degraded": params["degraded_state"],
        "offline": params["offline_state"],
        "excluded": params["excluded_state"],
    }.get(mdisk.status, State.WARN)
    yield Result(state=State(status_state), summary=f"Status: {mdisk.status}")

    mode_state = {
        "managed": params["managed_mode"],
        "array": params["array_mode"],
        "image": params["image_mode"],
        "unmanaged": params["unmanaged_mode"],
    }.get(mdisk.mode, State.WARN)
    yield Result(state=State(mode_state), summary=f"Mode: {mdisk.mode}")


agent_section_ibm_svc_mdisk = AgentSection(
    name="ibm_svc_mdisk",
    parse_function=parse_ibm_svc_mdisk,
)


check_plugin_ibm_svc_mdisk = CheckPlugin(
    name="ibm_svc_mdisk",
    service_name="MDisk %s",
    discovery_function=discover_ibm_svc_mdisk,
    check_function=check_ibm_svc_mdisk,
    check_ruleset_name="ibm_svc_mdisk",
    check_default_parameters={
        "online_state": State.OK.value,
        "degraded_state": State.WARN.value,
        "offline_state": State.CRIT.value,
        "excluded_state": State.CRIT.value,
        "managed_mode": State.OK.value,
        "array_mode": State.OK.value,
        "image_mode": State.OK.value,
        "unmanaged_mode": State.WARN.value,
    },
)
