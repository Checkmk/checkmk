#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Dict, Tuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.k8s import Resources


def parse(string_table: StringTable) -> Resources:
    """Parses limit and requests values into Resources"""
    return Resources(**json.loads(string_table[0][0]))


def discovery(section: Resources) -> DiscoveryResult:
    yield Service()


def check(params: Dict[str, Tuple[int, int]], section: Resources) -> CheckResult:
    yield Result(state=State.OK, summary=f"Limit: {section.limit}")
    yield Result(state=State.OK, summary=f"Requests: {section.requests}")


# TODO: suggest a new name for section
register.agent_section(
    name="kube_cpu_resources_v1",
    parsed_section_name="kube_cpu_resources",
    parse_function=parse,
)

register.check_plugin(
    name="kube_cpu_resources",
    service_name="CPU Load",
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={},
)
