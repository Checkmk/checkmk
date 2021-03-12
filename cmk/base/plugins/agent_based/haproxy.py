#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from time import time
from enum import Enum
from typing import Dict, Any, Mapping, Literal

from .agent_based_api.v1.type_defs import StringTable, CheckResult, DiscoveryResult
from .agent_based_api.v1 import (render, register, Result, Service, State, get_value_store,
                                 get_rate, check_levels)


class HAProxyFrontendStatus(Enum):
    OPEN = "OPEN"
    STOP = "STOP"


class HAProxyServerStatus(Enum):
    UP = "UP"
    DOWN = "DOWN"
    NOLB = "NOLB"
    MAINT = "MAINT"
    DRAIN = "DRAIN"
    NO_CHECK = "no check"


Section = Dict


def parse_haproxy(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        if len(line) <= 32 or line[32] not in ("0", "2"):
            continue

        data: Dict[str, Any] = {"status": line[17]}

        if line[32] == "0":
            data["type"] = Literal["frontend"]
            item = line[0]
            try:
                data["stot"] = int(line[7])
            except ValueError:
                continue

        elif line[32] == "2":
            data["type"] = Literal["server"]
            item = "%s/%s" % (line[0], line[1])
            data["layer_check"] = line[36]
            for key, idx in (("uptime", 23), ("active", 19), ("backup", 20)):
                try:
                    data[key] = int(line[idx])
                except ValueError:
                    continue

        parsed[item] = data

    return parsed


register.agent_section(
    name="haproxy",
    parse_function=parse_haproxy,
)


def discover_haproxy_frontend(section: Section) -> DiscoveryResult:
    for key in section.keys():
        if section[key]["type"] == Literal["frontend"]:
            yield Service(item=key)


def check_haproxy_frontend(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get(item)
    if data is None:
        return

    status = data.get("status")
    yield Result(state=State(params[status]), summary=f"Status: {status}")

    stot = data.get("stot")
    if stot is not None:
        value_store = get_value_store()
        session_rate = get_rate(value_store, f"sessions.{item}", time(), stot)
        yield from check_levels(value=session_rate,
                                metric_name="session_rate",
                                label="Session Rate")


register.check_plugin(name="haproxy_frontend",
                      sections=["haproxy"],
                      service_name="HAProxy Frontend %s",
                      discovery_function=discover_haproxy_frontend,
                      check_function=check_haproxy_frontend,
                      check_ruleset_name="haproxy_frontend",
                      check_default_parameters={
                          HAProxyFrontendStatus.OPEN.value: State.OK.value,
                          HAProxyFrontendStatus.STOP.value: State.CRIT.value
                      })


def discover_haproxy_server(section: Section) -> DiscoveryResult:
    for key in section.keys():
        if section[key]["type"] == Literal["server"]:
            yield Service(item=key)


def check_haproxy_server(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get(item)
    if data is None:
        return

    status = data.get("status")
    yield Result(state=State(params[status]), summary=f"Status: {status}")

    if data.get("active"):
        yield Result(state=State.OK, summary="Active")
    elif data.get("backup"):
        yield Result(state=State.OK, summary="Backup")
    else:
        yield Result(state=State.CRIT, summary="Neither active nor backup")

    yield Result(state=State.OK, summary=f"Layer Check: {data['layer_check']}")

    uptime = data.get("uptime")
    if uptime is not None:
        yield Result(state=State.OK, summary=f"Up since {render.timespan(uptime)}")


register.check_plugin(name="haproxy_server",
                      sections=["haproxy"],
                      service_name="HAProxy Server %s",
                      discovery_function=discover_haproxy_server,
                      check_function=check_haproxy_server,
                      check_ruleset_name="haproxy_server",
                      check_default_parameters={
                          HAProxyServerStatus.UP.value: State.OK.value,
                          HAProxyServerStatus.DOWN.value: State.CRIT.value,
                          HAProxyServerStatus.NOLB.value: State.CRIT.value,
                          HAProxyServerStatus.MAINT.value: State.CRIT.value,
                          HAProxyServerStatus.DRAIN.value: State.CRIT.value,
                          HAProxyServerStatus.NO_CHECK.value: State.CRIT.value
                      })
