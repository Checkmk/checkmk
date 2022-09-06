#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The main purpose of this plugin is to ensure the regular execution of the Datadog special agent in
the case where only logs are fetched. Without this plugin, no services would be detected in this
case and the agent would not be executed regularly in the background.
"""

from dataclasses import dataclass

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass(frozen=True)
class Section:
    n_logs: int


def parse_datadog_logs(string_table: StringTable) -> Section:
    """
    >>> parse_datadog_logs([["13"]])
    Section(n_logs=13)
    """
    return Section(int(string_table[0][0]))


register.agent_section(
    name="datadog_logs",
    parse_function=parse_datadog_logs,
)


def discover_datadog_logs(section: Section) -> DiscoveryResult:
    yield Service()


def check_datadog_logs(section: Section) -> CheckResult:
    """
    >>> list(check_datadog_logs(Section(4)))
    [Result(state=<State.OK: 0>, summary='Forwarded 4 logs to the Event Console')]
    >>> list(check_datadog_logs(Section(1)))
    [Result(state=<State.OK: 0>, summary='Forwarded 1 log to the Event Console')]
    """
    yield Result(
        state=State.OK,
        summary=f"Forwarded {section.n_logs} log{'' if section.n_logs == 1 else 's'} to the Event Console",
    )


register.check_plugin(
    name="datadog_logs",
    service_name="Datadog logs",
    discovery_function=discover_datadog_logs,
    check_function=check_datadog_logs,
)
