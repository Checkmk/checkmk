#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.bi.actions import BIStateOfServiceAction
from cmk.bi.aggregation_functions import (
    BIAggregationFunctionWorst,
    BIAggregationFunctionWorstSerialized,
)
from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.lib import BIAggregationComputationOptions, NodeComputeResult
from cmk.bi.packs import BIAggregationPacks
from cmk.bi.rule import BIRule
from cmk.bi.rule_interface import BIRuleProperties
from cmk.bi.searcher import BISearcher
from cmk.bi.trees import BICompiledRule
from cmk.bi.type_defs import ComputationConfigDict

from .bi_test_data import sample_config


def test_load_sample_config_rule(bi_packs_sample_config: BIAggregationPacks) -> None:
    applications_rule = bi_packs_sample_config.get_rule("networking")
    assert isinstance(applications_rule, BIRule)
    action = applications_rule.nodes[0].action
    assert isinstance(action, BIStateOfServiceAction)
    assert action.service_regex == "NFS|Interface|TCP"


def test_sample_config_networking_rule(
    bi_packs_sample_config: BIAggregationPacks,
    bi_searcher_with_sample_config: BISearcher,
    bi_status_fetcher: BIStatusFetcher,
) -> None:
    bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(sample_config.bi_status_rows)

    bi_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    assert bi_aggregation is not None
    applications_rule = bi_packs_sample_config.get_rule("networking")
    assert applications_rule is not None
    results = applications_rule.compile(("heute",), bi_searcher_with_sample_config)
    assert len(results) == 1
    compiled_rule = results[0]
    assert compiled_rule.required_elements() == {
        ("heute", "heute", "Interface 2"),
        ("heute", "heute", "Interface 3"),
        ("heute", "heute", "Interface 4"),
    }
    computed_tree = compiled_rule.compute(bi_aggregation.computation_options, bi_status_fetcher)
    assert computed_tree is not None
    assert computed_tree.assumed_result is None
    assert computed_tree.actual_result.state == 1
    assert computed_tree.actual_result.in_downtime is False
    assert not computed_tree.actual_result.acknowledged
    assert computed_tree.actual_result.in_service_period

    # Apply assumed states
    bi_status_fetcher.set_assumed_states(
        {
            ("heute", "heute", "Interface 2"): 0,
            ("heute", "heute", "Interface 3"): 0,
            ("heute", "heute", "Interface 4"): 0,
        }
    )

    computed_tree = compiled_rule.compute(
        bi_aggregation.computation_options, bi_status_fetcher, use_assumed=True
    )
    assert computed_tree is not None
    assert computed_tree.assumed_result is not None
    assert computed_tree.assumed_result.state == 0
    assert computed_tree.assumed_result.in_downtime is False
    assert not computed_tree.assumed_result.acknowledged
    assert computed_tree.assumed_result.in_service_period


@pytest.mark.parametrize(
    "existing_rules, expected_name",
    [
        pytest.param(["networking"], "networking_clone1", id="first clone"),
        pytest.param(
            ["networking", "networking_clone1"], "networking_clone2", id="clone already exists"
        ),
        pytest.param(
            ["networking", "networking_clone3"],
            "networking_clone1",
            id="not all subsequent clones exist",
        ),
    ],
)
def test_rule_clone_name(
    existing_rules: Sequence[str], expected_name: str, bi_packs_sample_config: BIAggregationPacks
) -> None:
    rule = bi_packs_sample_config.get_rule("networking")
    assert rule is not None

    cloned_rule = rule.clone(existing_rules)
    assert cloned_rule.id == expected_name


@pytest.mark.parametrize(
    "child_states, child_downtimes, expected_in_downtime",
    [
        pytest.param([2, 2], [True, True], True, id="all_failing_in_downtime"),
        pytest.param([2, 2], [True, False], False, id="partial_failing_not_in_downtime"),
        pytest.param([0, 0], [True, True], False, id="ok_aggregate_ignores_downtime"),
        pytest.param([0, 2], [False, True], True, id="only_failing_component_in_downtime"),
    ],
)
def test_downtime_only_on_full_problem_coverage(
    child_states: list[int],
    child_downtimes: list[bool],
    expected_in_downtime: bool,
) -> None:
    rule = _make_compiled_rule()
    children = [_make_child_result(s, d) for s, d in zip(child_states, child_downtimes)]
    options = _make_computation_options(downtime_only_on_full_problem_coverage=True)

    result = rule._process_node_compute_result(children, options)

    assert result.in_downtime is expected_in_downtime


def _make_compiled_rule() -> BICompiledRule:
    aggr_config = BIAggregationFunctionWorstSerialized(type="worst", count=1, restrict_state=2)
    return BICompiledRule(
        rule_id="test_rule",
        pack_id="test_pack",
        nodes=[],
        required_hosts=[],
        properties=BIRuleProperties(
            {"title": "", "comment": "", "docu_url": "", "icon": "", "state_messages": {}}
        ),
        aggregation_function=BIAggregationFunctionWorst(aggr_config),
        node_visualization={},
    )


def _make_child_result(state: int, in_downtime: bool) -> NodeComputeResult:
    return NodeComputeResult(
        state=state,
        in_downtime=in_downtime,
        acknowledged=False,
        output="",
        in_service_period=True,
        state_messages={},
        custom_infos={},
    )


def _make_computation_options(
    downtime_only_on_full_problem_coverage: bool,
) -> BIAggregationComputationOptions:
    config = ComputationConfigDict(
        disabled=False,
        use_hard_states=False,
        escalate_downtimes_as_warn=False,
        downtime_only_on_full_problem_coverage=downtime_only_on_full_problem_coverage,
    )
    return BIAggregationComputationOptions(config)
