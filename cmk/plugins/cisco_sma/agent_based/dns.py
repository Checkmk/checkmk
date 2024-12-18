#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.cisco_sma.agent_based.detect import DETECT_CISCO_SMA_SNMP
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


@dataclass(frozen=True, kw_only=True)
class DNSRequests:
    pending: int
    outstanding: int


class Params(TypedDict):
    pending_dns_levels: SimpleLevelsConfigModel[int]
    outstanding_dns_levels: SimpleLevelsConfigModel[int]


def _check_dns_requests(params: Params, section: DNSRequests) -> CheckResult:
    yield from check_levels(
        section.pending,
        label="Pending",
        metric_name="pending_dns_requests",
        render_func=lambda x: str(int(x)),
        levels_upper=params["pending_dns_levels"],
    )
    yield from check_levels(
        section.outstanding,
        label="Outstanding",
        metric_name="outstanding_dns_requests",
        render_func=lambda x: str(int(x)),
        levels_upper=params["outstanding_dns_levels"],
    )


def _discover_dns_requests(section: DNSRequests) -> DiscoveryResult:
    yield Service()


check_plugin_dns_requests = CheckPlugin(
    name="cisco_sma_dns_requests",
    service_name="DNS Requests",
    discovery_function=_discover_dns_requests,
    check_function=_check_dns_requests,
    check_ruleset_name="cisco_sma_dns_requests",
    check_default_parameters={
        "pending_dns_levels": (
            "no_levels",
            None,
        ),
        "outstanding_dns_levels": (
            "no_levels",
            None,
        ),
    },
)


def _parse_dns_requests(string_table: StringTable) -> DNSRequests | None:
    if not string_table or not string_table[0]:
        return None
    return DNSRequests(
        outstanding=int(string_table[0][0]),
        pending=int(string_table[0][1]),
    )


snmp_section_dns_requests = SimpleSNMPSection(
    parsed_section_name="cisco_sma_dns_requests",
    name="cisco_sma_dns_requests",
    detect=DETECT_CISCO_SMA_SNMP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["15.0", "16.0"],
    ),
    parse_function=_parse_dns_requests,
)
