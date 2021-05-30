#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from typing import Mapping

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from .agent_based_api.v1 import register, Service, Result, State


def parse_fuse_env_alerts(string_table: StringTable) -> list:
    return json.loads(string_table[0][0])


register.agent_section(
    name="fuse_env_alerts",
    parse_function=parse_fuse_env_alerts
)


def discovery_fuse_env_alerts(section: list) -> DiscoveryResult:
    for alert in section:
        service_name: str = "%s - %s" % (alert["name"], alert["component_type"])
        yield Service(
            item=service_name,
            parameters={
                "fuse_id": alert["fuse_id"],
                "component_type": alert["component_type"]
            })


def check_fuse_env_alerts(item: str, params: Mapping[str, str], section: list) -> CheckResult:
    for alert in section:
        if (alert["fuse_id"] == params.get("fuse_id") and alert["component_type"]) == params.get("component_type"):
            errors: int = alert["errors"]
            warnings: int = alert["warnings"]
            link: str = alert["link"]
            if link:
                link = " | <a href=\"%s\" target=\"_blank\">click here for more info</a>" % link
            state = State.OK
            if errors > 0:
                state = State.CRIT
            elif warnings > 0:
                state = State.WARN
            yield Result(
                state=state,
                summary="Errors: %s | Warnings: %s%s" % (errors, warnings, link),
            )


register.check_plugin(
    name="fuse_env_alerts",
    service_name="OpenText - Environment - %s",
    discovery_function=discovery_fuse_env_alerts,
    check_function=check_fuse_env_alerts,
    check_default_parameters={},
)
