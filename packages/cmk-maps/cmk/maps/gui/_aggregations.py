#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The cmk.bi types this projects from are themselves ``Any``-typed
# (``NodeResultBundle.instance`` in cmk/bi/lib.py).
# mypy: disable-error-code="explicit-any"
"""Checkmk BI (Business Intelligence) lookups for the Maps SPA.

The Maps GUI runs in a full Checkmk request context, so it resolves BI
aggregations through Checkmk's own :class:`~cmk.gui.bi.bi_manager.BIManager` —
the request-scoped compiler + computer the BI views use — instead of the
Flask-free Maps daemon reimplementing the compile/compute pipeline. Because the
page runs as the logged-in user, per-user permissions apply automatically: the
computer fetches leaf states through the ``bi`` livestatus auth domain, and the
branch listing is additionally filtered to aggregations that touch a host the
user may see (aggregation titles can be as sensitive as SETUP folder names).

BI always targets the local site (the daemon did the same via
``_default_site_id()``); ``BIManager`` operates over the site's compiled
``bi_config`` just like the ``aggr`` views.

The three lookups mirror the daemon's former endpoints so the SPA keeps the same
behaviour:

* :func:`list_aggregations`  -> editor autocomplete
* :func:`aggregation_tree`   -> editor preview / drawer
* :func:`aggregation_states` -> the SPA's state poll

:mod:`cmk.maps.rest_api.internal` maps the dataclasses below onto the wire models
its endpoints publish.
"""

from dataclasses import dataclass
from typing import Literal

from cmk.bi.computer import BIAggregationFilter
from cmk.bi.lib import ABCBICompiledNode, NodeResultBundle
from cmk.bi.trees import BICompiledAggregation, BICompiledLeaf, BICompiledRule
from cmk.gui.bi.bi_manager import BIManager
from cmk.gui.logged_in import user
from cmk.gui.sites import live
from cmk.livestatus_client import MKLivestatusException
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.hosts import Hosts

MAX_TREE_DEPTH = 10


@dataclass(frozen=True, kw_only=True)
class AggregationInfo:
    """One resolved BI aggregation branch, for the editor autocomplete."""

    aggregation_id: str
    title: str
    pack_id: str
    function: str


@dataclass(frozen=True, kw_only=True)
class AggregationNode:
    """One node of a computed BI aggregation hierarchy."""

    name: str
    node_type: Literal["bi_aggregator", "bi_leaf"]
    state: int
    in_downtime: bool
    acknowledged: bool
    output: str
    children: list[AggregationNode]
    host_name: str | None = None
    service_description: str | None = None


@dataclass(frozen=True, kw_only=True)
class AggregationTreeResult:
    """A computed hierarchy, or why there is none.

    ``connection_ok`` is False only when livestatus was unreachable, so the
    editor can tell "no such aggregation" from "backend unavailable".
    """

    tree: AggregationNode | None
    connection_ok: bool


@dataclass(frozen=True, kw_only=True)
class AggregationState:
    """The computed state of one BI aggregation branch."""

    state: int
    output: str
    acknowledged: bool
    in_downtime: bool


def _scoped() -> bool:
    """Whether the caller's aggregation view must be contact-scoped.

    ``general.see_all`` users (admins) run unscoped; everyone else only sees
    aggregations that touch a host in their contact groups.
    """
    return not user.may("general.see_all")


def _visible_hosts() -> set[str]:
    """Host names the caller's livestatus auth scope may see."""
    return {str(row["name"]) for row in Query([Hosts.name]).fetchall(live())}


def _branch_required_hosts(node: ABCBICompiledNode) -> set[str]:
    """Host names a compiled node depends on (``required_elements`` -> (site, host))."""
    return {str(el.host_name) for el in node.required_elements}


def _bundle_to_node(bundle: NodeResultBundle, depth: int, max_depth: int) -> AggregationNode:
    """Recursively convert a cmk.bi NodeResultBundle into an AggregationNode."""
    instance = bundle.instance
    actual = bundle.actual_result
    node_type: Literal["bi_aggregator", "bi_leaf"] = "bi_leaf"
    name = ""
    host_name: str | None = None
    service_description: str | None = None
    if isinstance(instance, BICompiledRule):
        node_type = "bi_aggregator"
        name = str(instance.properties.title or "")
    elif isinstance(instance, BICompiledLeaf):
        service_description = instance.service_description or None
        host_name = instance.host_name or None
        name = instance.service_description or instance.host_name or ""

    return AggregationNode(
        name=name,
        node_type=node_type,
        state=int(actual.state),
        in_downtime=bool(actual.in_downtime),
        acknowledged=bool(actual.acknowledged),
        output=str(actual.output or ""),
        host_name=host_name,
        service_description=service_description,
        children=(
            []
            if depth >= max_depth
            else [_bundle_to_node(child, depth + 1, max_depth) for child in bundle.nested_results]
        ),
    )


