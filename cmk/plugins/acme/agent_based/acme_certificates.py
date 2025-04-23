#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.acme.agent_based.lib import DETECT_ACME


class CheckParamT(TypedDict):
    expire_lower: LevelsT


Section = dict[str, tuple[str, str, str]]


# .1.3.6.1.4.1.9148.3.9.1.10.1.3.65.1 rootca
# .1.3.6.1.4.1.9148.3.9.1.10.1.5.65.1 Jul 25 00:33:17 2003 GMT
# .1.3.6.1.4.1.9148.3.9.1.10.1.6.65.1 Aug 17 05:19:39 2027 GMT
# .1.3.6.1.4.1.9148.3.9.1.10.1.7.65.1 /C=US/O=Avaya Inc./OU=SIP Product Certificate Authority/CN=SIP Product Certificate Authority


def parse_acme_certificates(string_table: StringTable) -> Section | None:
    section: Section = {}
    for name, start, expire, issuer in string_table:
        section[name] = (start, expire, issuer)
    return section or None


def discover_acme_certificates(section: Section) -> DiscoveryResult:
    if section:
        yield from [Service(item=name) for name in section]


def check_acme_certificates(item: str, params: CheckParamT, section: Section) -> CheckResult:
    start, expire, issuer = section[item]

    expire_date, _expire_tz = expire.rsplit(" ", 1)
    expire_time = time.mktime(time.strptime(expire_date, "%b %d %H:%M:%S %Y"))

    now = time.time()
    time_diff = expire_time - now

    yield from check_levels(
        time_diff,
        levels_lower=params["expire_lower"],
        metric_name="certificate_expiration_time",
        render_func=render.timespan,
    )


snmp_section_acme_certificates = SimpleSNMPSection(
    name="acme_certificates",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.9.1.10.1",
        oids=["3", "5", "6", "7"],
    ),
    parse_function=parse_acme_certificates,
)

check_plugin_acme_certificates = CheckPlugin(
    name="acme_certificates",
    service_name="Certificate %s",
    discovery_function=discover_acme_certificates,
    check_function=check_acme_certificates,
    check_ruleset_name="acme_certificates",
    check_default_parameters=CheckParamT(
        expire_lower=("fixed", (604800.0, 2592000.0)),  # 1 week, 30 days, suggested by customer
    ),
)
