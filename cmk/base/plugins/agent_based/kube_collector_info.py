#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import (
    CollectorComponents,
    CollectorHandlerLog,
    CollectorState,
)


def parse(string_table: StringTable) -> CollectorComponents:
    return CollectorComponents(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_collector_info_v1",
    parsed_section_name="kube_collector_info",
    parse_function=parse,
)


def discover(section: CollectorComponents) -> DiscoveryResult:
    yield Service()


def _component_check(component: str, component_log: Optional[CollectorHandlerLog]):
    if component_log is None:
        return

    if component_log.status == CollectorState.OK:
        yield Result(state=State.OK, summary=f"{component}: OK")
        return

    component_message = f"{component}: {component_log.title}"
    detail_message = f"({component_log.detail})" if component_log.detail else ""
    yield Result(
        state=State.CRIT,
        summary=component_message,
        details=f"{component_message}{detail_message}",
    )


def check(section: CollectorComponents) -> CheckResult:
    yield from _component_check("Container Metrics", section.container)
    yield from _component_check("Machine Metrics", section.machine)


register.check_plugin(
    name="kube_collector_info",
    service_name="Cluster Collector",
    discovery_function=discover,
    check_function=check,
)
