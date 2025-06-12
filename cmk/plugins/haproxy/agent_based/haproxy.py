#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from time import time
from typing import Any, NamedTuple, TypeVar

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.haproxy.lib import (
    HAProxyFrontendStatus,
    HAProxyServerStatus,
)


class Backend(NamedTuple):
    status: HAProxyServerStatus | str
    uptime: int | None
    active: int | None
    backup: int | None
    stot: int | None


class Frontend(NamedTuple):
    status: HAProxyFrontendStatus | str
    stot: int | None


class Server(NamedTuple):
    status: HAProxyServerStatus | str
    layer_check: str
    uptime: int | None
    active: int | None
    backup: int | None
    stot: int | None


class Section(NamedTuple):
    backends: dict[str, Backend]
    frontends: dict[str, Frontend]
    servers: dict[str, Server]


def parse_int(val: str) -> int | None:
    try:
        return int(val)
    except ValueError:
        return None


def status_result(
    status: HAProxyFrontendStatus | HAProxyServerStatus | str, params: Mapping[str, Any]
) -> CheckResult:
    """
    Yield the proper Result based on the available statuses in the params.
    State.WARN if status not in params.
    """
    if isinstance(status, str):
        yield Result(state=State.UNKNOWN, summary=f"Unknown status: {status}")
        return

    if status.name in params:
        yield Result(state=State(params[status.name]), summary=f"Status: {status.value}")
    else:
        # covers partial statuses like DOWN 1/2
        yield Result(
            state=State.WARN,
            summary=f"Status: {status.value}",
        )


T = TypeVar("T", HAProxyServerStatus, HAProxyFrontendStatus)


def status_to_enum(status: str, _enum: type[T]) -> T | str:
    try:
        return _enum(status)
    except ValueError:
        return status


def parse_haproxy(string_table: StringTable) -> Section:
    backends = {}
    frontends = {}
    servers = {}
    for line in string_table:
        if len(line) <= 32 or line[32] not in ("0", "1", "2"):
            continue

        status = line[17]

        if line[32] == "0":
            name = line[0]
            try:
                stot = int(line[7])
            except ValueError:
                continue
            frontends[name] = Frontend(
                status=status_to_enum(status=status, _enum=HAProxyFrontendStatus), stot=stot
            )

        elif line[32] in ["1", "2"]:
            uptime = parse_int(line[23])
            active = parse_int(line[19])
            backup = parse_int(line[20])
            try:
                stot = int(line[7])
            except ValueError:
                continue

            if line[32] in "1":
                name = line[0]

                backends[name] = Backend(
                    status=status_to_enum(status=status, _enum=HAProxyServerStatus),
                    uptime=uptime,
                    active=active,
                    backup=backup,
                    stot=stot,
                )
            elif line[32] == "2":
                name = f"{line[0]}/{line[1]}"
                layer_check = line[36]

                servers[name] = Server(
                    status=status_to_enum(status=status, _enum=HAProxyServerStatus),
                    layer_check=layer_check,
                    uptime=uptime,
                    active=active,
                    backup=backup,
                    stot=stot,
                )

    return Section(backends=backends, frontends=frontends, servers=servers)


agent_section_haproxy = AgentSection(
    name="haproxy",
    parse_function=parse_haproxy,
)


def discover_haproxy_backend(section: Section) -> DiscoveryResult:
    for key in section.backends.keys():
        yield Service(item=key)


def check_haproxy_backend(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from haproxy_result(item, params, section.backends.get(item))


check_plugin_haproxy_backend = CheckPlugin(
    name="haproxy_backend",
    sections=["haproxy"],
    service_name="HAProxy Backend %s",
    discovery_function=discover_haproxy_backend,
    check_function=check_haproxy_backend,
    check_ruleset_name="haproxy_server",
    check_default_parameters={
        HAProxyServerStatus.UP.name: State.OK.value,
        HAProxyServerStatus.DOWN.name: State.CRIT.value,
        HAProxyServerStatus.NOLB.name: State.CRIT.value,
        HAProxyServerStatus.MAINT.name: State.CRIT.value,
        HAProxyServerStatus.MAINT_VIA.name: State.WARN.value,
        HAProxyServerStatus.MAINT_RES.name: State.WARN.value,
        HAProxyServerStatus.DRAIN.name: State.CRIT.value,
        HAProxyServerStatus.NO_CHECK.name: State.CRIT.value,
    },
)


def discover_haproxy_frontend(section: Section) -> DiscoveryResult:
    for key in section.frontends.keys():
        yield Service(item=key)


def check_haproxy_frontend(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.frontends.get(item)
    if data is None:
        return

    status = data.status
    yield from status_result(status, params)

    stot = data.stot
    if stot is not None:
        value_store = get_value_store()
        session_rate = get_rate(value_store, f"sessions.{item}", time(), stot)
        yield from check_levels(
            value=session_rate, metric_name="session_rate", label="Session Rate"
        )


check_plugin_haproxy_frontend = CheckPlugin(
    name="haproxy_frontend",
    sections=["haproxy"],
    service_name="HAProxy Frontend %s",
    discovery_function=discover_haproxy_frontend,
    check_function=check_haproxy_frontend,
    check_ruleset_name="haproxy_frontend",
    check_default_parameters={
        HAProxyFrontendStatus.OPEN.name: State.OK.value,
        HAProxyFrontendStatus.STOP.name: State.CRIT.value,
    },
)


def discover_haproxy_server(section: Section) -> DiscoveryResult:
    for key in section.servers.keys():
        yield Service(item=key)


def check_haproxy_server(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from haproxy_result(item, params, section.servers.get(item))


def haproxy_result(
    item: str, params: Mapping[str, Any], data: Server | Backend | None
) -> CheckResult:
    if data is None:
        return

    status = data.status
    yield from status_result(status, params)

    if data.active:
        yield Result(state=State.OK, summary="Active")
    elif data.backup:
        yield Result(state=State.OK, summary="Backup")
    else:
        yield Result(state=State.CRIT, summary="Neither active nor backup")

    if isinstance(data, Server):
        yield Result(state=State.OK, summary=f"Layer Check: {data.layer_check}")

    uptime = data.uptime
    if uptime is not None:
        yield Result(state=State.OK, summary=f"Up since {render.timespan(uptime)}")

    if data.stot:
        value_store = get_value_store()
        session_rate = get_rate(value_store, f"sessions.{item}", time(), data.stot)
        yield from check_levels(
            value=session_rate, metric_name="session_rate", label="Session Rate"
        )


check_plugin_haproxy_server = CheckPlugin(
    name="haproxy_server",
    sections=["haproxy"],
    service_name="HAProxy Server %s",
    discovery_function=discover_haproxy_server,
    check_function=check_haproxy_server,
    check_ruleset_name="haproxy_server",
    check_default_parameters={
        HAProxyServerStatus.UP.name: State.OK.value,
        HAProxyServerStatus.DOWN.name: State.CRIT.value,
        HAProxyServerStatus.NOLB.name: State.CRIT.value,
        HAProxyServerStatus.MAINT.name: State.CRIT.value,
        HAProxyServerStatus.MAINT_VIA.name: State.WARN.value,
        HAProxyServerStatus.MAINT_RES.name: State.WARN.value,
        HAProxyServerStatus.DRAIN.name: State.CRIT.value,
        HAProxyServerStatus.NO_CHECK.name: State.CRIT.value,
    },
)
