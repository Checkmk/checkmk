#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import CollectorLogs, CollectorState


def parse(string_table: StringTable) -> CollectorLogs:
    """
    >>> parse([[
    ... '{"logs": ['
    ... '{"status": "ok", '
    ... '"component": "Container Metrics", '
    ... '"message": "message", '
    ... '"detail": "detail"}]}'
    ... ]])
    CollectorLogs(logs=[CollectorLog(component='Container Metrics', status=<CollectorState.OK: 'ok'>, message='message', detail='detail')])

    """
    return CollectorLogs(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_collector_connection_v1",
    parsed_section_name="kube_collector_connection",
    parse_function=parse,
)


def discover(section: CollectorLogs) -> DiscoveryResult:
    yield Service()


def check(section: CollectorLogs) -> CheckResult:
    for entry in section.logs:
        if entry.status == CollectorState.OK:
            yield Result(state=State.OK, summary=f"{entry.component}: OK")
            continue

        component_message = f"{entry.component}: {entry.message}"
        detail_message = f" ({entry.detail})" if entry.detail else ""
        yield Result(
            state=State.OK if entry.status == CollectorState.OK else State.CRIT,
            summary=component_message,
            details=f"{component_message}{detail_message}",
        )


register.check_plugin(
    name="kube_collector_connection",
    service_name="Cluster Collector",
    discovery_function=discover,
    check_function=check,
)
