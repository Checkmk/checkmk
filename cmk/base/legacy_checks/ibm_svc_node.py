#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

# Example output from agent:
# Put here the example output from your TCP-Based agent. If the
# check is SNMP-Based, then remove this section

# newer agent output with more columns
# 1:N1_164191:10001AA202:500507680100D7CA:online:0:io_grp0:no:2040000051442002:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n1164191::164191:::::
# 2:N2_164373:10001AA259:500507680100D874:online:0:io_grp0:no:2040000051442149:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n2164373::164373:::::
# 5:N3_162711:100025E317:500507680100D0A7:online:1:io_grp1:no:2040000085543047:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n3162711::162711:::::
# 6:N4_164312:100025E315:500507680100D880:online:1:io_grp1:yes:2040000085543045:CG8:iqn.1986-03.com.ibm:2145.svc-cl.n4164312::164312:::::


def parse_ibm_svc_node(string_table):
    dflt_header = [
        "id",
        "name",
        "UPS_serial_number",
        "WWNN",
        "status",
        "IO_group_id",
        "IO_group_name",
        "config_node",
        "UPS_unique_id",
        "hardware",
        "iscsi_name",
        "iscsi_alias",
        "panel_name",
        "enclosure_id",
        "canister_id",
        "enclosure_serial_number",
        "site_id",
        "site_name",
    ]
    parsed = {}
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        for data in rows:
            parsed.setdefault(data["IO_group_name"], []).append(data)
    return parsed


def check_ibm_svc_node(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    messages = []
    status = 0
    online_nodes = 0
    nodes_of_iogroup = 0

    for row in data:
        node_status = row["status"]
        messages.append("Node {} is {}".format(row["name"], node_status))
        nodes_of_iogroup += 1
        if node_status == "online":
            online_nodes += 1

    if nodes_of_iogroup == 0:
        yield 3, "IO Group %s not found in agent output" % item
        return

    if nodes_of_iogroup == online_nodes:
        status = 0
    elif online_nodes == 0:
        status = 2
    else:
        status = 1

    # sorted is needed for deterministic test results
    yield status, ", ".join(sorted(messages))


def discover_ibm_svc_node(section):
    yield from ((item, {}) for item in section)


check_info["ibm_svc_node"] = LegacyCheckDefinition(
    name="ibm_svc_node",
    parse_function=parse_ibm_svc_node,
    service_name="IO Group %s",
    discovery_function=discover_ibm_svc_node,
    check_function=check_ibm_svc_node,
)
