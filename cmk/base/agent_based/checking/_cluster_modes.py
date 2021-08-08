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
    NamedTuple,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Union,
)

from cmk.utils.type_defs import ClusterMode, state_markers as STATE_MARKERS

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
from cmk.base.api.agent_based.value_store import load_host_value_store
from cmk.base.check_utils import ServiceID

_Kwargs = Mapping[str, Any]

_NON_SECTION_KEYS: Final = {'item', 'params'}


class Selector(Protocol):
    def __call__(self, *a: State) -> State:
        ...


def _unfit_for_clustering(**_kw) -> CheckResult:
    """A cluster_check_function that displays a generic warning"""
    yield Result(
        state=State.UNKNOWN,
        summary=("This service does not implement a native cluster mode. Please change your "
                 "configuration using the rule 'Aggregation options for clustered services', "
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
            _cluster_check,
            clusterization_parameters=clusterization_parameters,
            executor=executor,
            check_function=plugin.check_function,
            label="worst",
            selector=State.worst,
        )

    raise ValueError(mode)


def _cluster_check(
    *,
    clusterization_parameters: Mapping[str, Any],
    executor: "NodeCheckExecutor",
    check_function: Callable,
    label: str,
    selector: Selector,
    **cluster_kwargs: Any,
) -> CheckResult:

    summarizer = Summarizer(
        node_results=executor(check_function, cluster_kwargs),
        label=label,
        selector=selector,
    )
    if summarizer.is_empty():
        return summarizer.raise_for_ignores()

    yield from summarizer.primary_results()

    yield from summarizer.secondary_results()

    yield from summarizer.metrics()


class NodeResults(NamedTuple):
    results: Mapping[str, Sequence[Result]]
    metrics: Mapping[str, Sequence[Metric]]
    ignore_results: Mapping[str, Sequence[IgnoreResults]]


class Summarizer:
    def __init__(
        self,
        *,
        node_results: NodeResults,
        label: str,
        selector: Selector,
    ) -> None:
        self._node_results = node_results
        self._label = label.title()
        self._selector = selector

        selected_nodes = self._get_selected_nodes(node_results.results, selector)
        # fallback: arbitrary, but comprehensible choice.
        self._pivoting = sorted(selected_nodes)[0]

    @staticmethod
    def _get_selected_nodes(
        results_map: Mapping[str, Sequence[Result]],
        selector: Selector,
    ) -> Set[str]:
        """Determine the best/worst nodes names"""
        nodes_by_states = defaultdict(set)
        for node, results in ((n, r) for n, r in results_map.items() if r):
            nodes_by_states[State.worst(*(r.state for r in results))].add(node)

        return nodes_by_states[selector(*nodes_by_states)] if nodes_by_states else set(results_map)

    def is_empty(self) -> bool:
        return not any(self._node_results.results.values())

    def raise_for_ignores(self) -> None:
        if (msgs := [
                f"[{node}] {', '.join(str(i) for i in ign)}"
                for node, ign in self._node_results.ignore_results.items()
                if ign
        ]):
            raise IgnoreResultsError(", ".join(msgs))

    def primary_results(self) -> Iterable[Result]:
        yield Result(state=State.OK, summary=f"{self._label}: [{self._pivoting}]")
        yield from self._node_results.results[self._pivoting]

    def secondary_results(self) -> Iterable[Result]:
        secondary_nodes = sorted(n for n in self._node_results.results if n != self._pivoting)
        if not secondary_nodes:
            return

        yield Result(
            state=State.OK,
            summary=f"Additional results from: {', '.join(f'[{n}]' for n in secondary_nodes)}",
        )
        yield from (Result(
            state=State.OK,
            notice=r.summary,
            details=f"{r.details}{STATE_MARKERS[int(r.state)]}",
        ) for node in secondary_nodes for r in self._node_results.results[node])

    def metrics(self) -> Iterable[Metric]:
        return self._node_results.metrics[self._pivoting]


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
        results = {}
        metrics = {}
        ignores = {}

        for node, kwargs in self._iter_node_kwargs(cluster_kwargs):

            elements = self._consume_checkresult(node, check_function(**kwargs))
            metrics[node] = [e for e in elements if isinstance(e, Metric)]
            ignores[node] = [e for e in elements if isinstance(e, IgnoreResults)]
            results[node] = [
                self._add_node_name(e, node) for e in elements if isinstance(e, Result)
            ]

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
            summary=result.summary,
            details='\n'.join(f"[{node_name}]: {line}" for line in result.details.splitlines()),
        )
