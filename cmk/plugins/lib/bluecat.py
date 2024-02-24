#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, equals, IgnoreResults, Metric, Result, State
from cmk.agent_based.v2.clusterize import make_node_notice_results

Section = Mapping[str, int]
ClusterSection = Mapping[str, Section | None]

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


def parse_bluecat(string_table: StringTable) -> Section | None:
    """
    >>> parse_bluecat([['1', '2']])
    {'oper_state': 1, 'leases': 2}
    >>> parse_bluecat([['3']])
    {'oper_state': 3}
    """
    return (
        {
            key: int(str_val)
            for key, str_val in zip(
                ["oper_state", "leases"],
                string_table[0],
            )
        }
        if string_table
        else None
    )


def _get_service_name(section: Section) -> str:
    return "DHCP" if "leases" in section else "DNS"


def check_bluecat_operational_state(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    oper_state = section["oper_state"]
    service_name = _get_service_name(section)

    mon_state = State.OK
    if oper_state in params["oper_states"]["warning"]:
        mon_state = State.WARN
    elif oper_state in params["oper_states"]["critical"]:
        mon_state = State.CRIT

    yield Result(
        state=mon_state,
        summary="%s is %s"
        % (
            service_name,
            _OPER_STATE_MAP[oper_state],
        ),
    )

    if service_name == "DHCP":
        leases = section["leases"]
        yield Result(
            state=State.OK,
            summary="{} lease{} per second".format(leases, "" if leases == 1 else "s"),
        )
        yield Metric(
            "leases",
            leases,
        )


class OKNodeResults(NamedTuple):
    name: str
    results: Sequence[IgnoreResults | Metric | Result]


def cluster_check_bluecat_operational_state(
    params: Mapping[str, Any],
    section: ClusterSection,
) -> CheckResult:
    results: dict[str, Sequence[IgnoreResults | Metric | Result]] = {}
    ok_node_results = None
    overall_state = State.OK

    for node_name, node_section in section.items():
        if node_section is None:
            continue

        node_results = results.setdefault(
            node_name,
            tuple(
                check_bluecat_operational_state(
                    params,
                    node_section,
                )
            ),
        )

        monitoring_state_result = node_results[0]
        assert isinstance(monitoring_state_result, Result)
        if monitoring_state_result.state is State.OK:
            ok_node_results = OKNodeResults(
                name=node_name,
                results=node_results,
            )
        overall_state = State.worst(
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
                    summary=f"{result.summary} on {ok_node_results.name}",
                )
            yield result
    else:
        first_node_section: Section = next(
            (node_section for node_section in section.values() if node_section is not None), {}
        )
        yield Result(
            state=overall_state,
            summary="No node with OK %s state" % _get_service_name(first_node_section),
        )
