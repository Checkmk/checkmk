#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Tuple
from cmk.base.api.agent_based.checking_classes import (
    CheckResult,
    IgnoreResultsError,
    Metric,
    Result,
    State,
)
from cmk.base.check_api_utils import state_markers


def aggregate_node_details(
    node_name: str,
    node_check_returns: CheckResult,
) -> Tuple[State, Optional[str]]:
    """Aggregate the results of a node check

    The results of the check on the node are aggregated.
    The state is the worst of all individual states (as checkmk would
    compute it for the service on the node).

    If no results for the nodes are available, an OK state and None is returned.

    Example:
        To yield the summary results of every node of a cluster from within a
        cluster_check_function use

            for node_name, node_section in sections.values():
                node_state, node_text = aggregate_node_details(
                    node_name,
                    check_my_plugin(item, node_section),
                )
                if node_text is not None:
                    yield Result(state=node_state, notice=node_text)

        Note that this example will send text to the services summary only if the
        state is not OK, otherwise to the details page.

    Args:
        node_name: The name of the node
        node_check_returns: The return values or generator of the nodes check_function call

    Returns:
        Aggregated node result. None if the node check returned nothing.

    """

    # drop Metrics, we may be evaluating a generator
    try:
        returns_wo_metrics = [r for r in node_check_returns if not isinstance(r, Metric)]
    except IgnoreResultsError:
        return State.OK, None

    results = [r for r in returns_wo_metrics if isinstance(r, Result)]
    if not results or len(results) != len(returns_wo_metrics):  # latter: encountered IgnoreResults
        return State.OK, None

    details_with_markers = [
        "%s%s" % (r.details.strip(), state_markers[int(r.state)]) for r in results
    ]

    return (
        State.worst(*(r.state for r in results)),
        '\n'.join("[%s]: %s" % (node_name, line)
                  for detail in details_with_markers
                  for line in detail.split('\n')),
    )
