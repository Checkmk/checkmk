#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusResponse, LivestatusRow, Query

from cmk.bi.aggregation_functions import BIAggregationFunctionWorst
from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.lib import BIAggregationComputationOptions, NodeComputeResult, SitesCallback
from cmk.bi.rule_interface import BIRuleProperties
from cmk.bi.trees import BICompiledLeaf, BICompiledRule, CompiledAggrTree
from cmk.bi.type_defs import ComputationConfigDict
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability import bi as availability_bi
from cmk.gui.availability.bi import (
    _bi_span_from_statehist_row,
    _bi_status_info_from_timeline_states,
    _is_better_timewarp_phase,
    _limit_reached_for_any_site,
    create_bi_timeline_entry,
    get_bi_split_history_data,
    reclassify_bi_rows,
)
from cmk.gui.availability.type_defs import AVSpan


def _rows_for_site(site: str, count: int) -> list[LivestatusRow]:
    return [LivestatusRow([site, "data"]) for _ in range(count)]


def test_limit_reached_for_any_site_no_limit() -> None:
    assert _limit_reached_for_any_site(_rows_for_site("site1", 1000), None) is False


def test_limit_reached_for_any_site_summed_rows_do_not_trip_per_site_limit() -> None:
    # Three sites each return a complete dataset below the per-site limit. Their sum
    # exceeds the limit, but no single site truncated its data (CMK-8277).
    limit = 11
    rows = _rows_for_site("site1", 5) + _rows_for_site("site2", 5) + _rows_for_site("site3", 5)
    assert _limit_reached_for_any_site(rows, limit) is False


def test_limit_reached_for_any_site_single_site_reaches_limit() -> None:
    limit = 11
    rows = _rows_for_site("site1", limit) + _rows_for_site("site2", 5)
    assert _limit_reached_for_any_site(rows, limit) is True


def test_create_bi_timeline_entry_site_id_is_not_empty() -> None:
    tree = CompiledAggrTree(
        type=2,
        frozen_marker=None,
        title="My Aggregation",
        docu_url="",
        rule_id="r1",
        reqhosts=[],
        nodes=[],
        rule_layout_style={},
        aggr_group_tree=[],
        aggr_type="multi",
        aggregation_id="a1",
        downtime_aggr_warn=False,
        use_hard_states=False,
        node_visualization={},
    )
    result = create_bi_timeline_entry(
        tree=tree,
        aggr_group="my-group",
        from_time=1000,
        until_time=2000,
        node_compute_result=NodeComputeResult(
            state=0,
            in_downtime=False,
            acknowledged=False,
            output="OK",
            in_service_period=True,
            state_messages={},
            custom_infos={},
        ),
    )
    assert result["site"] != "", "site_id must not be empty in BI timeline entries"


def test_bi_span_from_statehist_row_sets_all_required_avspan_fields() -> None:
    span = _bi_span_from_statehist_row(
        LivestatusRow(["site1", "host1", "Svc", 1000, 2500, "OK - all good", 0, 0, 1])
    )
    assert set(AVSpan.__required_keys__) <= set(span)
    assert span["duration"] == 1500
    assert span["host_down"] == 0
    assert span["in_host_downtime"] == 0
    assert span["in_notification_period"] == 1
    assert span["is_flapping"] == 0


def test_reclassify_bi_rows_splits_span_on_downtime_annotation() -> None:
    span = _bi_span_from_statehist_row(
        LivestatusRow(["site1", "host1", "Svc", 1000, 2000, "OK", 0, 0, 1])
    )
    new_spans = reclassify_bi_rows(
        [span],
        {
            (SiteId("site1"), HostName("host1"), "Svc"): [
                {"from": 1200, "until": 1500, "downtime": True}
            ]
        },
    )
    assert [(s["from"], s["until"], s["in_downtime"]) for s in new_spans] == [
        (1000, 1200, 0),
        (1200, 1500, 1),
        (1500, 2000, 0),
    ]
    assert all(s["duration"] == s["until"] - s["from"] for s in new_spans)


@pytest.mark.parametrize(
    "from_time, has_candidate, expected",
    [
        pytest.param(500, False, True, id="first phase is the fallback"),
        pytest.param(5000, False, True, id="first phase wins even after the timewarp"),
        pytest.param(1000, True, True, id="phase starting on the timewarp"),
        pytest.param(999, True, True, id="phase starting before the timewarp"),
        pytest.param(1001, True, False, id="phase starting after the timewarp"),
    ],
)
def test_is_better_timewarp_phase(from_time: int, has_candidate: bool, expected: bool) -> None:
    assert _is_better_timewarp_phase(from_time, 1000, has_candidate) is expected


def _host_and_service_rule() -> BICompiledRule:
    return BICompiledRule(
        rule_id="jira",
        pack_id="default",
        nodes=[
            BICompiledLeaf(host_name=HostName("jira-app"), site_id="site1"),
            BICompiledLeaf(
                host_name=HostName("jira-app"), service_description="Jira", site_id="site1"
            ),
        ],
        required_hosts=[(SiteId("site1"), HostName("jira-app"))],
        properties=BIRuleProperties(
            {"title": "Jira", "comment": "", "docu_url": "", "icon": "", "state_messages": {}}
        ),
        aggregation_function=BIAggregationFunctionWorst(
            {"type": "worst", "count": 1, "restrict_state": 2}
        ),
        node_visualization={},
    )


def _no_query(
    query: Query,  # noqa: ARG001
    only_sites: list[SiteId] | None = None,  # noqa: ARG001
    fetch_full_data: bool = False,  # noqa: ARG001
) -> LivestatusResponse:
    return LivestatusResponse([])


def test_aggregate_without_host_history_is_computed_from_its_services() -> None:
    # SUP-23138: a contact of the service only gets no host history. The host must count
    # as missing, not as UP outside of its service period (which turned the aggregate n/a).
    status_fetcher = BIStatusFetcher(
        SitesCallback(all_sites_with_id_and_online=list, query=_no_query, translate=str)
    )
    status_fetcher.states = _bi_status_info_from_timeline_states(
        {(SiteId("site1"), HostName("jira-app"), "Jira"): (2, "CRIT", 0, True)}
    )

    result = _host_and_service_rule().compute(
        BIAggregationComputationOptions(
            ComputationConfigDict(
                disabled=False, use_hard_states=False, escalate_downtimes_as_warn=False
            )
        ),
        status_fetcher,
    )

    assert result is not None
    assert (result.actual_result.state, result.actual_result.in_service_period) == (2, True)
    assert len(result.nested_results) == 1


def test_bi_history_is_queried_with_the_bi_visibility(monkeypatch: pytest.MonkeyPatch) -> None:
    # SUP-23138: the history must follow bi.see_all like the BI tree, not the contact
    # assignments. Tech debt: query_livestatus is module-level and can't be injected.
    auth_domains: list[str] = []

    def _record(*_args: object, auth_domain: str, **_kwargs: object) -> list[LivestatusRow]:
        auth_domains.append(auth_domain)
        return []

    monkeypatch.setattr(availability_bi, "query_livestatus", _record)

    get_bi_split_history_data((0, 1), ["host_name"], {SiteId("site1")}, "", None)

    assert auth_domains == ["bi"]
