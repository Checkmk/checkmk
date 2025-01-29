#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIAUTHENTICATOR

Section = Mapping[str, int]


def parse_fortiauthenticator_auth_fail(string_table: Sequence[StringTable]) -> Section | None:
    """
    >>> parse_fortiauthenticator_auth_fail([[['3']]])
    {'auth_fails': 3}
    """
    return {"auth_fails": int(string_table[0][0][0])} if all(string_table) else None


def discover_fortiauthenticator_auth_fail(section: Section) -> DiscoveryResult:
    """
    >>> list(discover_fortiauthenticator_auth_fail({"auth_fails": 3}))
    [Service()]
    """
    yield Service()


def check_fortiauthenticator_auth_fail(
    params: Mapping[str, tuple[int, int]],
    section: Section,
) -> CheckResult:
    """
    >>> for r in check_fortiauthenticator_auth_fail({"auth_fails": (1, 5)}, {"auth_fails": 3}):
    ...     print(r)
    Result(state=<State.WARN: 1>, summary='Authentication failures within the last 5 minutes: 3 (warn/crit at 1/5)')
    Metric('fortiauthenticator_fails_5min', 3.0, levels=(1.0, 5.0))
    """
    yield from check_levels_v1(
        section["auth_fails"],
        levels_upper=params["auth_fails"],
        metric_name="fortiauthenticator_fails_5min",
        label="Authentication failures within the last 5 minutes",
        render_func=str,
    )


snmp_section_fortiauthenticator_auth_fail = SNMPSection(
    name="fortiauthenticator_auth_fail",
    parse_function=parse_fortiauthenticator_auth_fail,
    detect=DETECT_FORTIAUTHENTICATOR,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.113.1.202",
            oids=[
                "23",  # facAuthFailures5Min
            ],
        ),
    ],
)

check_plugin_fortiauthenticator_auth_fail = CheckPlugin(
    name="fortiauthenticator_auth_fail",
    service_name="Authentication Failures",
    discovery_function=discover_fortiauthenticator_auth_fail,
    check_function=check_fortiauthenticator_auth_fail,
    check_default_parameters={"auth_fails": (100, 200)},
    check_ruleset_name="fortiauthenticator_auth_fail",
)
