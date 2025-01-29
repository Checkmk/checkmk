#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.lib.bluecat import (
    check_bluecat_operational_state,
    CHECK_DEFAULT_PARAMETERS,
    cluster_check_bluecat_operational_state,
    ClusterSection,
    DETECT_BLUECAT,
    parse_bluecat,
    Section,
)

snmp_section_bluecat_dns = SimpleSNMPSection(
    name="bluecat_dns",
    parse_function=parse_bluecat,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.2.2.1",
        oids=[
            "1",  # DnsSerOperState
        ],
    ),
    detect=DETECT_BLUECAT,
)


def discover_bluecat_dns(section: Section) -> DiscoveryResult:
    """
    >>> list(discover_bluecat_dns({'oper_state': 1}))
    [Service()]
    """
    yield Service()


def check_bluecat_dns(
    params: Mapping[str, object],
    section: Section,
) -> CheckResult:
    yield from check_bluecat_operational_state(
        params,
        section,
    )


def cluster_check_bluecat_dns(
    params: Mapping[str, object],
    section: ClusterSection,
) -> CheckResult:
    yield from cluster_check_bluecat_operational_state(
        params,
        section,
    )


check_plugin_bluecat_dns = CheckPlugin(
    name="bluecat_dns",
    service_name="DNS",
    discovery_function=discover_bluecat_dns,
    check_ruleset_name="bluecat_dns",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_bluecat_dns,
    cluster_check_function=cluster_check_bluecat_dns,
)
