#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional
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
) -> Optional[Result]:
    """Aggregate the results of a node check into a single Result

    The results of the check on the node are aggregated into a single
    Result instance, showing all node results in its details.
    The state is the worst of all individual states (as checkmk would
    compute it for the service on the node).

    If no results for the nodes are available, None is returned.

    Example:
        To yield the summary results of every node of a cluster from within a
        cluster_check_function use

            for node_name, node_section in sections.values():
                summary_result = aggregate_node_details(
                    node_name,
                    check_my_plugin(item, node_section),
                )
                if summary_result is not None:
                    yield summary_result

        Note that this will send no text to the services summary, only to the
        details page.

    Args:
        node_name (str): The name of the node
        node_check_returns (Sequence[Union[IgnoreResults, Result, Metric]]): The return values or
        generator of the nodes check_function call

    Returns:
        Optional[Result]: Aggregated node result. None if the node check returned nothing.

    """

    # drop Metrics, we may be evaluating a generator
    try:
        returns_wo_metrics = [r for r in node_check_returns if not isinstance(r, Metric)]
    except IgnoreResultsError:
        return None

    results = [r for r in returns_wo_metrics if isinstance(r, Result)]
    if not results or len(results) != len(returns_wo_metrics):  # latter: encountered IgnoreResults
        return None

    details_with_markers = [
        "%s%s" % (r.details.strip(), state_markers[int(r.state)]) for r in results
    ]

    details_lines: List[str] = sum((d.split('\n') for d in details_with_markers), [])

    return Result(
        state=State.worst(*(r.state for r in results)),
        details="\n".join("[%s]: %s" % (node_name, d) for d in details_lines),
    )
