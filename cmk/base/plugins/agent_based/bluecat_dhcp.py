#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from .agent_based_api.v1 import register, Service, SNMPTree, type_defs
from .utils.bluecat import (
    check_bluecat_operational_state,
    CHECK_DEFAULT_PARAMETERS,
    cluster_check_bluecat_operational_state,
    ClusterSection,
    DETECT_BLUECAT,
    parse_bluecat,
    Section,
)

register.snmp_section(
    name="bluecat_dhcp",
    parse_function=parse_bluecat,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.1.2.1",
        oids=[
            "1",  # dhcpOperState
            "3",  # dhcpLeaseStatsSuccess
        ],
    ),
    detect=DETECT_BLUECAT,
)


def discover_bluecat_dhcp(section: Section) -> type_defs.DiscoveryResult:
    """
    >>> list(discover_bluecat_dhcp({'oper_state': 1, 'leases': 2}))
    [Service()]
    >>> list(discover_bluecat_dhcp({'oper_state': 2, 'leases': 2}))
    []
    """
    if section["oper_state"] != 2:
        yield Service()


def check_bluecat_dhcp(
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    yield from check_bluecat_operational_state(
        params,
        section,
    )


def cluster_check_bluecat_dhcp(
    params: Mapping[str, Any],
    section: ClusterSection,
) -> type_defs.CheckResult:
    yield from cluster_check_bluecat_operational_state(
        params,
        section,
    )


register.check_plugin(
    name="bluecat_dhcp",
    service_name="DHCP",
    discovery_function=discover_bluecat_dhcp,
    check_ruleset_name="bluecat_dhcp",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_bluecat_dhcp,
    cluster_check_function=cluster_check_bluecat_dhcp,
)
