#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection, Sequence

import pytest

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.bi.actions import BIStateOfServiceAction
from cmk.bi.aggregation_functions import (
    BIAggregationFunctionCountOK,
    BIAggregationFunctionWorst,
)
from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.lib import (
    ABCBICompiledNode,
    BIAggregationComputationOptions,
    BIHostSpec,
    BIHostStatusInfoRow,
    BIServiceWithFullState,
    BIStatusInfo,
    NodeComputeResult,
)
from cmk.bi.packs import BIAggregationPacks
from cmk.bi.rule import BIRule
from cmk.bi.rule_interface import BIRuleProperties
from cmk.bi.searcher import BISearcher
from cmk.bi.trees import BICompiledLeaf, BICompiledRule
from cmk.bi.type_defs import ComputationConfigDict

from .bi_test_data import sample_config

_SITE_ID = SiteId("site1")
_HOST_NAME = HostName("host1")


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


# (levels_ok, levels_warn) for a rule with three children
_ALWAYS_CRIT_LEVELS = (5, 4)  # neither level reachable
_AT_BEST_WARN_LEVELS = (4, 2)  # only the WARN level reachable
_ALL_CHILDREN = (None, "CPU", "Memory")


@pytest.mark.parametrize(
    "levels, out_of_service_period, expected_in_service_period",
    [
        pytest.param(
            _ALWAYS_CRIT_LEVELS,
            (),
            True,
            id="always CRIT, no child out of service period",
        ),
        pytest.param(
            _ALWAYS_CRIT_LEVELS,
            _ALL_CHILDREN,
            False,
            id="always CRIT, all children out of service period",
        ),
        pytest.param(
            _ALWAYS_CRIT_LEVELS,
            ("CPU",),
            True,
            id="always CRIT, one child out of service period",
        ),
        pytest.param(
            _AT_BEST_WARN_LEVELS,
            ("CPU",),
            True,
            id="at best WARN, one child out of service period",
        ),
        pytest.param(
            _AT_BEST_WARN_LEVELS,
            _ALL_CHILDREN,
            False,
            id="at best WARN, all children out of service period",
        ),
    ],
)
def test_count_ok_unreachable_levels_do_not_leave_service_period(
    bi_status_fetcher: BIStatusFetcher,
    levels: tuple[int, int],
    out_of_service_period: Collection[ServiceName | None],
    expected_in_service_period: bool,
) -> None:
    """SUP-22054: unreachable levels must not turn the aggregate n/a."""
    bi_status_fetcher.states = _status_info(out_of_service_period=out_of_service_period)

    result = _make_count_ok_rule(*levels).compute(
        _make_computation_options(downtime_only_on_full_problem_coverage=False),
        bi_status_fetcher,
    )

    assert result is not None
    assert result.actual_result.in_service_period is expected_in_service_period


@pytest.mark.parametrize(
    "levels, in_downtime, expected_in_downtime",
    [
        pytest.param(
            _ALWAYS_CRIT_LEVELS,
            (),
            False,
            id="always CRIT, no child in downtime",
        ),
        pytest.param(
            _ALWAYS_CRIT_LEVELS, _ALL_CHILDREN, True, id="always CRIT, all children in downtime"
        ),
        pytest.param(
            _ALWAYS_CRIT_LEVELS,
            ("CPU",),
            False,
            id="always CRIT, one child in downtime",
        ),
        pytest.param(
            _AT_BEST_WARN_LEVELS, _ALL_CHILDREN, True, id="at best WARN, all children in downtime"
        ),
    ],
)
def test_count_ok_unreachable_levels_do_not_cause_downtime(
    bi_status_fetcher: BIStatusFetcher,
    levels: tuple[int, int],
    in_downtime: Collection[ServiceName | None],
    expected_in_downtime: bool,
) -> None:
    """SUP-22054: unreachable levels must not put the aggregate in downtime."""
    bi_status_fetcher.states = _status_info(in_downtime=in_downtime)

    result = _make_count_ok_rule(*levels).compute(
        _make_computation_options(downtime_only_on_full_problem_coverage=False),
        bi_status_fetcher,
    )

    assert result is not None
    assert result.actual_result.in_downtime is expected_in_downtime


