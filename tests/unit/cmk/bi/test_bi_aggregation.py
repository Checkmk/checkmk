#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusResponse

from cmk.bi.actions import BICallARuleAction
from cmk.bi.aggregation import BIAggregation
from cmk.bi.data_fetcher import BIStatusFetcher, BIStructureFetcher
from cmk.bi.packs import BIAggregationPacks
from cmk.bi.searcher import BISearcher
from cmk.ccc.site import SiteId

from .bi_test_data import sample_config


def test_load_aggregation_integrity(bi_packs_sample_config: BIAggregationPacks) -> None:
    default_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    assert default_aggregation is not None
    assert default_aggregation.id == "default_aggregation"
    assert default_aggregation.groups.names == ["Hosts"]
    assert not default_aggregation.computation_options.disabled
    action = default_aggregation.node.action
    assert isinstance(action, BICallARuleAction)
    assert action.rule_id == "host"

    # Generate the schema for the default_aggregation and instantiate a new aggregation from it
    aggregation_schema = BIAggregation.schema()()
    schema_config = aggregation_schema.dump(default_aggregation)
    cloned_aggregation = BIAggregation(schema_config)
    assert cloned_aggregation.id == "default_aggregation"
    assert cloned_aggregation.groups.names == ["Hosts"]
    assert not cloned_aggregation.computation_options.disabled

    action = cloned_aggregation.node.action
    assert isinstance(action, BICallARuleAction)
    assert action.rule_id == "host"


@pytest.mark.parametrize(
    "status_data, expected_state, expected_acknowledgment, expected_in_downtime, "
    "expected_computed_branches, expected_service_period",
    [
        (sample_config.bi_status_rows, 1, False, False, 2, True),
        (sample_config.bi_acknowledgment_status_rows, 1, True, False, 1, True),
        (sample_config.bi_downtime_status_rows, 1, False, True, 1, True),
        (sample_config.bi_service_period_status_rows, 1, False, False, 1, False),
    ],
)
def test_compute_aggregation(
    bi_packs_sample_config: BIAggregationPacks,
    bi_structure_fetcher: BIStructureFetcher,
    bi_searcher: BISearcher,
    bi_status_fetcher: BIStatusFetcher,
    status_data: LivestatusResponse,
    expected_state: int,
    expected_acknowledgment: bool,
    expected_in_downtime: bool,
    expected_computed_branches: int,
    expected_service_period: bool,
) -> None:
    bi_structure_fetcher.add_site_data(SiteId("heute"), sample_config.bi_structure_states)
    bi_searcher.set_hosts(bi_structure_fetcher.hosts)
    bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(status_data)

    bi_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    assert bi_aggregation is not None
    compiled_aggregation = bi_aggregation.compile(bi_searcher)
    # Compile aggregations based on structure data
    assert len(compiled_aggregation.branches) == 2

    computed_branches = compiled_aggregation.compute_branches(
        compiled_aggregation.branches, bi_status_fetcher
    )
    # Compute aggregation with status data
    assert len(computed_branches) == expected_computed_branches
    actual_result = computed_branches[0].actual_result

    # Host heute -> General state -> Check_MK -> Check_MK Discovery (state warn / acknowledged)
    assert actual_result.state == expected_state
    assert actual_result.acknowledged == expected_acknowledgment
    assert actual_result.in_downtime == expected_in_downtime
    assert actual_result.in_service_period == expected_service_period
