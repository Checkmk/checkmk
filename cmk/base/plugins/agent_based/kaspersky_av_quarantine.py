#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<kaspersky_av_quarantine:sep(58)>>>
# Quarantine/backup statistics:
#         Objects: 0
#         Size: 0
#         Last added: unknown

from typing import Dict

from .agent_based_api.v1 import Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Dict[str, str]


def parse_kaspersky_av_quarantine(string_table: StringTable) -> Section:
    """
    >>> parse_kaspersky_av_quarantine([["Objects", " 1"]])
    {'Objects': ' 1'}
    """
    return {l[0]: " ".join(l[1:]) for l in string_table}


register.agent_section(
    name="kaspersky_av_quarantine",
    parse_function=parse_kaspersky_av_quarantine,
)


def discover_kaspersky_av_quarantine(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_kaspersky_av_quarantine(section: Section) -> CheckResult:
    """
    >>> list(check_kaspersky_av_quarantine({"Objects": " 0"}))
    [Result(state=<State.OK: 0>, summary='No objects in Quarantine'), Metric('Objects', 0.0)]
    """
    objects = int(section["Objects"])
    if objects > 0:
        yield Result(
            state=State.CRIT if objects > 0 else State.OK,
            summary=f"{objects} Objects in Quarantine, Last added: {section['Last added'].strip()}",
        )
    else:
        yield Result(state=State.OK, summary="No objects in Quarantine")
    yield Metric(name="Objects", value=objects)


register.check_plugin(
    name="kaspersky_av_quarantine",
    service_name="AV Quarantine",
    discovery_function=discover_kaspersky_av_quarantine,
    check_function=check_kaspersky_av_quarantine,
)
