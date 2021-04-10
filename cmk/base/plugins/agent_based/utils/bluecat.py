#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple
from typing import Any, Dict, List, Mapping, Tuple
from ..agent_based_api.v1 import (
    equals,
    Metric,
    Result,
    State as state,
    type_defs,
)
from ..agent_based_api.v1.clusterize import make_node_notice_results

Section = Mapping[str, int]
ClusterSection = Mapping[str, Section]

DETECT_BLUECAT = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13315.2.1")

CHECK_DEFAULT_PARAMETERS = {
    "oper_states": {
        "warning": [2, 3, 4],
        "critical": [5],
    },
}

_OPER_STATE_MAP = {
    1: "running normally",
    2: "not running",
    3: "currently starting",
    4: "currently stopping",
    5: "fault",
}


def parse_bluecat(string_table: List[type_defs.StringTable]) -> Section:
    """
    >>> parse_bluecat([[['1', '2']]])
    {'oper_state': 1, 'leases': 2}
    >>> parse_bluecat([[['3']]])
    {'oper_state': 3}
    """
    return {
        key: int(str_val) for key, str_val in zip(
            ['oper_state', 'leases'],
            string_table[0][0],
        )
    }


def _get_service_name(section: Section) -> str:
    return 'DHCP' if 'leases' in section else 'DNS'


def check_bluecat_operational_state(
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    oper_state = section['oper_state']
    service_name = _get_service_name(section)

    mon_state = state.OK
    if oper_state in params['oper_states']['warning']:
        mon_state = state.WARN
    elif oper_state in params['oper_states']['critical']:
        mon_state = state.CRIT

    yield Result(
        state=mon_state,
        summary='%s is %s' % (
            service_name,
            _OPER_STATE_MAP[oper_state],
        ),
    )

    if service_name == 'DHCP':
        leases = section['leases']
        yield Result(
            state=state.OK,
            summary="%s lease%s per second" % (leases, "" if leases == 1 else "s"),
        )
        yield Metric(
            'leases',
            leases,
        )


OKNodeResults = namedtuple(
    'OKNodeResults',
    [
        'name',
        'results',
    ],
)


def cluster_check_bluecat_operational_state(
    params: Mapping[str, Any],
    section: ClusterSection,
) -> type_defs.CheckResult:

    results: Dict[str, Tuple] = {}
    ok_node_results = None
    overall_state = state.OK

    for node_name, node_section in section.items():
        node_results = results.setdefault(
            node_name, tuple(check_bluecat_operational_state(
                params,
                node_section,
            )))

        monitoring_state_result = node_results[0]
        assert isinstance(monitoring_state_result, Result)
        if monitoring_state_result.state is state.OK:
            ok_node_results = OKNodeResults(
                name=node_name,
                results=node_results,
            )
        overall_state = state.worst(
            overall_state,
            monitoring_state_result.state,
        )

    for node_name, original_results in results.items():
        yield from make_node_notice_results(
            node_name,
            original_results,
            force_ok=bool(ok_node_results),
        )

    if ok_node_results:
        for result in ok_node_results.results:
            if isinstance(result, Result):
                result = Result(
                    state=result.state,
                    summary="%s on %s" % (result.summary, ok_node_results.name),
                )
            yield result
    else:
        yield Result(
            state=overall_state,
            summary="No node with OK %s state" % _get_service_name(next(iter(section.values()))),  # pylint: disable=stop-iteration-return
        )
