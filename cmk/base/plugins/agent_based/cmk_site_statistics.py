#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, fields
from typing import Dict, Generator, Iterable, Mapping, Optional, Sequence, Tuple, Union

from .agent_based_api.v1 import Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.livestatus_status import LivestatusSection


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


CMKSiteStatisticsSection = Mapping[str, Tuple[HostStatistics, ServiceStatistics]]


def _timeout_and_delta_position(*lines_stats: Sequence[str]) -> Tuple[bool, int]:
    for delta_position, line_stats in enumerate(
        lines_stats,
        start=1,
    ):
        if len(line_stats) == 1:
            return True, delta_position
    return False, len(lines_stats) + 1


def parse_cmk_site_statistics(string_table: StringTable) -> CMKSiteStatisticsSection:
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

    current_position = 0
    while True:
        try:
            line_site_name = string_table[current_position]
            line_hosts_stats = string_table[current_position + 1]
            line_service_stats = string_table[current_position + 2]
        except IndexError:
            return section

        timed_out, delta_position = _timeout_and_delta_position(
            line_hosts_stats,
            line_service_stats,
        )
        current_position += delta_position
        if timed_out:
            continue

        site_name = line_site_name[0][1:-1]
        host_stats = HostStatistics(*(int(n) for n in line_hosts_stats))
        service_stats = ServiceStatistics(*(int(n) for n in line_service_stats))
        section[site_name] = host_stats, service_stats


register.agent_section(
    name="cmk_site_statistics",
    parse_function=parse_cmk_site_statistics,
)


def discover_cmk_site_statistics(
    section_cmk_site_statistics: Optional[CMKSiteStatisticsSection],
    section_livestatus_status: Optional[LivestatusSection],
) -> DiscoveryResult:
    if section_cmk_site_statistics:
        yield from (Service(item=site_name) for site_name in section_cmk_site_statistics)


def _host_results(host_stats: HostStatistics) -> Iterable[Result]:
    n_hosts_not_up = host_stats.down + host_stats.unreachable + host_stats.in_downtime
    n_hosts_total = n_hosts_not_up + host_stats.up
    yield Result(
        state=State.OK,
        summary=f"Total hosts: {n_hosts_total}",
    )
    yield Result(
        state=State.OK,
        summary=f"Problem hosts: {n_hosts_not_up}",
        details="\n".join(
            (
                f"Hosts in state UP: {host_stats.up}",
                f"Hosts in state DOWN: {host_stats.down}",
                f"Unreachable hosts: {host_stats.unreachable}",
                f"Hosts in downtime: {host_stats.in_downtime}",
            )
        ),
    )


def _service_results(service_stats: ServiceStatistics) -> Iterable[Result]:
    n_services_not_ok = (
        service_stats.in_downtime
        + service_stats.on_down_hosts
        + service_stats.warning
        + service_stats.unknown
        + service_stats.critical
    )
    n_services_total = n_services_not_ok + service_stats.ok
    yield Result(
        state=State.OK,
        summary=f"Total services: {n_services_total}",
    )
    yield Result(
        state=State.OK,
        summary=f"Problem services: {n_services_not_ok}",
        details="\n".join(
            (
                f"Services in state OK: {service_stats.ok}",
                f"Services in downtime: {service_stats.in_downtime}",
                f"Services of down hosts: {service_stats.on_down_hosts}",
                f"Services in state WARNING: {service_stats.warning}",
                f"Services in state UNKNOWN: {service_stats.unknown}",
                f"Services in state CRITICAL: {service_stats.critical}",
            )
        ),
    )


def _metrics_from_stats(
    stats: Union[HostStatistics, ServiceStatistics],
    metrics_prefix: str,
) -> Iterable[Metric]:
    for field in fields(stats):
        yield Metric(
            f"{metrics_prefix}_{field.name}",
            getattr(stats, field.name),
        )


def check_cmk_site_statistics(
    item: str,
    section_cmk_site_statistics: Optional[CMKSiteStatisticsSection],
    section_livestatus_status: Optional[LivestatusSection],
) -> Generator[Union[Metric, Result], None, None]:
    if not section_cmk_site_statistics or item not in section_cmk_site_statistics:
        return
    host_stats, service_stats = section_cmk_site_statistics[item]
    yield from _host_results(host_stats)
    yield from _service_results(service_stats)
    yield from _metrics_from_stats(host_stats, "cmk_hosts")
    yield from _metrics_from_stats(service_stats, "cmk_services")

    # This part is needed for the timeseries graphs which show host and service problems in the
    # main dashboard (to as far as possible uniquely cross-match sites in this agent output with
    # sites to which are remotely connected)
    if (
        section_livestatus_status
        and item in section_livestatus_status
        and section_livestatus_status[item]
    ):
        yield Result(
            state=State.OK,
            notice=f"Core PID: {section_livestatus_status[item]['core_pid']}",
        )


register.check_plugin(
    name="cmk_site_statistics",
    sections=["cmk_site_statistics", "livestatus_status"],
    service_name="Site %s statistics",
    discovery_function=discover_cmk_site_statistics,
    check_function=check_cmk_site_statistics,
)
