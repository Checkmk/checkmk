#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

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

# Output may have 11 fields:
# id:fc_io_port_id:port_id:type:port_speed:node_id:node_name:WWPN:nportid:status:attachment
# Example output from agent:
# <<<ibm_svc_portfc:sep(58)>>>
# 0:1:1:fc:8Gb:1:node1:5005076803042126:030400:active:switch
# 1:2:2:fc:8Gb:1:node1:5005076803082126:040400:active:switch
# 2:3:3:fc:N/A:1:node1:50050768030C2126:000000:inactive_unconfigured:none
# 3:4:4:fc:N/A:1:node1:5005076803102126:000000:inactive_unconfigured:none
# 8:1:1:fc:8Gb:2:node2:5005076803042127:030500:active:switch
# 9:2:2:fc:8Gb:2:node2:5005076803082127:040500:active:switch
# 10:3:3:fc:N/A:2:node2:50050768030C2127:000000:inactive_unconfigured:none
# 11:4:4:fc:N/A:2:node2:5005076803102127:000000:inactive_unconfigured:none
#
# Output may have 12 fields:
# id:fc_io_port_id:port_id:type:port_speed:node_id:node_name:WWPN:nportid:status:attachment:cluster_use
# Example output from agent:
# <<<ibm_svc_portfc:sep(58)>>>
# 0:1:1:fc:8Gb:1:node1:5005076803042126:030400:active:switch:local_partner
# 1:2:2:fc:8Gb:1:node1:5005076803082126:040400:active:switch:local_partner
# 2:3:3:fc:N/A:1:node1:50050768030C2126:000000:inactive_unconfigured:none:local_partner
# 3:4:4:fc:N/A:1:node1:5005076803102126:000000:inactive_unconfigured:none:local_partner
# 8:1:1:fc:8Gb:2:node2:5005076803042127:030500:active:switch:local_partner
# 9:2:2:fc:8Gb:2:node2:5005076803082127:040500:active:switch:local_partner
# 10:3:3:fc:N/A:2:node2:50050768030C2127:000000:inactive_unconfigured:none:local_partner
# 11:4:4:fc:N/A:2:node2:5005076803102127:000000:inactive_unconfigured:none:local_partner

Section = dict[str, Mapping[str, str]]


def parse_ibm_svc_portfc(string_table: StringTable) -> Section:
    dflt_header = [
        "id",
        "fc_io_port_id",
        "port_id",
        "type",
        "port_speed",
        "node_id",
        "node_name",
        "WWPN",
        "nportid",
        "status",
        "attachment",
        "cluster_use",
        "adapter_location",
        "adapter_port_id",
    ]
    parsed: Section = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        if "node_id" in data and "adapter_location" in data and "adapter_port_id" in data:
            item_name = f"Node {data['node_id']} Slot {data['adapter_location']} Port {data['adapter_port_id']}"
        else:
            item_name = f"Port {id_}"
        parsed.setdefault(item_name, data)
    return parsed


def discover_ibm_svc_portfc(section: Section) -> DiscoveryResult:
    for item_name, data in section.items():
        if data["status"] != "active":
            continue
        yield Service(item=item_name)


def check_ibm_svc_portfc(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    port_status = data["status"]
    infotext = f"Status: {port_status}, Speed: {data['port_speed']}, WWPN: {data['WWPN']}"

    yield Result(
        state=State.OK if port_status == "active" else State.CRIT,
        summary=infotext,
    )


agent_section_ibm_svc_portfc = AgentSection(
    name="ibm_svc_portfc",
    parse_function=parse_ibm_svc_portfc,
)


check_plugin_ibm_svc_portfc = CheckPlugin(
    name="ibm_svc_portfc",
    service_name="FC %s",
    discovery_function=discover_ibm_svc_portfc,
    check_function=check_ibm_svc_portfc,
)
