#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import LivestatusRow

from cmk.bi.lib import NodeComputeResult
from cmk.bi.trees import CompiledAggrTree
from cmk.gui.availability.bi import _limit_reached_for_any_site, create_bi_timeline_entry


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
