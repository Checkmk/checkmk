#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest  # type: ignore[import]

from cmk.utils.bi.bi_actions import (
    BIStateOfHostAction,
    BIStateOfServiceAction,
    BIStateOfRemainingServicesAction,
    BICallARuleAction,
)

from cmk.utils.bi.bi_trees import (
    BICompiledLeaf,
    BICompiledRule,
    BIRemainingResult,
)


@pytest.mark.parametrize("host_regex, num_results, num_results_unknown", [
    ("$WRONGPATTERN$", 0, 0),
    ("$HOSTNAME$", 1, 0),
    (".*", 2, 2),
    ("heute_clone", 1, 1),
])
def test_state_of_host_execute(host_regex, num_results, num_results_unknown,
                               use_test_structure_data):
    schema_config = BIStateOfHostAction.schema()().dump({"host_regex": host_regex}).data
    action = BIStateOfHostAction(schema_config)
    results = action.execute({"$HOSTNAME$": "heute"})
    assert len(results) == num_results
    for result in results:
        assert isinstance(result, BICompiledLeaf)

    results = action.execute({"$HOSTNAME$": "unkown"})
    assert len(results) == num_results_unknown
    for result in results:
        assert isinstance(result, BICompiledLeaf)


@pytest.mark.parametrize("host_regex, num_results, num_results_unknown", [
    ("$HOSTNAME$", 1, 0),
    ("$WRONGPATTERN$", 0, 0),
    (".*", 2, 2),
    ("heute_clone", 1, 1),
])
def test_state_of_service_execute(host_regex, num_results, num_results_unknown,
                                  use_test_structure_data):
    schema_config = BIStateOfServiceAction.schema()().dump({
        "host_regex": host_regex,
        "service_regex": "Uptime"
    }).data
    action = BIStateOfServiceAction(schema_config)
    results = action.execute({"$HOSTNAME$": "heute"})
    assert len(results) == num_results
    for result in results:
        assert isinstance(result, BICompiledLeaf)
        assert result.service_description == "Uptime"

    results = action.execute({"$HOSTNAME$": "unknown"})
    assert len(results) == num_results_unknown
    for result in results:
        assert isinstance(result, BICompiledLeaf)
        assert result.service_description == "Uptime"


def test_call_a_rule_execute(dummy_bi_rule, use_test_structure_data):
    # noqa: F811 # pylint: disable=unused-import
    schema_config = BICallARuleAction.schema()().dump({"rule_id": dummy_bi_rule.id}).data
    action = BICallARuleAction(schema_config)
    results = action.execute({})
    assert len(results) == 1
    assert isinstance(results[0], BICompiledRule)


@pytest.mark.parametrize("host_regex, num_host_matches, num_host_matches_unknown", [
    ("$HOSTNAME$", 1, 0),
    ("$WRONGPATTERN$", 0, 0),
    (".*", 2, 2),
    ("heute", 1, 1),
])
def test_state_of_remaining(host_regex, num_host_matches, num_host_matches_unknown,
                            use_test_structure_data):
    # TODO: Test misses compile_postprocess (reveals number of services)
    #       this requires a more complicated setup -> bi_aggregation_test
    schema_config = BIStateOfRemainingServicesAction.schema()().dump({
        "host_regex": host_regex
    }).data
    action = BIStateOfRemainingServicesAction(schema_config)
    results = action.execute({"$HOSTNAME$": "heute"})
    assert len(results) == 1
    assert isinstance(results[0], BIRemainingResult)
    assert len(results[0].host_names) == num_host_matches

    results = action.execute({"$HOSTNAME$": "unkown"})
    assert len(results) == 1
    assert isinstance(results[0], BIRemainingResult)
    assert len(results[0].host_names) == num_host_matches_unknown
