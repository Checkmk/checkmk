#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP-Cluster Config Sync - SNMP sections and Checks
"""
from typing import Optional

from .agent_based_api.v1 import (
    SNMPTree,
    register,
    all_of,
)
from .agent_based_api.v1.type_defs import SNMPStringTable

from .utils.f5_bigip import (
    F5_BIGIP,
    VERSION_V11_2_PLUS,
    F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS,
)
from .f5_bigip_cluster_status import (
    check_f5_bigip_cluster_status_v11_2,
    cluster_check_f5_bigip_cluster_status_v11_2,
    discover_f5_bigip_cluster_status,
)

NodeState = int


def parse_f5_bigip_vcmpfailover(string_table: SNMPStringTable) -> Optional[NodeState]:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_vcmpfailover([[["0", "4"]]])
    4
    """
    # .1.3.6.1.4.1.3375.2.1.13.1.1.0 0 # sysVcmpNumber
    # .1.3.6.1.4.1.3375.2.1.14.1.1.0 3 # sysCmFailoverStatusId
    count, status = string_table[0][0]
    if int(count) == 0:
        return NodeState(status)
    # do nothing if we're at a vCMP-/Host/
    return None


register.snmp_section(
    name="f5_bigip_vcmpfailover",
    detect=all_of(F5_BIGIP, VERSION_V11_2_PLUS),
    parse_function=parse_f5_bigip_vcmpfailover,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1",
            oids=[
                "13.1.1.0",  # sysVcmpNumber
                "14.3.1.0",  # sysCmFailoverStatusId
            ]),
    ],
)

register.check_plugin(
    name="f5_bigip_vcmpfailover",  # name taken from pre-1.7 plugin
    service_name="BIG-IP vCMP Guest Failover Status",
    discovery_function=discover_f5_bigip_cluster_status,
    check_default_parameters=F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cluster_status",
    check_function=check_f5_bigip_cluster_status_v11_2,
    cluster_check_function=cluster_check_f5_bigip_cluster_status_v11_2,
)
