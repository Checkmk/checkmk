#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#.1.3.6.1.2.1.1.1.0 testname
#.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.8072.3.2.10
#[...]
#.1.3.6.1.4.1.12356.113.1.202.23.0 0
#[...]

#Example GUI Output:
#OK	FortiAuthenticator Authentication Failures
#       Authentication Failures within the last 5 Minutes: 0

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    Service,
    equals,
    check_levels,
    SNMPTree,
)
from typing import Mapping, List, Tuple

Section = List[str]


def parse_fortiauthenticator_auth_fail(string_table: List[StringTable]) -> Section:
    return string_table[0][0]


def discovery_fortiauthenticator_auth_fail(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortiauthenticator_auth_fail(params: Mapping[str, Tuple[float, float]],
                                       section: Section) -> CheckResult:
    fail_limit_upper = params.get("auth_fails")
    fails = int(section[0][0][0])
    yield from check_levels(
        fails,
        levels_upper=fail_limit_upper,
        metric_name="fortiauthenticator_fails_5min",
        label="Authentication Failures within the last 5min",
        render_func=lambda v: "%s" % v,
    )


register.snmp_section(
    name="fortiauthenticator_auth_fail",
    parse_function=parse_fortiauthenticator_auth_fail,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.8072.3.2.10'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.113.1.202',
            oids=[
                '23.0',  # facAuthFailures5Min
            ]),
    ],
)

register.check_plugin(
    name="fortiauthenticator_auth_fail",
    service_name="FortiAuthenticator Authentication Failures",
    discovery_function=discovery_fortiauthenticator_auth_fail,
    check_function=check_fortiauthenticator_auth_fail,
    check_default_parameters={"auth_fails": (100, 200)},
    check_ruleset_name="fortiauthenticator_auth_fail",
)
