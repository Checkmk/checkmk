#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<ibm_svc_host:sep(58)>>>
# 0:h_esx01:2:4:degraded
# 1:host206:2:2:online
# 2:host105:2:2:online
# 3:host106:2:2:online

from collections.abc import Mapping, Sequence
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.legacy_includes.ibm_svc import parse_ibm_svc_with_header

Section = Mapping[str, Sequence[Mapping[str, str]]]


class _HostParams(TypedDict, total=False):
    active_hosts: tuple[int, int]
    inactive_hosts: tuple[int, int]
    degraded_hosts: tuple[int, int]
    offline_hosts: tuple[int, int]
    other_hosts: tuple[int, int]


def parse_ibm_svc_host(string_table: StringTable) -> Section:
    dflt_header = [
        "id",
        "name",
        "port_count",
        "iogrp_count",
        "status",
        "site_id",
        "site_name",
        "host_cluster_id",
        "host_cluster_name",
    ]
    return parse_ibm_svc_with_header(string_table, dflt_header)


def discover_ibm_svc_host(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_ibm_svc_host(params: _HostParams, section: Section) -> CheckResult:
    degraded = 0
    offline = 0
    active = 0
    inactive = 0
    other = 0
    for rows in section.values():
        for data in rows:
            status = data["status"]
            if status == "degraded":
                degraded += 1
            elif status == "offline":
                offline += 1
            elif status in ["active", "online"]:
                active += 1
            elif status == "inactive":
                inactive += 1
            else:
                other += 1

    if "always_ok" in params:
        # Old configuration rule from before version 1.2.7
        always_ok = bool(params.get("always_ok"))
        yield Result(state=State.OK, summary=f"{active} active, {inactive} inactive")
        yield Metric("active", active)
        yield Metric("inactive", inactive)
        yield Metric("degraded", degraded)
        yield Metric("offline", offline)
        yield Metric("other", other)
        if degraded > 0:
            yield Result(
                state=State.OK if always_ok else State.WARN,
                summary=f"{degraded} degraded",
            )
        if offline > 0:
            yield Result(
                state=State.OK if always_ok else State.CRIT,
                summary=f"{offline} offline",
            )
        if other > 0:
            yield Result(
                state=State.OK if always_ok else State.WARN,
                summary=f"{other} in an unidentified state",
            )
        return

    active_levels = params.get("active_hosts")
    yield from check_levels(
        active,
        label="Active",
        levels_lower=("fixed", active_levels) if active_levels else ("no_levels", None),
        metric_name="active",
        render_func=str,
    )

    for ident, value, raw_levels in [
        ("inactive", inactive, params.get("inactive_hosts")),
        ("degraded", degraded, params.get("degraded_hosts")),
        ("offline", offline, params.get("offline_hosts")),
        ("other", other, params.get("other_hosts")),
    ]:
        yield from check_levels(
            value,
            label=ident.capitalize(),
            levels_upper=("fixed", raw_levels) if raw_levels else ("no_levels", None),
            metric_name=ident,
            render_func=str,
        )


agent_section_ibm_svc_host = AgentSection(
    name="ibm_svc_host",
    parse_function=parse_ibm_svc_host,
)


check_plugin_ibm_svc_host = CheckPlugin(
    name="ibm_svc_host",
    service_name="Hosts",
    discovery_function=discover_ibm_svc_host,
    check_function=check_ibm_svc_host,
    check_ruleset_name="ibm_svc_host",
    check_default_parameters={},
)
