#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import PodLifeCycle


def parse_kube_pod_lifecycle(string_table: StringTable) -> PodLifeCycle:
    """
    >>> parse_kube_pod_lifecycle([['{"phase": "running"}']])
    PodLifeCycle(phase=<Phase.RUNNING: 'running'>)
    """
    return PodLifeCycle(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_pod_lifecycle_v1",
    parse_function=parse_kube_pod_lifecycle,
    parsed_section_name="kube_pod_lifecycle",
)


def discovery_kube_pod_phase(section: PodLifeCycle) -> DiscoveryResult:
    yield Service()


def check_kube_pod_phase(section: PodLifeCycle) -> CheckResult:
    yield Result(state=State.OK, summary=section.phase.title())


register.check_plugin(
    name="kube_pod_phase",
    service_name="Phase",
    sections=["kube_pod_lifecycle"],
    discovery_function=discovery_kube_pod_phase,
    check_function=check_kube_pod_phase,
)
