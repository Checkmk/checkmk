#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ``NodeResultBundle.instance`` (cmk/bi/lib.py) is ``Any``-typed, which leaks
# into every helper building one here.
# mypy: disable-error-code="explicit-any"
"""Wire-contract tests for the GUI BI-aggregation lookups backing the Maps SPA.

These functions are the GUI-side replacement for the daemon's in-process cmk.bi
compute: they drive Checkmk's ``BIManager`` (compiler + computer) and project its
results into the typed shapes ``cmk.maps.rest_api.internal`` publishes. The BI
pipeline itself is covered by the BI tests; what we pin here is the projection —
branch listing (dedup, sort, scope filter, function label), the tree node shape,
and the per-branch state.
"""

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest

from cmk.bi.lib import NodeComputeResult, NodeResultBundle, RequiredBIElement
from cmk.bi.trees import BICompiledAggregation, BICompiledLeaf, BICompiledRule
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.livestatus_client import MKLivestatusException
from cmk.maps.gui import _aggregations
from cmk.maps.gui._aggregations import AggregationInfo, AggregationState


def _compute_result(
    state: int, output: str = "", *, in_downtime: bool = False, acknowledged: bool = False
) -> NodeComputeResult:
    return NodeComputeResult(
        state=state,
        in_downtime=in_downtime,
        acknowledged=acknowledged,
        output=output,
        in_service_period=True,
        state_messages={},
        custom_infos={},
    )


def _leaf(
    host: str, svc: str | None, state: int, output: str = "", *, in_downtime: bool = False
) -> NodeResultBundle:
    """A NodeResultBundle whose instance is a host/service leaf (not a rule).

    The instance is spec'd to the real ``BICompiledLeaf`` so the projection's
    ``isinstance`` type dispatch resolves it as a leaf.
    """
    instance = MagicMock(spec=BICompiledLeaf)
    instance.host_name = host
    instance.service_description = svc
    return NodeResultBundle(
        actual_result=_compute_result(state, output, in_downtime=in_downtime),
        assumed_result=None,
        nested_results=[],
        instance=instance,
    )


def _rule(
    title: str, state: int, children: list[NodeResultBundle], *, in_downtime: bool = False
) -> NodeResultBundle:
    """A NodeResultBundle whose instance is a compiled rule (aggregator)."""
    instance = MagicMock(spec=BICompiledRule)
    instance.properties = SimpleNamespace(title=title)
    return NodeResultBundle(
        actual_result=_compute_result(state, in_downtime=in_downtime, acknowledged=True),
        assumed_result=None,
        nested_results=children,
        instance=instance,
    )


def _results(
    branches: list[NodeResultBundle],
) -> list[tuple[BICompiledAggregation, list[NodeResultBundle]]]:
    """Wrap top-level branches in the (aggregation, branches) shape the computer returns."""
    aggr = cast(BICompiledAggregation, MagicMock(spec=BICompiledAggregation))
    return [(aggr, branches)]


def test_bundle_to_node_maps_rule_and_leaf() -> None:
    tree = _aggregations._bundle_to_node(  # noqa: SLF001
        _rule("Host db1", 2, [_leaf("db1", "CPU", 1, "warn"), _leaf("db1", None, 0)]),
        depth=0,
        max_depth=10,
    )
    assert tree.name == "Host db1"
    assert tree.node_type == "bi_aggregator"
    assert tree.state == 2
    assert tree.acknowledged is True
    assert [child.name for child in tree.children] == ["CPU", "db1"]
    leaf = tree.children[0]
    assert leaf.node_type == "bi_leaf"
    assert leaf.host_name == "db1"
    assert leaf.service_description == "CPU"
    assert leaf.output == "warn"


def test_bundle_to_node_truncates_at_max_depth() -> None:
    tree = _aggregations._bundle_to_node(  # noqa: SLF001
        _rule("root", 0, [_leaf("h", "s", 0)]), depth=0, max_depth=0
    )
    assert tree.children == []


def test_results_to_states_projects_per_branch() -> None:
    # The branches are the top-level rules (with a title); leaves live nested
    # inside and are not keyed here.
    results = _results([_rule("Host a", 2, []), _rule("Host b", 1, [])])
    states = _aggregations._results_to_states(results, None)  # noqa: SLF001
    assert states["Host a"].state == 2
    assert states["Host a"].acknowledged is True
    assert states["Host b"].state == 1


def test_results_to_states_reads_in_downtime_from_actual_result() -> None:
    # The downtime flag comes from ``actual_result.in_downtime``.
    results = _results([_rule("Host a", 2, [], in_downtime=True)])
    assert _aggregations._results_to_states(results, None)["Host a"].in_downtime is True  # noqa: SLF001


def _fake_manager(
    monkeypatch: pytest.MonkeyPatch,
    *,
    compiled: dict[str, object] | None = None,
    results: object = None,
) -> None:
    manager = SimpleNamespace(
        compiler=SimpleNamespace(compiled_aggregations=compiled or {}),
        computer=SimpleNamespace(compute_result_for_filter=lambda _f: results),
    )
    monkeypatch.setattr(_aggregations, "BIManager", lambda: manager)


