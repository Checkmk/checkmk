#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compute the cluster check function from the plugin and parameters."""

from collections import defaultdict
from functools import partial
from typing import (
    Any,
    Callable,
    Final,
    Iterable,
    Mapping,
    Sequence,
    Set,
    Tuple,
    Union,
)

from cmk.utils.type_defs import ClusterMode, state_markers as STATE_MARKERS
from cmk.base.api.agent_based.value_store import load_host_value_store
from cmk.base.api.agent_based.checking_classes import (
    CheckFunction,
    CheckPlugin,
    CheckResult,
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    State,
)
from cmk.base.check_utils import ServiceID

_Kwargs = Mapping[str, Any]

_NON_SECTION_KEYS: Final = {'item', 'params'}


def _unfit_for_clustering(**_kw) -> CheckResult:
    """A cluster_check_function that displays a generic warning"""
    yield Result(
        state=State.UNKNOWN,
        summary=("This service does not implement a native cluster mode. Please change your "
                 "configuration using the rule 'Aggreation options for clustered services', "
                 "and select one of the other available aggregation modes."),
    )


def get_cluster_check_function(
    mode: ClusterMode,
    clusterization_parameters: Mapping[str, Any],
    *,
    service_id: ServiceID,
    plugin: CheckPlugin,
    persist_value_store_changes: bool,
) -> CheckFunction:
    if mode == 'native':
        return plugin.cluster_check_function or _unfit_for_clustering

    executor = NodeCheckExecutor(
        service_id=service_id,
        persist_value_store_changes=persist_value_store_changes,
    )

    if mode == "worst":
        return partial(
            _cluster_check_worst,
            clusterization_parameters=clusterization_parameters,
            executor=executor,
            check_function=plugin.check_function,
        )

    raise ValueError(mode)


def _cluster_check_worst(
    *,
    clusterization_parameters: Mapping[str, Any],
    executor: "NodeCheckExecutor",
    check_function: Callable,
    **cluster_kwargs: Any,
) -> CheckResult:

    node_results = executor(check_function, cluster_kwargs)
    if not node_results.results:
        if (node_ignores := node_results.ignore_results.items()):
            raise IgnoreResultsError(", ".join(
                f"[{node}] {', '.join(str(i) for i in ign)}" for node, ign in node_ignores))
        return

    worst_node = node_results.get_worst_node()
    yield from node_results.results[worst_node]

    # TODO: maybe output information on how many nodes there are in total?
    # see how we do this for the failover case, and find a consistent solutiuon.

    yield from (_noticeify(r)
                for node in sorted(n for n in node_results.results if n != worst_node)
                for r in node_results.results[node])

    # TODO: check if we need an option to "nail down" the node here
    yield from node_results.metrics[worst_node]


class NodeResults:
    def __init__(
        self,
        results: Mapping[str, Sequence[Result]],
        metrics: Mapping[str, Sequence[Metric]],
        ignore_results: Mapping[str, Sequence[IgnoreResults]],
    ) -> None:
        self.results: Final = results
        self.metrics: Final = metrics
        self.ignore_results: Final = ignore_results

    def get_worst_node(self) -> str:
        return self._get_extreme_node(selector=State.worst)

    def _get_extreme_node(
        self,
        *,
        selector: Callable[..., State],
    ) -> str:
        """Determine the best/worst nodes name

        If multiple nodes share the extreme (best/worst) state,
        for now we choose the first one (alphabetically).
        """
        if not self.results:
            # This would happen in the selector call anyway, but better be explicit.
            raise ValueError('no results available')

        nodes_by_states = defaultdict(set)
        for node, results in self.results.items():
            nodes_by_states[State.worst(*(r.state for r in results))].add(node)

        extreme_nodes = nodes_by_states[selector(*nodes_by_states)]

        # for now: arbitrary, but comprehensible choice
        return sorted(extreme_nodes)[0]


class NodeCheckExecutor:
    def __init__(self, *, service_id: ServiceID, persist_value_store_changes: bool) -> None:
        self._service_id = service_id
        self._persist_value_store_changes = persist_value_store_changes

    def __call__(
        self,
        check_function: Callable[..., CheckResult],
        cluster_kwargs: _Kwargs,
    ) -> NodeResults:
        """Dispatch the check function results for all nodes"""
        results = defaultdict(list)
        metrics = defaultdict(list)
        ignores = defaultdict(list)

        for node, kwargs in self._iter_node_kwargs(cluster_kwargs):

            for element in self._consume_checkresult(node, check_function(**kwargs)):

                if isinstance(element, Metric):
                    metrics[node].append(element)

                elif isinstance(element, IgnoreResults):
                    ignores[node].append(element)

                elif isinstance(element, Result):
                    results[node].append(self._add_node_name(element, node))

        return NodeResults(results, metrics, ignores)

    def _iter_node_kwargs(self, cluster_kwargs: _Kwargs) -> Iterable[Tuple[str, _Kwargs]]:
        """create kwargs for every nodes check function"""
        section_names = set(cluster_kwargs) - _NON_SECTION_KEYS
        all_nodes: Set[str] = {
            node for section_name in section_names for node in cluster_kwargs[section_name]
        }
        yield from ((node, kwargs)
                    for node, kwargs in self._extract_node_kwargs(sorted(all_nodes), cluster_kwargs)
                    if self._contains_data(kwargs))

    @staticmethod
    def _extract_node_kwargs(
        nodes: Iterable[str],
        cluster_kwargs: _Kwargs,
    ) -> Iterable[Tuple[str, _Kwargs]]:
        yield from ((n, {
            k: v if k in _NON_SECTION_KEYS else v.get(n) for k, v in cluster_kwargs.items()
        }) for n in nodes)

    @staticmethod
    def _contains_data(node_kwargs: _Kwargs) -> bool:
        return any(v is not None for k, v in node_kwargs.items() if k not in _NON_SECTION_KEYS)

    def _consume_checkresult(
        self,
        node: str,
        result_generator: CheckResult,
    ) -> Sequence[Union[Result, Metric, IgnoreResults]]:
        with load_host_value_store(
                node,
                store_changes=self._persist_value_store_changes,
        ) as value_store_manager:
            with value_store_manager.namespace(self._service_id):
                try:
                    return list(result_generator)
                except IgnoreResultsError as exc:
                    return [IgnoreResults(str(exc))]

    @staticmethod
    def _add_node_name(result: Result, node_name: str) -> Result:
        return Result(
            state=result.state,
            summary=f"[{node_name}]: {result.summary}",
            details='\n'.join(f"[{node_name}]: {line}" for line in result.details.splitlines()),
        )


def _noticeify(result: Result) -> Result:
    """Force notice text"""
    return Result(
        state=State.OK,
        notice=result.summary,
        details=f"{result.details}{STATE_MARKERS[int(result.state)]}",
    )
