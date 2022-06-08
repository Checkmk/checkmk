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
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Union,
)

from cmk.utils.type_defs import ClusterMode, state_markers

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
from cmk.base.api.agent_based.value_store import ValueStoreManager
from cmk.base.check_utils import ServiceID

_Kwargs = Mapping[str, Any]

_NON_SECTION_KEYS: Final = {"item", "params"}

_INF = float("inf")


class Selector(Protocol):
    def __call__(self, *a: State) -> State:
        ...


def _unfit_for_clustering(**_kw) -> CheckResult:
    """A cluster_check_function that displays a generic warning"""
    yield Result(
        state=State.UNKNOWN,
        summary=(
            "This service does not implement a native cluster mode. Please change your "
            "configuration using the rule 'Aggregation options for clustered services', "
            "and select one of the other available aggregation modes."
        ),
    )


def get_cluster_check_function(
    mode: ClusterMode,
    clusterization_parameters: Mapping[str, Any],
    *,
    service_id: ServiceID,
    plugin: CheckPlugin,
    persist_value_store_changes: bool,
    value_store_manager: ValueStoreManager,
) -> CheckFunction:
    if mode == "native":
        return plugin.cluster_check_function or _unfit_for_clustering

    executor = NodeCheckExecutor(
        service_id=service_id,
        persist_value_store_changes=persist_value_store_changes,
        value_store_manager=value_store_manager,
    )

    if mode == "failover":
        return partial(
            _cluster_check,
            clusterization_parameters=clusterization_parameters,
            executor=executor,
            check_function=plugin.check_function,
            label="active",
            selector=State.worst,
            levels_additional_nodes_count=(1, _INF),
            unpreferred_node_state=State.WARN,
        )

    if mode == "worst":
        return partial(
            _cluster_check,
            clusterization_parameters=clusterization_parameters,
            executor=executor,
            check_function=plugin.check_function,
            label="worst",
            selector=State.worst,
            levels_additional_nodes_count=(_INF, _INF),
            unpreferred_node_state=State.OK,
        )

    if mode == "best":
        return partial(
            _cluster_check,
            clusterization_parameters=clusterization_parameters,
            executor=executor,
            check_function=plugin.check_function,
            label="best",
            selector=State.best,
            levels_additional_nodes_count=(_INF, _INF),
            unpreferred_node_state=State.OK,
        )

    raise ValueError(mode)


def _cluster_check(
    *,
    clusterization_parameters: Mapping[str, Any],
    executor: "NodeCheckExecutor",
    check_function: Callable,
    label: str,
    selector: Selector,
    levels_additional_nodes_count: Tuple[float, float],
    unpreferred_node_state: State,
    **cluster_kwargs: Any,
) -> CheckResult:

    summarizer = Summarizer(
        node_results=executor(check_function, cluster_kwargs),
        label=label,
        selector=selector,
        preferred=clusterization_parameters.get("primary_node"),
        unpreferred_node_state=unpreferred_node_state,
    )
    if summarizer.is_empty():
        return summarizer.raise_for_ignores()

    yield from summarizer.primary_results()

    yield from summarizer.secondary_results(
        levels_additional_nodes_count=levels_additional_nodes_count
    )

    yield from summarizer.metrics(clusterization_parameters.get("metrics_node"))


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
        preferred: Optional[str],
        unpreferred_node_state: State,
    ) -> None:
        self._node_results = node_results
        self._label = label.title()
        self._selector = selector
        self._preferred = preferred
        self._unpreferred_node_state = unpreferred_node_state

        selected_nodes = self._get_selected_nodes(node_results.results, selector)
        # fallback: arbitrary, but comprehensible choice.
        self._pivoting = preferred if preferred in selected_nodes else sorted(selected_nodes)[0]

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
        if msgs := [
            f"[{node}] {', '.join(str(i) for i in ign)}"
            for node, ign in self._node_results.ignore_results.items()
            if ign
        ]:
            raise IgnoreResultsError(", ".join(msgs))

    def primary_results(self) -> Iterable[Result]:
        if self._preferred is None or self._preferred == self._pivoting:
            yield Result(state=State.OK, summary=f"{self._label}: [{self._pivoting}]")
        else:
            yield Result(
                state=self._unpreferred_node_state,
                summary=f"{self._label}: [{self._pivoting}]",
                details=f"{self._label}: [{self._pivoting}], Preferred node is [{self._preferred}]",
            )
        yield from self._node_results.results[self._pivoting]

    def secondary_results(
        self,
        *,
        levels_additional_nodes_count: Tuple[float, float],
    ) -> Iterable[Result]:
        secondary_nodes = sorted(n for n in self._node_results.results if n != self._pivoting)
        if not secondary_nodes:
            return

        yield Result(
            state=self._secondary_nodes_state(secondary_nodes, levels_additional_nodes_count),
            summary=f"Additional results from: {', '.join(f'[{n}]' for n in secondary_nodes)}",
        )
        yield from (
            Result(
                state=State.OK,
                notice=r.summary,
                details=f"{r.details}{state_markers[int(r.state)]}",
            )
            for node in secondary_nodes
            for r in self._node_results.results[node]
        )

    @staticmethod
    def _secondary_nodes_state(
        secondary_nodes: Sequence[str],
        levels: Tuple[float, float],
    ) -> State:
        count = len(secondary_nodes)
        return State.CRIT if count >= levels[1] else State(count >= levels[0])

    def metrics(self, node_name: Optional[str]) -> CheckResult:
        used_node = node_name or self._pivoting
        if not (metrics := self._node_results.metrics.get(used_node, ())):
            return
        yield Result(
            state=State.OK,
            notice=f"[{used_node}] Metrics: {', '.join(m.name for m in metrics)}",
        )
        yield from metrics


class NodeCheckExecutor:
    def __init__(
        self,
        *,
        service_id: ServiceID,
        persist_value_store_changes: bool,
        value_store_manager: ValueStoreManager,
    ) -> None:
        self._service_id = service_id
        self._persist_value_store_changes = persist_value_store_changes
        self._value_store_manager = value_store_manager

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

            elements = self._consume_checkresult(
                node, check_function(**kwargs), self._value_store_manager
            )
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
        yield from (
            (node, kwargs)
            for node, kwargs in self._extract_node_kwargs(sorted(all_nodes), cluster_kwargs)
            if self._contains_data(kwargs)
        )

    @staticmethod
    def _extract_node_kwargs(
        nodes: Iterable[str],
        cluster_kwargs: _Kwargs,
    ) -> Iterable[Tuple[str, _Kwargs]]:
        yield from (
            (n, {k: v if k in _NON_SECTION_KEYS else v.get(n) for k, v in cluster_kwargs.items()})
            for n in nodes
        )

    @staticmethod
    def _contains_data(node_kwargs: _Kwargs) -> bool:
        return any(v is not None for k, v in node_kwargs.items() if k not in _NON_SECTION_KEYS)

    def _consume_checkresult(
        self,
        node: str,
        result_generator: CheckResult,
        value_store_manager: ValueStoreManager,
    ) -> Sequence[Union[Result, Metric, IgnoreResults]]:
        with value_store_manager.namespace(self._service_id, host_name=node):
            try:
                return list(result_generator)
            except IgnoreResultsError as exc:
                return [IgnoreResults(str(exc))]

    @staticmethod
    def _add_node_name(result: Result, node_name: str) -> Result:
        return Result(
            state=result.state,
            summary="FAKE",
            details="\n".join(f"[{node_name}]: {line}" for line in result.details.splitlines()),
        )._replace(summary=result.summary)
