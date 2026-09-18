#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.bi.aggregation_functions import BIAggregationFunctionBest, BIAggregationFunctionWorst
from cmk.bi.lib import ABCBIAggregationFunction, ABCBICompiledNode
from cmk.bi.rule_interface import BIRuleProperties
from cmk.bi.trees import BICompiledLeaf, BICompiledRule
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.bi.view import _combine_branches, branches_differ, NodeIdentifier

WORST = BIAggregationFunctionWorst({"type": "worst", "count": 1, "restrict_state": 2})
BEST = BIAggregationFunctionBest({"type": "best", "count": 1, "restrict_state": 2})


def _properties(title: str) -> BIRuleProperties:
    return BIRuleProperties(
        {"title": title, "comment": "", "docu_url": "", "icon": "", "state_messages": {}}
    )


def _leaf(service: str) -> BICompiledLeaf:
    return BICompiledLeaf(host_name=HostName("heute"), service_description=service, site_id="heute")


def _rule(
    title: str,
    *,
    aggregation_function: ABCBIAggregationFunction = WORST,
    nodes: Sequence[ABCBICompiledNode] | None = None,
) -> BICompiledRule:
    # BICompiledRule wants an invariant list, so the covariant Sequence the
    # callers find convenient has to be copied into one.
    node_list: list[ABCBICompiledNode] = list(nodes) if nodes is not None else [_leaf("CPU")]
    return BICompiledRule(
        rule_id="hostcheck",
        pack_id="default",
        nodes=node_list,
        required_hosts=[(SiteId("heute"), HostName("heute"))],
        properties=_properties(title),
        aggregation_function=aggregation_function,
        node_visualization={"style_config": {}, "type": "none"},
    )


def _markers(branch: BICompiledRule) -> dict[NodeIdentifier, str | None]:
    return {
        info.id: None if info.node_ref.frozen_marker is None else info.node_ref.frozen_marker.status
        for info in branch.get_identifiers((), set())
    }


class TestBranchesDiffer:
    def test_identical_branches_do_not_differ(self) -> None:
        assert branches_differ(_rule("Host heute"), _rule("Host heute")) is False

    def test_changed_aggregation_function_differs(self) -> None:
        assert (
            branches_differ(
                _rule("Host heute", aggregation_function=BEST),
                _rule("Host heute", aggregation_function=WORST),
            )
            is True
        )

    def test_changed_shape_differs(self) -> None:
        assert (
            branches_differ(
                _rule("Host heute", nodes=[_leaf("CPU")]),
                _rule("Host heute", nodes=[_leaf("CPU"), _leaf("Memory")]),
            )
            is True
        )

    def test_does_not_mutate_its_arguments(self) -> None:
        frozen = _rule("Host heute", aggregation_function=BEST)
        live = _rule("Host heute", aggregation_function=WORST)

        assert branches_differ(frozen, live) is True

        assert set(_markers(frozen).values()) == {None}
        assert set(_markers(live).values()) == {None}
        assert len(frozen.nodes) == 1


class TestCombineBranches:
    def test_identical_branches_are_equal(self) -> None:
        frozen = _rule("Host heute")

        assert _combine_branches(frozen, _rule("Host heute")) is True
        assert set(_markers(frozen).values()) == {None}

    def test_changed_aggregation_function_is_reported(self) -> None:
        """SUP-30030: the tree shape is identical, only the function changed."""
        frozen = _rule("Host heute", aggregation_function=BEST)
        live = _rule("Host heute", aggregation_function=WORST)

        assert _combine_branches(frozen, live) is False
        assert _markers(frozen)[((1, "Host heute"),)] == "changed"

    def test_changed_nested_rule_marks_its_ancestor(self) -> None:
        def branch(aggregation_function: ABCBIAggregationFunction) -> BICompiledRule:
            return _rule(
                "Host heute",
                nodes=[_rule("Performance", aggregation_function=aggregation_function)],
            )

        frozen = branch(BEST)

        assert _combine_branches(frozen, branch(WORST)) is False
        markers = _markers(frozen)
        assert markers[((1, "Host heute"),)] == "parent"
        assert markers[((1, "Host heute"), (1, "Performance"))] == "changed"

    def test_changed_rule_property_is_reported(self) -> None:
        frozen = _rule("Host heute")
        live = _rule("Host heute")
        live.properties.state_messages = {"2": "call the on-call"}

        assert _combine_branches(frozen, live) is False
        assert _markers(frozen)[((1, "Host heute"),)] == "changed"

    def test_changed_node_that_is_also_a_parent_keeps_its_own_change(self) -> None:
        """A reconfigured node must not be reduced to "something below me differs"."""
        frozen = _rule("Host heute", aggregation_function=BEST, nodes=[_leaf("CPU")])
        live = _rule(
            "Host heute", aggregation_function=WORST, nodes=[_leaf("CPU"), _leaf("Memory")]
        )

        assert _combine_branches(frozen, live) is False
        assert _markers(frozen)[((1, "Host heute"),)] == "changed"

    def test_missing_node_is_still_reported(self) -> None:
        frozen = _rule("Host heute", nodes=[_leaf("CPU"), _leaf("Memory")])
        live = _rule("Host heute", nodes=[_leaf("CPU")])

        assert _combine_branches(frozen, live) is False
        markers = _markers(frozen)
        assert markers[((1, "Host heute"),)] == "parent"
        assert markers[((1, "Host heute"), (1, "heute", "Memory"))] == "missing"
