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

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Service,
    StringTable,
)
from cmk.plugins.ibm_svc.lib import parse_ibm_svc_with_header


@dataclass(frozen=True)
class Host:
    status: str


Section = Sequence[Host]


class _HostParams(TypedDict):
    active_hosts: LevelsT[int]
    inactive_hosts: LevelsT[int]
    degraded_hosts: LevelsT[int]
    offline_hosts: LevelsT[int]
    other_hosts: LevelsT[int]


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
    return [
        Host(status=row["status"])
        for rows in parse_ibm_svc_with_header(string_table, dflt_header).values()
        for row in rows
    ]


def discover_ibm_svc_host(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_ibm_svc_host(params: _HostParams, section: Section) -> CheckResult:
    degraded = 0
    offline = 0
    active = 0
    inactive = 0
    other = 0
    for host in section:
        if host.status == "degraded":
            degraded += 1
        elif host.status == "offline":
            offline += 1
        elif host.status in ["active", "online"]:
            active += 1
        elif host.status == "inactive":
            inactive += 1
        else:
            other += 1

    yield from check_levels(
        active,
        label="Active",
        levels_lower=params["active_hosts"],
        metric_name="active",
        render_func=str,
    )

    for ident, value, levels in [
        ("inactive", inactive, params["inactive_hosts"]),
        ("degraded", degraded, params["degraded_hosts"]),
        ("offline", offline, params["offline_hosts"]),
        ("other", other, params["other_hosts"]),
    ]:
        yield from check_levels(
            value,
            label=ident.capitalize(),
            levels_upper=levels,
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
    check_default_parameters={
        "active_hosts": ("no_levels", None),
        "inactive_hosts": ("no_levels", None),
        "degraded_hosts": ("no_levels", None),
        "offline_hosts": ("no_levels", None),
        "other_hosts": ("no_levels", None),
    },
)