def _results_to_states(
    results: list[tuple[BICompiledAggregation, list[NodeResultBundle]]],
    visible: set[str] | None,
) -> dict[str, AggregationState]:
    """Normalise BIComputer.compute_result_for_filter output into per-branch states.

    ``visible`` scopes the result to aggregations touching a host the caller may
    see (``None`` for ``general.see_all`` users) — the same guard the list/tree
    lookups apply, so a contact-scoped user cannot pull the live state/output of
    an aggregation outside their contact groups by guessing its title.
    """
    out: dict[str, AggregationState] = {}
    for _aggr, branches in results:
        for bundle in branches:
            instance = bundle.instance
            if not isinstance(instance, BICompiledRule):
                continue
            title = str(instance.properties.title or "")
            if not title:
                continue
            if visible is not None and not (_branch_required_hosts(instance) & visible):
                continue
            actual = bundle.actual_result
            out[title] = AggregationState(
                state=int(actual.state),
                output=str(actual.output or ""),
                acknowledged=bool(actual.acknowledged),
                in_downtime=bool(actual.in_downtime),
            )
    return out


def list_aggregations() -> list[AggregationInfo]:
    """All resolved BI aggregations (one entry per branch), for editor autocomplete.

    Iterates the compiled branches and returns their resolved titles (what
    ``aggr_single`` filters by and what users see in the BI UI), not the abstract
    bi_config templates with their ``Host $HOSTNAME$`` placeholders.

    The title *is* the identity here because that is BI's own addressing model:
    Checkmk's ``aggr_name`` view filter is an exact match on the title too (it is
    passed to ``BIAggregationFilter.aggr_titles``). Two aggregations sharing a
    title are therefore indistinguishable to a map binding just as they are to a
    view — this listing keeps the first of them, so a duplicate title shows up
    once in the editor's autocomplete. Worth stating as a known limitation in the
    user documentation rather than papering over here with an identity BI itself
    does not offer.
    """
    manager = BIManager()
    visible = _visible_hosts() if _scoped() else None
    out: list[AggregationInfo] = []
    seen: set[str] = set()
    for compiled_aggr in manager.compiler.compiled_aggregations.values():
        for branch in compiled_aggr.branches:
            title = str(branch.properties.title or "")
            if not title or title in seen:
                continue
            if visible is not None and not (_branch_required_hosts(branch) & visible):
                continue
            seen.add(title)
            out.append(
                AggregationInfo(
                    aggregation_id=title,
                    title=title,
                    pack_id=branch.pack_id,
                    function=branch.aggregation_function.kind(),
                )
            )
    out.sort(key=lambda entry: entry.title.lower())
    return out


def aggregation_tree(aggregation_name: str, max_depth: int) -> AggregationTreeResult:
    """The BI aggregation hierarchy, truncated at *max_depth*.

    The tree is ``None`` when no matching branch exists or the caller's scope
    hides it (a contact-scoped user must not pull the title/structure of an
    aggregation whose hosts they can't see, even with a guessed name).
    """
    try:
        return AggregationTreeResult(
            tree=_compute_tree(aggregation_name, max_depth), connection_ok=True
        )
    except MKLivestatusException:
        # A dead livestatus is a connection problem, not a missing aggregation —
        # let the editor show the "unavailable" hint. Other exceptions are
        # genuine faults and must surface as a crash report.
        return AggregationTreeResult(tree=None, connection_ok=False)


def _compute_tree(aggregation_name: str, max_depth: int) -> AggregationNode | None:
    if not aggregation_name:
        return None
    manager = BIManager()
    visible = _visible_hosts() if _scoped() else None
    bi_filter = BIAggregationFilter([], [], [], [aggregation_name], [], [])
    for _aggr, branches in manager.computer.compute_result_for_filter(bi_filter):
        for bundle in branches:
            instance = bundle.instance
            if not isinstance(instance, BICompiledRule):
                continue
            if str(instance.properties.title or "") != aggregation_name:
                continue
            if visible is not None and not (_branch_required_hosts(instance) & visible):
                return None
            return _bundle_to_node(bundle, depth=0, max_depth=max_depth)
    return None


def aggregation_states(aggregation_names: list[str]) -> dict[str, AggregationState]:
    """Current state per resolved BI aggregation name."""
    if not aggregation_names:
        return {}
    manager = BIManager()
    visible = _visible_hosts() if _scoped() else None
    bi_filter = BIAggregationFilter([], [], [], list(aggregation_names), [], [])
    return _results_to_states(manager.computer.compute_result_for_filter(bi_filter), visible)
