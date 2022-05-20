#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mobileiron import SourceHostSection


def check_mobileiron_sourcehost(section: SourceHostSection) -> CheckResult:

    yield Result(
        state=State.OK,
        summary=f"Query Time: {section.query_time}",
    )

    yield Result(
        state=State.OK,
        summary=f"Total number of returned devices: {section.total_count}",
    )


def discover_single(section: SourceHostSection) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="mobileiron_sourcehost",
    sections=["mobileiron_source_host"],
    service_name="Mobileiron source host",
    discovery_function=discover_single,
    check_function=check_mobileiron_sourcehost,
)
