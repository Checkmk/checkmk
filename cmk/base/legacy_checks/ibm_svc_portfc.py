#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

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


def parse_ibm_svc_portfc(string_table):
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


def discover_ibm_svc_portfc(parsed):
    for item_name, data in parsed.items():
        if data["status"] != "active":
            continue
        yield item_name, None


def check_ibm_svc_portfc(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    port_status = data["status"]
    infotext = "Status: {}, Speed: {}, WWPN: {}".format(
        port_status, data["port_speed"], data["WWPN"]
    )

    if port_status == "active":
        state = 0
    else:
        state = 2

    yield state, infotext


check_info["ibm_svc_portfc"] = LegacyCheckDefinition(
    name="ibm_svc_portfc",
    parse_function=parse_ibm_svc_portfc,
    service_name="FC %s",
    discovery_function=discover_ibm_svc_portfc,
    check_function=check_ibm_svc_portfc,
)