def test_count_ok_warn_baseline_is_not_downtime_when_escalating_as_warn(
    bi_status_fetcher: BIStatusFetcher,
) -> None:
    """SUP-22054: the WARN baseline of reachable WARN levels is not a downtime."""
    bi_status_fetcher.states = _status_info()

    result = _make_count_ok_rule(*_AT_BEST_WARN_LEVELS).compute(
        _make_computation_options(
            downtime_only_on_full_problem_coverage=False, escalate_downtimes_as_warn=True
        ),
        bi_status_fetcher,
    )

    assert result is not None
    assert result.actual_result.in_downtime is False


@pytest.mark.parametrize(
    "flag, expected",
    [
        pytest.param(
            "in_service_period",
            True,
            id="parent stays in service period",
        ),
        pytest.param(
            "in_downtime",
            False,
            id="parent is not in downtime",
        ),
    ],
)
def test_count_ok_unreachable_levels_do_not_leak_into_parent(
    bi_status_fetcher: BIStatusFetcher, flag: str, expected: bool
) -> None:
    """SUP-22054: the n/a showed on the aggregate above the count_ok rule."""
    bi_status_fetcher.states = _status_info()
    parent = _make_compiled_rule(nodes=[_make_count_ok_rule(*_ALWAYS_CRIT_LEVELS)])

    result = parent.compute(
        _make_computation_options(downtime_only_on_full_problem_coverage=False),
        bi_status_fetcher,
    )

    assert result is not None
    assert getattr(result.actual_result, flag) is expected


def _make_count_ok_rule(levels_ok: int, levels_warn: int) -> BICompiledRule:
    aggr_config = dict(
        type="count_ok",
        levels_ok={"type": "count", "value": levels_ok},
        levels_warn={"type": "count", "value": levels_warn},
    )
    return BICompiledRule(
        rule_id="test_rule",
        pack_id="test_pack",
        nodes=[
            BICompiledLeaf(host_name=_HOST_NAME, site_id=_SITE_ID, service_description=service)
            for service in _ALL_CHILDREN
        ],
        required_hosts=[(_SITE_ID, _HOST_NAME)],
        properties=BIRuleProperties(
            {"title": "", "comment": "", "docu_url": "", "icon": "", "state_messages": {}}
        ),
        aggregation_function=BIAggregationFunctionCountOK(aggr_config),
        node_visualization={},
    )


def _status_info(
    *,
    out_of_service_period: Collection[ServiceName | None] = (),
    in_downtime: Collection[ServiceName | None] = (),
) -> BIStatusInfo:
    """All children OK; the host is the child None.

    Host downtime (not service period) also applies to services.
    """
    return {
        BIHostSpec(site_id=_SITE_ID, host_name=_HOST_NAME): BIHostStatusInfoRow(
            state=0,
            has_been_checked=True,
            hard_state=0,
            plugin_output="",
            scheduled_downtime_depth=int(None in in_downtime),
            in_service_period=None not in out_of_service_period,
            acknowledged=False,
            services_with_fullstate={
                service: BIServiceWithFullState(
                    state=0,
                    has_been_checked=True,
                    plugin_output="",
                    hard_state=0,
                    current_attempt=1,
                    max_check_attempts=1,
                    scheduled_downtime_depth=int(service in in_downtime),
                    acknowledged=False,
                    in_service_period=service not in out_of_service_period,
                )
                for service in _ALL_CHILDREN
                if service is not None
            },
            remaining_row_keys={},
        )
    }


def _make_compiled_rule(nodes: Sequence[ABCBICompiledNode] = ()) -> BICompiledRule:
    aggr_config = dict(type="worst", count=1, restrict_state=2)
    return BICompiledRule(
        rule_id="test_rule",
        pack_id="test_pack",
        nodes=list(nodes),
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
    escalate_downtimes_as_warn: bool = False,
) -> BIAggregationComputationOptions:
    config = ComputationConfigDict(
        disabled=False,
        use_hard_states=False,
        escalate_downtimes_as_warn=escalate_downtimes_as_warn,
        downtime_only_on_full_problem_coverage=downtime_only_on_full_problem_coverage,
    )
    return BIAggregationComputationOptions(config)
