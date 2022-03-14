#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable

from cmk.utils.type_defs import state_markers

from cmk.base.api.agent_based.checking_classes import (
    CheckResult,
    IgnoreResultsError,
    Metric,
    Result,
    State,
)


def make_node_notice_results(
    node_name: str,
    node_check_results: CheckResult,
    *,
    force_ok: bool = False,
) -> Iterable[Result]:
    """Prepare results of a node for output in a cluster check function

    This function consumes everything from a check function (that is, a :class:`.Result`,
    a :class:`.Metric` or an :class:`.IgnoreResults`) and returns an iterable of :class:`.Result`\\ s.

    The text is prepended with `'[node]: '`, and the text type is changed from `summary` to `notice`
    (see :class:`.Result` for more details).

    Usage example:
        >>> def cluster_check_myplugin(item, section):
        ...     '''A cluster check function that just passes along all node results'''
        ...     for node_name, node_section in sections.values():
        ...         yield from make_node_notice_results(
        ...             node_name,
        ...             check_myplugin(item, node_section),
        ...         )

        This will write text from every node to the services summary if the state is not OK,
        otherwise to the details text.

    Args:
        node_name:          The name of the node
        node_check_results: The return values or generator of the nodes check_function call
        force_ok:           If specified, the state of all results is chacnged to OK. In this case
                            the state marker corresponding to the original state is appended to
                            the text.

    Returns:
        The node results, with the text type `notice`.

    """

    # consume potential generator and drop Metrics
    try:
        returns_wo_metrics = [r for r in node_check_results if not isinstance(r, Metric)]
    except IgnoreResultsError:
        return

    # check for encountered IgnoreResults (also tells mypy that it's all Results)
    results = [r for r in returns_wo_metrics if isinstance(r, Result)]
    if len(results) != len(returns_wo_metrics):
        return

    def _nodify(text: str, state: State) -> str:
        """Prepend node name and, if state is forced to OK, append state marker"""
        node_text = "\n".join("[%s]: %s" % (node_name, line) for line in text.split("\n"))
        if not force_ok:
            return node_text
        return "%s%s" % (node_text.rstrip(), state_markers[int(state)])

    for result in results:
        yield Result(
            state=State.OK if force_ok else result.state,
            notice=_nodify(result.summary, result.state),
            details=_nodify(result.details, result.state),
        )
