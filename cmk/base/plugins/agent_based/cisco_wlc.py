#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Cisco WLC sections and checks

>>> all(v in _DEVICE_OIDS for v in (
...     ".1.3.6.1.4.1.14179.1.1.4.3",
...     ".1.3.6.1.4.1.9.1.1069",
...     ".1.3.6.1.4.1.9.1.1279",
...     ".1.3.6.1.4.1.9.1.1293",
...     ".1.3.6.1.4.1.9.1.1615",
...     ".1.3.6.1.4.1.9.1.1631",
...     ".1.3.6.1.4.1.9.1.1645",
...     ".1.3.6.1.4.1.9.1.2170",
...     ".1.3.6.1.4.1.9.1.2171",
...     ".1.3.6.1.4.1.9.1.2250",
...     ".1.3.6.1.4.1.9.1.2370",
...     ".1.3.6.1.4.1.9.1.2371",
...     ".1.3.6.1.4.1.9.1.2391",
...     ".1.3.6.1.4.1.9.1.2427",
...     ".1.3.6.1.4.1.9.1.2530",
...     ".1.3.6.1.4.1.9.1.2860",
... ))
True
>>> any(v in _DEVICE_OIDS for v in (
...     ".1.3.6.1.4.1.14179",
...     ".1.3.6.1.4.1.9.1.1068",
...     ".1 3.6.1.4.1.9.1.1069",
...     "1.3.6.1.4.1.9.1.1069",
... ))
False
"""

from typing import Any, Dict, List, Mapping, Optional

from .agent_based_api.v1 import any_of, equals, register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cisco_wlc import CISCO_WLC_OIDS

Section = Dict[str, str]

_OID_sysObjectID = ".1.3.6.1.2.1.1.2.0"

_DEVICE_OIDS = (
    *CISCO_WLC_OIDS,
    # Not sure if cisco_wlc_clients also supports these oids
    ".1.3.6.1.4.1.9.1.2171",
    ".1.3.6.1.4.1.9.1.2391",
    ".1.3.6.1.4.1.9.1.2530",  # cisco WLC 9800
    ".1.3.6.1.4.1.9.1.2860",  # cisco WLC C9800
)

_DETECT_SPEC = any_of(*(equals(_OID_sysObjectID, device_id) for device_id in _DEVICE_OIDS))


map_states = {
    "1": (state.OK, "online"),
    "2": (state.CRIT, "critical"),
    "3": (state.WARN, "warning"),
}


def parse_cisco_wlc(string_table: List[StringTable]) -> Section:
    """
    >>> parse_cisco_wlc([[['AP19', '1'], ['AP02', '1']]])
    {'AP19': '1', 'AP02': '1'}
    """
    return dict(string_table[0])  # type: ignore[arg-type]


def discovery_cisco_wlc(section: Section) -> DiscoveryResult:
    """
    >>> list(discovery_cisco_wlc({'AP19': '1', 'AP02': '1'}))
    [Service(item='AP19'), Service(item='AP02')]
    """
    yield from (Service(item=item) for item in section)


def _node_not_found(item: str, params: Mapping[str, Any]) -> Result:
    infotext = "Accesspoint not found"
    for ap_name, ap_state in params.get("ap_name", []):
        if item.startswith(ap_name):
            return Result(state=ap_state, summary=infotext)
    return Result(state=state.CRIT, summary=infotext)


def _ap_info(node: Optional[str], wlc_status: str) -> Result:
    status, state_readable = map_states.get(wlc_status, (state.UNKNOWN, "unknown[%s]" % wlc_status))
    return Result(
        state=status,
        summary="Accesspoint: %s%s"
        % (state_readable, (" (connected to %s)" % node) if node else ""),
    )


def check_cisco_wlc(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    >>> list(check_cisco_wlc("AP19", {}, {'AP19': '1', 'AP02': '1'}))
    [Result(state=<State.OK: 0>, summary='Accesspoint: online')]
    >>> list(check_cisco_wlc("AP18", {}, {'AP19': '1', 'AP02': '1'}))
    [Result(state=<State.CRIT: 2>, summary='Accesspoint not found')]
    """
    if item in section:
        yield _ap_info(None, section[item])
    else:
        yield _node_not_found(item, params)


def cluster_check_cisco_wlc(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[Section]],
) -> CheckResult:
    """
    >>> list(cluster_check_cisco_wlc("AP19", {}, {"node1": {'AP19': '1', 'AP02': '1'}}))
    [Result(state=<State.OK: 0>, summary='Accesspoint: online (connected to node1)')]
    >>> list(cluster_check_cisco_wlc("AP18", {}, {"node1": {'AP19': '1', 'AP02': '1'}}))
    [Result(state=<State.CRIT: 2>, summary='Accesspoint not found')]
    """
    for node, node_section in section.items():
        if node_section is not None and item in node_section:
            yield _ap_info(node, node_section[item])
            return
    yield _node_not_found(item, params)


register.snmp_section(
    name="cisco_wlc",
    detect=_DETECT_SPEC,
    parse_function=parse_cisco_wlc,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14179.2.2.1.1",
            oids=[
                "3",
                "6",
            ],
        ),
    ],
)

register.check_plugin(
    name="cisco_wlc",  # name taken from pre-1.7 plugin
    service_name="AP %s",
    discovery_function=discovery_cisco_wlc,
    check_default_parameters={},
    check_ruleset_name="cisco_wlc",
    check_function=check_cisco_wlc,
    cluster_check_function=cluster_check_cisco_wlc,
)
