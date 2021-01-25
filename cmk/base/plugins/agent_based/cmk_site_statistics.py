#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import (
    dataclass,
    fields,
)
from typing import (
    Dict,
    Mapping,
    Tuple,
    Union,
)
from .agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    State,
    register,
)
from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass
class HostStatistics:
    up: int
    down: int
    unreachable: int
    in_downtime: int


@dataclass
class ServiceStatistics:
    ok: int
    in_downtime: int
    on_down_hosts: int
    warning: int
    unknown: int
    critical: int


Section = Mapping[str, Tuple[HostStatistics, ServiceStatistics]]


def parse_cmk_site_statistics(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_cmk_site_statistics([
    ... ['[heute]'],
    ... ['1', '0', '0', '0'],
    ... ['32', '0', '0', '2', '0', '1']]))
    {'heute': (HostStatistics(up=1, down=0, unreachable=0, in_downtime=0),
               ServiceStatistics(ok=32, in_downtime=0, on_down_hosts=0, warning=2, unknown=0, critical=1))}
    """
    section: Dict[str, Tuple[HostStatistics, ServiceStatistics]] = {}
    iter_lines = iter(string_table)

    while True:
        try:
            line_site_name = next(iter_lines)
        except StopIteration:
            return section

        site_name = line_site_name[0][1:-1]
        host_stats = HostStatistics(*(int(n) for n in next(iter_lines)))
        service_stats = ServiceStatistics(*(int(n) for n in next(iter_lines)))
        section[site_name] = host_stats, service_stats


register.agent_section(
    name="cmk_site_statistics",
    parse_function=parse_cmk_site_statistics,
)


def discover_cmk_site_statistics(section: Section) -> DiscoveryResult:
    yield from (Service(item=site_name) for site_name in section)


def _host_results(host_stats: HostStatistics) -> CheckResult:
    n_hosts_not_up = host_stats.down + host_stats.unreachable + host_stats.in_downtime
    n_hosts_total = n_hosts_not_up + host_stats.up
    yield Result(
        state=State.OK,
        summary=f"Total hosts: {n_hosts_total}",
    )
    yield Result(
        state=State.OK,
        summary=f"Problem hosts: {n_hosts_not_up}",
        details="\n".join((
            f"Hosts in state UP: {host_stats.up}",
            f"Hosts in state DOWN: {host_stats.down}",
            f"Unreachable hosts: {host_stats.unreachable}",
            f"Hosts in downtime: {host_stats.in_downtime}",
        )),
    )


def _service_results(service_stats: ServiceStatistics) -> CheckResult:
    n_services_not_ok = (service_stats.in_downtime + service_stats.on_down_hosts +
                         service_stats.warning + service_stats.unknown + service_stats.critical)
    n_services_total = n_services_not_ok + service_stats.ok
    yield Result(
        state=State.OK,
        summary=f"Total services: {n_services_total}",
    )
    yield Result(
        state=State.OK,
        summary=f"Problem services: {n_services_not_ok}",
        details="\n".join((
            f"Services in state OK: {service_stats.ok}",
            f"Services in downtime: {service_stats.in_downtime}",
            f"Services of down hosts: {service_stats.on_down_hosts}",
            f"Services in state WARNING: {service_stats.warning}",
            f"Services in state UNKNOWN: {service_stats.unknown}",
            f"Services in state CRITICAL: {service_stats.critical}",
        )),
    )


def _metrics_from_stats(
    stats: Union[HostStatistics, ServiceStatistics],
    metrics_prefix: str,
) -> CheckResult:
    for field in fields(stats):
        yield Metric(
            f"{metrics_prefix}_{field.name}",
            getattr(stats, field.name),
        )


def check_cmk_site_statistics(item: str, section: Section) -> CheckResult:
    if item not in section:
        return
    host_stats, service_stats = section[item]
    yield from _host_results(host_stats)
    yield from _service_results(service_stats)
    yield from _metrics_from_stats(host_stats, "cmk_hosts")
    yield from _metrics_from_stats(service_stats, "cmk_services")


register.check_plugin(
    name="cmk_site_statistics",
    service_name="Site %s statistics",
    discovery_function=discover_cmk_site_statistics,
    check_function=check_cmk_site_statistics,
)
