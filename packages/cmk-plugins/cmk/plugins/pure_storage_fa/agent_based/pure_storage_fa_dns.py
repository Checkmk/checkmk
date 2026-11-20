#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import List
from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    Metric,
)


class DNSServer(BaseModel, frozen=True):
    domain: str
    dns_server: List[str]


def parse_dns(string_table: StringTable) -> DNSServer | None:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    return DNSServer(
        domain=json_data["items"][0]["domain"],
        dns_server=json_data["items"][0]["nameservers"],
    )


agent_section_pure_storage_fa_dns = AgentSection(
    name="pure_storage_fa_dns",
    parse_function=parse_dns,
)


def discover_dns(section: DNSServer) -> DiscoveryResult:
    if section is not None:
        yield Service()


def check_dns(section: DNSServer) -> CheckResult:
    if len(section.dns_server) == 0:
        yield Result(
            state=State.CRIT,
            summary=f"No DNS Server for Domain {section.domain} found!",
        )
        yield Metric("pure_storage_fa_dns", len(section.dns_server))
    else:
        yield from check_levels(
            len(section.dns_server),
            metric_name="pure_storage_fa_dns",
            render_func=lambda v: (
                f"{v} DNS Server in Domain {section.domain} found: {', '.join(section.dns_server)}"
            ),
        )


check_plugin_pure_storage_fa_dns = CheckPlugin(
    name="pure_storage_fa_dns",
    service_name="DNS Server",
    discovery_function=discover_dns,
    check_function=check_dns,
)
