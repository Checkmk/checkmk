#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.couchbase import parse_couchbase_lines


def discover_couchbase_nodes_services(section: Any) -> DiscoveryResult:
    for key, data in section.items():
        yield Service(item=key, parameters={"discovered_services": data.get("services", [])})


def check_couchbase_nodes_services(
    item: str, params: Mapping[str, Any], section: Any
) -> CheckResult:
    if not (data := section.get(item)):
        return
    services_present = set(data.get("services", []))
    services_discovered = set(params["discovered_services"])

    services_appeared = services_present - services_discovered
    services_vanished = services_discovered - services_present
    services_unchanged = services_discovered & services_present

    if services_vanished:
        srt = sorted(services_vanished)
        yield Result(
            state=State.CRIT, summary="%d services vanished: %s" % (len(srt), ", ".join(srt))
        )
    if services_appeared:
        srt = sorted(services_appeared)
        yield Result(
            state=State.CRIT, summary="%d services appeared: %s" % (len(srt), ", ".join(srt))
        )

    srt = sorted(services_unchanged)
    yield Result(state=State.OK, summary="%d services unchanged: %s" % (len(srt), ", ".join(srt)))


agent_section_couchbase_nodes_services = AgentSection(
    name="couchbase_nodes_services", parse_function=parse_couchbase_lines
)

check_plugin_couchbase_nodes_services = CheckPlugin(
    name="couchbase_nodes_services",
    service_name="Couchbase %s Services",
    discovery_function=discover_couchbase_nodes_services,
    check_function=check_couchbase_nodes_services,
    check_default_parameters={},
)
