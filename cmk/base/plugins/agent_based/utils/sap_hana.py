#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Any, Tuple, NamedTuple, Union

from ..agent_based_api.v1 import Result, State, Metric, IgnoreResults
from ..agent_based_api.v1.type_defs import StringTable, CheckResult


class CheckResults(NamedTuple):
    overall_state: State
    results: List[Union[IgnoreResults, Metric, Result]] = []


ParsedSection = Dict[str, Dict]


def parse_sap_hana(info: StringTable):
    parsed: Dict[str, List[Any]] = {}
    instance = None
    for line in info:
        joined_line = " ".join(line)
        if joined_line.startswith("[[") and joined_line.endswith("]]"):
            instance = parsed.setdefault(joined_line[2:-2], [])
        elif instance is not None:
            instance.append([e.strip('"') for e in line])
    return parsed


def parse_sap_hana_cluster_aware(info):
    parsed: Dict[Tuple, List[Any]] = {}
    instance = None
    for line in info:
        node, line = line[0], line[1:]
        joined_line = " ".join(line)
        if joined_line.startswith("[[") and joined_line.endswith("]]"):
            instance = parsed.setdefault((joined_line[2:-2], node), [])
        elif instance is not None:
            instance.append([e.strip('"') for e in line])
    return parsed


def assume_best_state_cluster_check(item, section, check_function, params=None):
    yield Result(state=State.OK, summary="Nodes: %s" % ", ".join(section.keys()))

    node_results: Dict[str, CheckResults] = {}
    for node, node_section in section.items():
        if item in node_section:
            if params is not None:
                all_results = list(check_function(item, params, node_section))
            else:
                all_results = list(check_function(item, node_section))

            all_states = [r.state for r in all_results if isinstance(r, Result)]
            node_results[node] = CheckResults(State.worst(*all_states), all_results)

    node_states = [r.overall_state for r in node_results.values()]
    best_state = State.best(*node_states)

    for result in node_results.values():
        if result.overall_state == best_state:
            yield from result.results
            return


def get_cluster_check(check_function):
    def cluster_check(
        item,
        section,
    ) -> CheckResult:

        yield from assume_best_state_cluster_check(item, section, check_function)

    return cluster_check


def get_cluster_check_with_params(check_function):
    def cluster_check(
        item,
        params,
        section,
    ) -> CheckResult:

        yield from assume_best_state_cluster_check(item, section, check_function, params)

    return cluster_check
