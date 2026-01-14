#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# netappFiler(1)
# netappClusteredFiler(3)
#                sysStat(2) cf(3)     cfSettings(1)
#                                     cfState(2)
#                                     cfCannotTakeoverCause(3)
#                                     cfPartnerStatus(4)
#                                     cfPartnerName(6)
#                                     cfInterconnectStatus(8)
# SNMPv2-SMI::enterprises.789.1.2.3.1.0 = INTEGER: 2
# SNMPv2-SMI::enterprises.789.1.2.3.2.0 = INTEGER: 2
# SNMPv2-SMI::enterprises.789.1.2.3.3.0 = INTEGER: 1
# SNMPv2-SMI::enterprises.789.1.2.3.4.0 = INTEGER: 2
# SNMPv2-SMI::enterprises.789.1.2.3.6.0 = STRING: "ZMUCFB"
# SNMPv2-SMI::enterprises.789.1.2.3.8.0 = INTEGER: 4


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, SNMPTree, startswith, StringTable

check_info = {}


def discover_netapp_cluster(info):
    inventory = []
    if info:
        (
            cfSettings,
            _cfState,
            _cfCannotTakeoverCause,
            _cfPartnerStatus,
            cfPartnerName,
            _cfInterconnectStatus,
        ) = info[0]
        # only inventorizes clusters that dont have takeover disabled.
        if int(cfSettings) not in [1, 3]:
            # Include the cluster partner name in inventory (value added data)
            inventory.append((cfPartnerName, None))
        return inventory
    return []


def check_netapp_cluster(item, _no_params, info):
    (
        cfSettings,
        cfState,
        cfCannotTakeoverCause,
        cfPartnerStatus,
        cfPartnerName,
        cfInterconnectStatus,
    ) = info[0]

    # first handle all critical states.
    # "dead" and "thisNodeDead"
    if cfState == "1" or cfSettings == "5":
        return (2, "Node is declared dead by cluster")
    if cfPartnerStatus in [1, 3]:
        return (2, "Partner Status is dead or maybeDown")
    if cfInterconnectStatus == "2":
        return (2, "Cluster Interconnect failure")

    # then handle warnings.
    if cfSettings in [3, 4] or cfState == "3":
        return (1, "Cluster takeover is disabled")
    if cfInterconnectStatus == "partialFailure":
        return (1, "Cluster interconnect partially failed")

    # if the partner name has changed, we'd like to issue a warning
    if cfPartnerName != item:
        return 1, f"Partner Name {cfPartnerName} instead of {item}"

    # OK - Cluster enabled, Cluster can takeover and the partner is OK and the
    # infiniband interconnect is working.
    if all(
        (
            cfSettings == "2",
            cfState == "2",
            cfCannotTakeoverCause == "1",
            cfPartnerStatus == "2",
            cfInterconnectStatus == "4",
        )
    ):
        return (0, "Cluster Status is OK")

    # if we reach here, we hit an unknown case.
    return (3, "Got unhandled information")


def parse_netapp_cluster(string_table: StringTable) -> StringTable:
    return string_table


check_info["netapp_cluster"] = LegacyCheckDefinition(
    name="netapp_cluster",
    parse_function=parse_netapp_cluster,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "netapp release"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.2.3",
        oids=["1", "2", "3", "4", "6", "8"],
    ),
    service_name="metrocluster_w_%s",
    discovery_function=discover_netapp_cluster,
    check_function=check_netapp_cluster,
)
