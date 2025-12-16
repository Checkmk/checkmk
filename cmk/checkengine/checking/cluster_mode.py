#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compute the cluster check function from the plug-in and parameters."""

# mypy: disable-error-code="type-arg"

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import partial
from typing import Any, Final, Literal, NamedTuple, Protocol

from cmk.agent_based.v1 import IgnoreResults, IgnoreResultsError, Metric, Result, State
from cmk.agent_based.v2 import CheckResult
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.checkresults import state_markers
from cmk.checkengine.plugins import CheckPlugin, ServiceID
from cmk.checkengine.value_store import ValueStoreManager

_Kwargs = Mapping[str, Any]

_NON_SECTION_KEYS: Final = {"item", "params"}

_INF = float("inf")

ClusterMode = Literal["native", "failover", "worst", "best"]


class Selector(Protocol):
    def __call__(self, *a: State) -> State: ...


def _unfit_for_clustering(**_kw: object) -> CheckResult:
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
    value_store_manager: ValueStoreManager,
) -> Callable[..., Iterable[object]]:
    if mode == "native":
        return plugin.cluster_check_function or _unfit_for_clustering

    executor = NodeCheckExecutor(
        service_id=service_id,
        value_store_manager=value_store_manager,
    )

    if mode == "failover":
        return partial(
            _cluster_check,
            clusterization_parameters=clusterization_parameters,
            executor=executor,
            check_function=plugin.check_function,
            cluster_mode=mode,
            additional_nodes_label="More than one node are reporting results:",
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
            cluster_mode=mode,
            additional_nodes_label="Aggregating results from host(s):",
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
            cluster_mode=mode,
            additional_nodes_label="Aggregating results from host(s):",
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
    cluster_mode: ClusterMode,
    additional_nodes_label: str,
    selector: Selector,
    levels_additional_nodes_count: tuple[float, float],
    unpreferred_node_state: State,
    **cluster_kwargs: Any,
) -> CheckResult:
    summarizer = Summarizer(
        node_results=executor(check_function, cluster_kwargs),
        cluster_mode=cluster_mode,
        additional_node_label=additional_nodes_label,
        selector=selector,
        preferred=clusterization_parameters.get("primary_node"),
        unpreferred_node_state=unpreferred_node_state,
        levels_additional_nodes_count=levels_additional_nodes_count,
        metrics_node=clusterization_parameters.get("metrics_node"),
    )
    yield from summarizer()
    return None


class NodeResults(NamedTuple):
    results: Mapping[HostName, Sequence[Result]]
    metrics: Mapping[HostName, Sequence[Metric]]
    ignore_results: Mapping[HostName, Sequence[IgnoreResults]]


