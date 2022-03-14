#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
<<<omd_status>>>
[kaputt]
apache 1
rrdcached 1
npcd 1
nagios 1
crontab 1
OVERALL 1
[test]
apache 1
rrdcached 1
npcd 0
nagios 1
crontab 1
OVERALL 2
"""

from typing import Any, Dict, Mapping, Optional

from .agent_based_api.v1 import register, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Dict[str, Dict[str, Any]]


def parse_omd_status(string_table: StringTable) -> Optional[Section]:
    """
    >>> for site, status in parse_omd_status([
    ...     ['[heute]'],
    ...     ['cmc', '0'], ['apache', '0'], ['OVERALL', '0'],
    ...     ['[stable]'],
    ...     ['cmc', '0'], ['apache', '0'], ['OVERALL', '0'],
    ... ]).items():
    ...     print(site, status)
    heute {'stopped': [], 'existing': ['cmc', 'apache'], 'overall': 'running'}
    stable {'stopped': [], 'existing': ['cmc', 'apache'], 'overall': 'running'}
    """
    result: Section = {}
    current_item: Optional[Dict[str, Any]] = None

    for name, *states in string_table:
        if name.startswith("["):
            current_item = result.setdefault(name.strip("[]"), {"stopped": [], "existing": []})
            continue
        if current_item is None:
            continue
        if name == "OVERALL":
            if states[0] == "0":
                current_item["overall"] = "running"
            elif states[0] == "1":
                current_item["overall"] = "stopped"
            current_item = None
            continue
        current_item["existing"].append(name)
        if states[0] != "0":
            current_item["stopped"].append(name)
            current_item["overall"] = "partially"
    return result


register.agent_section(name="omd_status", parse_function=parse_omd_status)


def discovery_omd_status(
    section_omd_status: Optional[Section],
    section_omd_info: Optional[Section],
) -> DiscoveryResult:
    """
    >>> for service in discovery_omd_status(
    ...     {'heute': {
    ...        'stopped': [],
    ...        'existing': ['mknotifyd', 'rrdcached', 'cmc'],
    ...        'overall': 'running'},},
    ...     {'versions': {
    ...        '1.6.0-2020.04.27.cee': {
    ...        'version': '1.6.0-2020.04.27.cee',
    ...          'number': '1.6.0-2020.04.27',
    ...          'edition': 'cee',
    ...          'demo': '0'},},
    ...      'sites': {
    ...        'heute': {
    ...          'site': 'heute',
    ...          'used_version': '2020.07.29.cee',
    ...          'autostart': '1'},
    ...        'stable': {
    ...          'site': 'stable',
    ...          'used_version': '1.6.0-2020.07.22.cee',
    ...          'autostart': '0'},},
    ... }):
    ...     print(service)
    Service(item='heute')
    """
    for site in (section_omd_status or {}).keys():
        # if we have omd_info we want to ensure that checks are only executed for sites
        # that do have autostart enabled
        if (section_omd_info or {}).get("sites", {}).get(site, {}).get("autostart") != "0":
            yield Service(item=site)


def _check_omd_status(
    item: str,
    site_services: Mapping[str, Any],
    others_running: bool,
    extra_text: str,
) -> CheckResult:
    """
    >>> for result in _check_omd_status(
    ...       "stable",
    ...       {'stopped': [], 'existing': ['mknotifyd', 'rrdcached', 'cmc'], 'overall': 'running'},
    ...       False,
    ...       ""):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='running')
    """
    if "overall" not in site_services:
        yield Result(state=state.CRIT, summary="defective installation")
    elif site_services["overall"] == "running":
        yield Result(state=state.OK, summary="running")
    elif site_services["overall"] == "stopped":
        # stopped sites are only CRIT when all are stopped
        yield Result(
            state=(state.OK if others_running else state.CRIT), summary="stopped%s" % extra_text
        )
    else:
        # partially running sites are always CRIT
        yield Result(
            state=state.CRIT,
            summary="partially running, stopped services: %s"
            % (", ".join(site_services["stopped"])),
        )


def check_omd_status(
    item: str,
    section_omd_status: Optional[Section],
    section_omd_info: Optional[Section],
) -> CheckResult:
    """
    >>> for result in check_omd_status(
    ...       "production",
    ...       {"production": {
    ...          "stopped": [],
    ...          "existing": ['mknotifyd', 'rrdcached', 'cmc'],
    ...          "overall": 'running'}},
    ...       {}):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='running')
    """
    if not section_omd_status or item not in section_omd_status:
        return
    yield from _check_omd_status(item, section_omd_status[item], False, "")


def cluster_check_omd_status(
    item: str,
    section_omd_status: Mapping[str, Optional[Section]],
    section_omd_info: Mapping[str, Optional[Section]],
) -> CheckResult:
    """
    >>> for result in cluster_check_omd_status(
    ...       "production",
    ...       {"monitoring": {
    ...          "production": {
    ...            "stopped": [],
    ...            "existing": ['mknotifyd', 'rrdcached', 'cmc'],
    ...            "overall": 'running'}}},
    ...       {"monitoring": {}}):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='running')
    """
    # TODO(frans)(question): shouldn't it be better to look for =="running" ?
    any_running = any(
        section[item]["overall"] != "stopped"
        for section in section_omd_status.values()
        if section is not None and item in section
    )

    for node, section in section_omd_status.items():
        if section is None or item not in section:
            continue
        yield from _check_omd_status(item, section[item], any_running, " on %s" % node)


register.check_plugin(
    name="omd_status",
    sections=[
        "omd_status",
        "omd_info",
    ],
    service_name="OMD %s status",
    discovery_function=discovery_omd_status,
    check_function=check_omd_status,
    cluster_check_function=cluster_check_omd_status,
)