def _branch(title: str, pack_id: str, function: str) -> MagicMock:
    branch = MagicMock(spec=BICompiledRule)
    branch.properties = SimpleNamespace(title=title)
    branch.pack_id = pack_id
    branch.aggregation_function = SimpleNamespace(kind=lambda: function)
    branch.required_elements = {RequiredBIElement(SiteId("SITE"), HostName("h1"), None)}
    return branch


def _compiled_aggr(pack_id: str, function: str, titles: list[str]) -> SimpleNamespace:
    # pack_id and the aggregation function live on each compiled *branch*
    # (BICompiledRule), not on the aggregation container.
    return SimpleNamespace(branches=[_branch(t, pack_id, function) for t in titles])


def test_list_aggregations_dedups_sorts_and_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_aggregations, "_scoped", lambda: False)
    _fake_manager(
        monkeypatch,
        compiled={
            "p1": _compiled_aggr("pack1", "worst", ["Zeta", "Alpha", "Alpha"]),
        },
    )
    out = _aggregations.list_aggregations()
    assert [entry.title for entry in out] == ["Alpha", "Zeta"]  # deduped + sorted
    assert out[0] == AggregationInfo(
        aggregation_id="Alpha", title="Alpha", pack_id="pack1", function="worst"
    )


def test_list_aggregations_scope_filters_invisible_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_aggregations, "_scoped", lambda: True)
    monkeypatch.setattr(_aggregations, "_visible_hosts", lambda: {"other"})
    _fake_manager(
        monkeypatch,
        compiled={"p1": _compiled_aggr("pack1", "worst", ["Alpha"])},
    )
    # The only branch requires host "h1", which is not visible -> filtered out.
    assert _aggregations.list_aggregations() == []


def test_aggregation_tree_matches_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_aggregations, "_scoped", lambda: False)
    _fake_manager(
        monkeypatch,
        results=_results([_rule("Host db1", 2, [_leaf("db1", "CPU", 1)])]),
    )
    result = _aggregations.aggregation_tree("Host db1", 10)
    assert result.connection_ok is True
    assert result.tree is not None
    assert result.tree.name == "Host db1"
    assert result.tree.children[0].name == "CPU"


def test_aggregation_tree_returns_none_for_unknown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_aggregations, "_scoped", lambda: False)
    _fake_manager(monkeypatch, results=_results([_rule("Host db1", 2, [])]))
    assert _aggregations.aggregation_tree("Host other", 10).tree is None


def test_aggregation_tree_empty_name_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    # No BIManager should be constructed for an empty name.
    monkeypatch.setattr(
        _aggregations, "BIManager", lambda: pytest.fail("BIManager must not be built")
    )
    assert _aggregations.aggregation_tree("", 10).tree is None


def test_aggregation_states_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_aggregations, "_scoped", lambda: False)
    _fake_manager(monkeypatch, results=_results([_rule("Host a", 2, [])]))
    states = _aggregations.aggregation_states(["Host a"])
    assert states == {
        "Host a": AggregationState(state=2, output="", acknowledged=True, in_downtime=False)
    }


def _scoped_states_bundle(host: str) -> NodeResultBundle:
    bundle = _rule("Host a", 2, [])
    bundle.instance.required_elements = {RequiredBIElement(SiteId("SITE"), HostName(host), None)}
    return bundle


def test_aggregation_states_scope_hides_invisible_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: a contact-scoped user must not get the live state/output of an
    # aggregation whose required host they cannot see, even by guessing its title
    # (the list/tree endpoints already refuse this).
    monkeypatch.setattr(_aggregations, "_scoped", lambda: True)
    monkeypatch.setattr(_aggregations, "_visible_hosts", lambda: {"other"})
    _fake_manager(monkeypatch, results=_results([_scoped_states_bundle("h1")]))
    assert _aggregations.aggregation_states(["Host a"]) == {}


def test_aggregation_states_scope_keeps_visible_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_aggregations, "_scoped", lambda: True)
    monkeypatch.setattr(_aggregations, "_visible_hosts", lambda: {"h1"})
    _fake_manager(monkeypatch, results=_results([_scoped_states_bundle("h1")]))
    assert "Host a" in _aggregations.aggregation_states(["Host a"])


def test_aggregation_states_empty_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _aggregations, "BIManager", lambda: pytest.fail("BIManager must not be built")
    )
    assert _aggregations.aggregation_states([]) == {}


def test_aggregation_tree_reports_a_dead_livestatus(monkeypatch: pytest.MonkeyPatch) -> None:
    # A dead livestatus must read as "backend unavailable", not "no such
    # aggregation" — the editor shows a different hint for each.
    def _raise(_name: str, _depth: int) -> None:
        raise MKLivestatusException("no socket")

    monkeypatch.setattr(_aggregations, "_compute_tree", _raise)
    result = _aggregations.aggregation_tree("Host a", 10)
    assert result.tree is None
    assert result.connection_ok is False
