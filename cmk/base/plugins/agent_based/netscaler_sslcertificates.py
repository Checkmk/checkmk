#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping

from .agent_based_api.v1 import check_levels, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.netscaler import SNMP_DETECT

# example SNMP output:
#
# .1.3.6.1.4.1.5951.4.1.1.56.1.1.1.20.67.79.77.79.68.79.95.82.83.65.95.67.101.114.116.95.65.117.116.104 COMODO_RSA_Cert_Auth
# .1.3.6.1.4.1.5951.4.1.1.56.1.1.1.21.110.115.45.115.101.114.118.101.114.45.99.101.114.116.105.102.105.99.97.116.101 ns-server-certificate
# .1.3.6.1.4.1.5951.4.1.1.56.1.1.1.25.67.79.77.79.68.79.95.82.83.65.95.67.101.114.116.95.65.117.116.104.95.82.111.111.116 COMODO_RSA_Cert_Auth_Root
# .1.3.6.1.4.1.5951.4.1.1.56.1.1.5.20.67.79.77.79.68.79.95.82.83.65.95.67.101.114.116.95.65.117.116.104 4286
# .1.3.6.1.4.1.5951.4.1.1.56.1.1.5.21.110.115.45.115.101.114.118.101.114.45.99.101.114.116.105.102.105.99.97.116.101 3655
# .1.3.6.1.4.1.5951.4.1.1.56.1.1.5.25.67.79.77.79.68.79.95.82.83.65.95.67.101.114.116.95.65.117.116.104.95.82.111.111.116 1106

Section = Mapping[str, int]


def parse_netscaler_sslcertificates(string_table: List[StringTable]) -> Section:
    """
    >>> parse_netscaler_sslcertificates([[['cert1', '3'], ['cert2', '100']]])
    {'cert1': 3, 'cert2': 100}
    """
    return {certname: int(daysleft) for certname, daysleft in string_table[0]}


register.snmp_section(
    name="netscaler_sslcertificates",
    parse_function=parse_netscaler_sslcertificates,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5951.4.1.1.56.1.1",
            oids=[
                "1",  # sslCertKeyName
                "5",  # sslDaysToExpire
            ],
        ),
    ],
    detect=SNMP_DETECT,
)


def discover_netscaler_sslcertificates(section: Section) -> DiscoveryResult:
    """
    >>> list(discover_netscaler_sslcertificates({'cert1': 3, 'cert2': 100, '': 4}))
    [Service(item='cert1'), Service(item='cert2')]
    """
    for certname in section:
        if certname:
            yield Service(item=certname)


def check_netscaler_sslcertificates(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if item not in section:
        return
    label = "certificate valid for"
    yield from check_levels(
        section[item],
        levels_lower=params["age_levels"],
        metric_name="daysleft",
        render_func=lambda d: str(d) + " days",
        label=label,
    )


register.check_plugin(
    name="netscaler_sslcertificates",
    service_name="SSL Certificate %s",
    discovery_function=discover_netscaler_sslcertificates,
    check_ruleset_name="netscaler_sslcerts",
    check_default_parameters={
        "age_levels": (30, 10),
    },
    check_function=check_netscaler_sslcertificates,
)
