#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A throw-away check plug-in that reports its effective parameters.  It is copied
# into a test site to play the role of a local plugin (see test_check_variables.py).

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse(string_table: StringTable) -> StringTable:
    return string_table


def discover(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check(params: Mapping[str, object], section: StringTable) -> CheckResult:  # noqa: ARG001
    yield Result(state=State.OK, summary=f"params={dict(params)!r}")


agent_section_test_check_3 = AgentSection(
    name="test_check_3",
    parse_function=parse,
)

check_plugin_test_check_3 = CheckPlugin(
    name="test_check_3",
    service_name="Testcheck 3",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="asd",
    check_default_parameters={"param1": 123},
)
