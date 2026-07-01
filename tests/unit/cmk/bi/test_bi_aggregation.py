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


def test_compiled_aggregation_customer_none_propagates(
    bi_packs_sample_config: BIAggregationPacks,
    bi_structure_fetcher: BIStructureFetcher,
    bi_searcher: BISearcher,
) -> None:
    bi_structure_fetcher.add_site_data(SiteId("heute"), sample_config.bi_structure_states)
    bi_searcher.set_hosts(bi_structure_fetcher.hosts)

    bi_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    assert bi_aggregation is not None
    bi_aggregation.customer = None

    compiled_aggregation = bi_aggregation.compile(bi_searcher)
    assert compiled_aggregation.customer is None


def test_compiled_aggregation_propagates_customer_to_legacy_row(
    bi_packs_sample_config: BIAggregationPacks,
    bi_structure_fetcher: BIStructureFetcher,
    bi_searcher: BISearcher,
    bi_status_fetcher: BIStatusFetcher,
) -> None:
    # SUP-29522: the aggregation's customer must reach the legacy row as
    # "customer_id" so the CME customer filter can filter BI aggregations.
    bi_structure_fetcher.add_site_data(SiteId("heute"), sample_config.bi_structure_states)
    bi_searcher.set_hosts(bi_structure_fetcher.hosts)
    bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(sample_config.bi_status_rows)

    bi_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    assert bi_aggregation is not None
    bi_aggregation.customer = "cust_x"

    compiled_aggregation = bi_aggregation.compile(bi_searcher)
    assert compiled_aggregation.customer == "cust_x"

    computed_branches = compiled_aggregation.compute_branches(
        compiled_aggregation.branches, bi_status_fetcher
    )
    legacy_row = compiled_aggregation.convert_result_to_legacy_format(computed_branches[0])
    assert legacy_row["customer_id"] == "cust_x"


def test_compiled_aggregation_serialize_roundtrips_customer(
    bi_packs_sample_config: BIAggregationPacks,
    bi_structure_fetcher: BIStructureFetcher,
    bi_searcher: BISearcher,
) -> None:
    # SUP-29522: the customer must survive the compiled-aggregation cache. The
    # cache (AggregationStore) round-trips through serialize() / create_trees_from_schema,
    # NOT the marshmallow schema - so this must exercise serialize() directly, or a
    # regression that only drops customer from serialize() slips through.
    bi_structure_fetcher.add_site_data(SiteId("heute"), sample_config.bi_structure_states)
    bi_searcher.set_hosts(bi_structure_fetcher.hosts)

    bi_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    assert bi_aggregation is not None
    bi_aggregation.customer = "cust_x"
    compiled_aggregation = bi_aggregation.compile(bi_searcher)

    serialized = compiled_aggregation.serialize()
    assert serialized["customer"] == "cust_x"

    restored = BIAggregation.create_trees_from_schema(serialized)
    assert restored.customer == "cust_x"