class Summarizer:
    def __init__(
        self,
        *,
        node_results: NodeResults,
        cluster_mode: ClusterMode,
        selector: Selector,
        preferred: HostName | None,
        unpreferred_node_state: State,
        levels_additional_nodes_count: tuple[float, float],
        metrics_node: HostName | None = None,
        additional_node_label: str = "Additional results from:",
    ) -> None:
        self._node_results = node_results
        self._cluster_mode = cluster_mode
        self._additional_node_label = additional_node_label
        self._selector = selector
        self._preferred = preferred
        self._unpreferred_node_state = unpreferred_node_state
        self._levels_additional_nodes_count = levels_additional_nodes_count
        self._metrics_node = metrics_node

        selected_nodes = self._get_selected_nodes(node_results.results, selector)
        # fallback: arbitrary, but comprehensible choice.
        self._pivoting = preferred if preferred in selected_nodes else sorted(selected_nodes)[0]

        if self._cluster_mode == "failover":
            # If we are in failover mode, always pick preferred node
            self._active = (
                preferred if preferred in node_results.results else sorted(selected_nodes)[0]
            )
        else:
            self._active = self._pivoting

        self._secondary_nodes = sorted(
            node
            for node, results in self._node_results.results.items()
            if node != self._pivoting and results
        )

    def __call__(self) -> CheckResult:
        if self.is_empty():
            self.raise_for_ignores()
            return

        yield from self.general_results()
        yield from self.primary_results()
        yield from self.secondary_results()
        yield from self.metrics()

    @property
    def _label(self) -> str:
        return "Best" if self._cluster_mode == "best" else "Worst"

    @staticmethod
    def _get_selected_nodes(
        results_map: Mapping[HostName, Sequence[Result]],
        selector: Selector,
    ) -> set[HostName]:
        """Determine the best/worst nodes names"""
        nodes_by_states = defaultdict(set)
        for node, results in ((n, r) for n, r in results_map.items() if r):
            nodes_by_states[State.worst(*(r.state for r in results))].add(node)

        return nodes_by_states[selector(*nodes_by_states)] if nodes_by_states else set(results_map)

    def is_empty(self) -> bool:
        return not any(self._node_results.results.values())

    def is_preferred_node_active(self) -> bool:
        # FYI: In order to be really active, the node has to produce a result, too.
        return self._preferred is None or (
            self._preferred == self._active and len(self._node_results.results[self._preferred]) > 0
        )

    def raise_for_ignores(self) -> None:
        if msgs := [
            f"[{node}] {', '.join(str(i) for i in ign)}"
            for node, ign in self._node_results.ignore_results.items()
            if ign
        ]:
            raise IgnoreResultsError(", ".join(msgs))

    def general_results(self) -> Iterable[Result]:
        """
        Generate results about the cluster configuration
        """
        details_header = [
            f"Cluster mode: {self._cluster_mode.title()}",
            f"{self._label} node: {self._pivoting}",
        ]
        if self._preferred:
            details_header.append(f"Preferred node: {self._preferred}")

        yield Result(state=State.OK, notice="Cluster details", details=", ".join(details_header))

        if not self.is_preferred_node_active():
            yield Result(
                state=self._unpreferred_node_state,
                notice="Preferred node is not active",
            )

        if not self._secondary_nodes:
            return

        summary = f"{self._additional_node_label} {', '.join(self._node_results.results)}"
        yield Result(
            state=self._secondary_nodes_state(self._levels_additional_nodes_count),
            notice=summary,
            details="\n" + summary,
        )

    def primary_results(self) -> Iterable[Result]:
        """
        Return the results from the primary/pivoting/active node
        """
        results = self._node_results.results[self._pivoting]
        details = [f"Results from node: {self._pivoting}"] + [
            self._add_state_marker_to_details(r.details, state_markers[int(r.state)])
            for r in results
        ]

        state = State.worst(*(r.state for r in results))
        summary = ", ".join(self._remove_state_markers(r.summary) for r in results if r.summary)

        if state is State.OK and not summary:
            yield Result(
                state=state,
                notice=f"Results from node: {self._pivoting}",
                details="\n" + "\n".join(details),
            )
        else:
            yield Result(state=state, summary=summary, details="\n" + "\n".join(details))

    def secondary_results(self) -> Iterable[Result]:
        """
        Return the results from the remaining nodes
        """
        for node in self._secondary_nodes:
            yield Result(
                state=State.OK,
                notice=f"Results from node: {node}",
                details=f"\nResults from node: {node}\n"
                + "\n".join(
                    self._add_state_marker_to_details(r.details, state_markers[int(r.state)])
                    for r in self._node_results.results[node]
                ),
            )

    @staticmethod
    def _remove_state_markers(summary_or_details: str) -> str:
        # Legacy checks may already add state markers to details.
        # TODO: Remove this workaround after all legacy checks are converted.
        cleaned = summary_or_details
        for m in state_markers:
            cleaned = cleaned.replace(m, "")
        return cleaned

    @staticmethod
    def _add_state_marker_to_details(details: str, marker: str) -> str:
        # Legacy checks may already add state markers to details.
        # TODO: Remove this workaround after all legacy checks are converted.
        if marker in details:
            return details

        return f"{Summarizer._remove_state_markers(details)}{marker}"

    def _secondary_nodes_state(
        self,
        levels: tuple[float, float],
    ) -> State:
        count = len(self._secondary_nodes)
        return State.CRIT if count >= levels[1] else State(count >= levels[0])

    def metrics(self) -> CheckResult:
        used_node = self._metrics_node or self._pivoting
        if not (metrics := self._node_results.metrics.get(used_node, ())):
            return

        yield Result(
            state=State.OK,
            notice=f"Metrics from node {used_node}: {', '.join(m.name for m in metrics)}",
        )
        yield from metrics


class NodeCheckExecutor:
    def __init__(
        self,
        *,
        service_id: ServiceID,
        value_store_manager: ValueStoreManager,
    ) -> None:
        self._service_id = service_id
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
            results[node] = [e for e in elements if isinstance(e, Result)]

        return NodeResults(results, metrics, ignores)

    def _iter_node_kwargs(self, cluster_kwargs: _Kwargs) -> Iterable[tuple[HostName, _Kwargs]]:
        """create kwargs for every nodes check function"""
        section_names = set(cluster_kwargs) - _NON_SECTION_KEYS
        all_nodes: set[HostName] = {
            node for section_name in section_names for node in cluster_kwargs[section_name]
        }
        yield from (
            (node, kwargs)
            for node, kwargs in self._extract_node_kwargs(sorted(all_nodes), cluster_kwargs)
            if self._contains_data(kwargs)
        )

    @staticmethod
    def _extract_node_kwargs(
        nodes: Iterable[HostName],
        cluster_kwargs: _Kwargs,
    ) -> Iterable[tuple[HostName, _Kwargs]]:
        yield from (
            (n, {k: v if k in _NON_SECTION_KEYS else v.get(n) for k, v in cluster_kwargs.items()})
            for n in nodes
        )

    @staticmethod
    def _contains_data(node_kwargs: _Kwargs) -> bool:
        return any(v is not None for k, v in node_kwargs.items() if k not in _NON_SECTION_KEYS)

    def _consume_checkresult(
        self,
        node: HostName,
        result_generator: CheckResult,
        value_store_manager: ValueStoreManager,
    ) -> Sequence[Result | Metric | IgnoreResults]:
        with value_store_manager.namespace(self._service_id, host_name=node):
            try:
                return list(result_generator)
            except IgnoreResultsError as exc:
                return [IgnoreResults(str(exc))]
