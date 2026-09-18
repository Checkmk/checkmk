#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from livestatus import SiteId

from cmk.utils.hostaddress import HostName

from cmk.gui.bi.view import (
    branches_differ,
    changed_node_details,
    combine_branches,
    NodeIdentifier,
)

from cmk.bi.aggregation_functions import BIAggregationFunctionBest, BIAggregationFunctionWorst
from cmk.bi.lib import ABCBIAggregationFunction, ABCBICompiledNode
from cmk.bi.rule_interface import BIRuleProperties
from cmk.bi.trees import BICompiledLeaf, BICompiledRule

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
        live = _rule("Host heute")

        assert combine_branches(live, _rule("Host heute")) is True
        assert set(_markers(live).values()) == {None}

    def test_changed_aggregation_function_is_reported(self) -> None:
        """SUP-30030: the tree shape is identical, only the function changed."""
        live = _rule("Host heute", aggregation_function=WORST)
        frozen = _rule("Host heute", aggregation_function=BEST)

        assert combine_branches(live, frozen) is False
        assert _markers(live)[((1, "Host heute"),)] == "changed"

    def test_changed_nested_rule_marks_its_ancestor(self) -> None:
        def branch(aggregation_function: ABCBIAggregationFunction) -> BICompiledRule:
            return _rule(
                "Host heute",
                nodes=[_rule("Performance", aggregation_function=aggregation_function)],
            )

        live = branch(WORST)

        assert combine_branches(live, branch(BEST)) is False
        markers = _markers(live)
        assert markers[((1, "Host heute"),)] == "parent"
        assert markers[((1, "Host heute"), (1, "Performance"))] == "changed"

    def test_changed_rule_property_is_reported(self) -> None:
        live = _rule("Host heute")
        frozen = _rule("Host heute")
        frozen.properties.state_messages = {"2": "call the on-call"}

        assert combine_branches(live, frozen) is False
        assert _markers(live)[((1, "Host heute"),)] == "changed"

    def test_node_added_since_freezing_is_reported(self) -> None:
        live = _rule("Host heute", nodes=[_leaf("CPU"), _leaf("Memory")])
        frozen = _rule("Host heute", nodes=[_leaf("CPU")])

        assert combine_branches(live, frozen) is False
        markers = _markers(live)
        assert markers[((1, "Host heute"),)] == "parent"
        assert markers[((1, "Host heute"), (1, "heute", "Memory"))] == "new"

    def test_node_removed_since_freezing_is_grafted_in_and_reported(self) -> None:
        live = _rule("Host heute", nodes=[_leaf("CPU")])
        frozen = _rule("Host heute", nodes=[_leaf("CPU"), _leaf("Memory")])

        assert combine_branches(live, frozen) is False
        markers = _markers(live)
        assert markers[((1, "Host heute"),)] == "parent"
        assert markers[((1, "Host heute"), (1, "heute", "Memory"))] == "missing"
        # Grafted into the rendered tree, so the deletion stays visible.
        assert len(live.nodes) == 2


class TestChangedNodeDetails:
    def test_changed_aggregation_function(self) -> None:
        assert (
            changed_node_details(
                _rule("Host heute", aggregation_function=WORST),
                _rule("Host heute", aggregation_function=BEST),
            )
            == "aggregation function: best \u2192 worst"
        )

    def test_removed_value_is_reported_as_removed(self) -> None:
        frozen = _rule("Host heute")
        frozen.properties.state_messages = {"2": "call the on-call"}

        # The nested key is a configuration name and stays verbatim.
        assert changed_node_details(_rule("Host heute"), frozen) == (
            "properties state_messages 2: removed"
        )

    def test_a_whole_subconfiguration_is_not_spelled_out(self) -> None:
        live = _rule("Host heute")
        live.node_visualization = {"style_config": {"padding": "x" * 500}, "type": "none"}

        details = changed_node_details(live, _rule("Host heute"))

        assert details == "node visualization style_config padding: added"

    def test_a_long_value_is_capped(self) -> None:
        live = _rule("Host heute")
        frozen = _rule("Host heute")
        live.properties.comment = "y" * 500
        frozen.properties.comment = "z" * 500

        details = changed_node_details(live, frozen)

        assert details.startswith("properties comment: zzz")
        assert "..." in details
        assert len(details) < 120

    def test_identical_nodes_have_no_details(self) -> None:
        assert changed_node_details(_rule("Host heute"), _rule("Host heute")) == ""

    def test_details_survive_when_the_node_is_also_a_parent(self) -> None:
        """SUP-30030 review: the parent marker must not swallow the node's own change."""
        live = _rule(
            "Host heute", aggregation_function=WORST, nodes=[_leaf("CPU"), _leaf("Memory")]
        )
        frozen = _rule("Host heute", aggregation_function=BEST, nodes=[_leaf("CPU")])

        assert combine_branches(live, frozen) is False

        marker = live.frozen_marker
        assert marker is not None
        assert marker.status == "changed"
        assert marker.details == "aggregation function: best \u2192 worst"

    def test_combine_branches_puts_the_details_on_the_marker(self) -> None:
        live = _rule("Host heute", aggregation_function=WORST)

        assert combine_branches(live, _rule("Host heute", aggregation_function=BEST)) is False

        marker = live.frozen_marker
        assert marker is not None
        assert marker.status == "changed"
        assert marker.details == "aggregation function: best \u2192 worst"
