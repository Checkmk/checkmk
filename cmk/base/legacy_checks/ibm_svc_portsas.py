#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="var-annotated"

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

# Example agent output:
# <<<ibm_svc_portsas:sep(58)>>>
# 0:1:6Gb:1:node1:500507680305D3C0:online::host:host_controller:0:1
# 1:2:6Gb:1:node1:500507680309D3C0:online::host:host_controller:0:2
# 2:3:6Gb:1:node1:50050768030DD3C0:online::host:host_controller:0:3
# 3:4:6Gb:1:node1:500507680311D3C0:offline:500507680474F03F:none:enclosure:0:4
# 4:5:N/A:1:node1:500507680315D3C0:offline_unconfigured::none:host_controller:1:1
# 5:6:N/A:1:node1:500507680319D3C0:offline_unconfigured::none:host_controller:1:2
# 6:7:N/A:1:node1:50050768031DD3C0:offline_unconfigured::none:host_controller:1:3
# 7:8:N/A:1:node1:500507680321D3C0:offline_unconfigured::none:host_controller:1:4
# 8:1:6Gb:2:node2:500507680305D3C1:online::host:host_controller:0:1
# 9:2:6Gb:2:node2:500507680309D3C1:online::host:host_controller:0:2
# 10:3:6Gb:2:node2:50050768030DD3C1:online::host:host_controller:0:3
# 11:4:6Gb:2:node2:500507680311D3C1:offline:500507680474F07F:none:enclosure:0:4
# 12:5:N/A:2:node2:500507680315D3C1:offline_unconfigured::none:host_controller:1:1
# 13:6:N/A:2:node2:500507680319D3C1:offline_unconfigured::none:host_controller:1:2
# 14:7:N/A:2:node2:50050768031DD3C1:offline_unconfigured::none:host_controller:1:3
# 15:8:N/A:2:node2:500507680321D3C1:offline_unconfigured::none:host_controller:1:4

# the corresponding header line
# id:port_id:port_speed:node_id:node_name:WWPN:status:switch_WWPN:attachment:type:adapter_location:adapter_port_id


def parse_ibm_svc_portsas(
    string_table: Sequence[Sequence[str]],
) -> Mapping[str, Mapping[str, str]]:
    dflt_header = [
        "id",
        "port_id",
        "port_speed",
        "node_id",
        "node_name",
        "WWPN",
        "status",
        "switch_WWPN",
        "attachment",
        "type",
        "adapter_location",
        "adapter_port_id",
    ]
    parsed = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        if "node_id" in data and "adapter_location" in data and "adapter_port_id" in data:
            item_name = "Node {} Slot {} Port {}".format(
                data["node_id"],
                data["adapter_location"],
                data["adapter_port_id"],
            )
        else:
            item_name = "Port %s" % id_
        parsed.setdefault(item_name, data)
    return parsed


def discover_ibm_svc_portsas(
    parsed: Mapping[str, Mapping[str, str]],
) -> Iterable[tuple[str, dict[str, object]]]:
    for item_name, data in parsed.items():
        status = data["status"]
        if status == "offline_unconfigured":
            continue
        yield item_name, {"current_state": status}


def check_ibm_svc_portsas(
    item: str, params: Mapping[str, Any], parsed: Mapping[str, Mapping[str, str]]
) -> Iterable[tuple[int, str]]:
    if not (data := parsed.get(item)):
        return
    sasport_status = data["status"]

    infotext = "Status: %s" % sasport_status
    if sasport_status == params["current_state"]:
        state = 0
    else:
        state = 2

    infotext += ", Speed: {}, Type: {}".format(data["port_speed"], data["type"])

    yield state, infotext


check_info["ibm_svc_portsas"] = LegacyCheckDefinition(
    name="ibm_svc_portsas",
    parse_function=parse_ibm_svc_portsas,
    service_name="SAS %s",
    discovery_function=discover_ibm_svc_portsas,
    check_function=check_ibm_svc_portsas,
    check_default_parameters={
        "current_state": "offline",
    },
)
