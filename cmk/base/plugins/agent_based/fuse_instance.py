#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Mapping

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from .agent_based_api.v1 import register, Service, Result, State


FUSE_UP: str = "Fuse Management Central is up and running"

FAILED_AUTH: str = "Cannot connect to Fuse Management Central (Authentication Failed)"

NO_DATA: str = "No data sent by Fuse Management Central"

CONNECTION_FAILED: str = "Cannot connect to Fuse Management Central (Alerts API URL is not available)"


def parse_fuse_instance(string_table: StringTable) -> str:
    return string_table[0][0]


register.agent_section(
    name="fuse_instance",
    parse_function=parse_fuse_instance
)


def discover_fuse_instance(section: str) -> DiscoveryResult:
    yield Service()


def check_fuse_instance(params: Mapping[str, Any], section: str) -> CheckResult:
    result: Result = Result(
        state=State.CRIT,
        summary=CONNECTION_FAILED,
    )
    
    if (section == "up"):
        result = Result(
            state=State.OK,
            summary=FUSE_UP,
        )
    elif (section == "unauth"):
        result = Result(
            state=State.CRIT,
            summary=FAILED_AUTH,
        )
    elif (section == "empty"):
        result = Result(
            state=State.CRIT,
            summary=NO_DATA,
        )
    
    yield result


register.check_plugin(
    name="fuse_instance",
    service_name="Fuse Management Central - Instance",
    discovery_function=discover_fuse_instance,
    check_function=check_fuse_instance,
    check_default_parameters={},
)