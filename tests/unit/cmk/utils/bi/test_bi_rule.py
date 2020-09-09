#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from cmk.utils.bi.bi_data_fetcher import bi_status_fetcher


def test_load_sample_config_rule(bi_packs_sample_config):
    applications_rule = bi_packs_sample_config.get_rule("networking")
    assert applications_rule.nodes[0].action.service_regex == "NFS|Interface|TCP"


def test_sample_config_networking_rule(
    bi_packs_sample_config,
    use_test_structure_data,
    use_test_status_data,
):
    bi_aggregation = bi_packs_sample_config.get_aggregation("default_aggregation")
    applications_rule = bi_packs_sample_config.get_rule("networking")
    results = applications_rule.compile(["heute"])
    assert len(results) == 1
    compiled_rule = results[0]
    assert compiled_rule.required_elements() == {("heute", "heute", "Interface 2"),
                                                 ("heute", "heute", "Interface 3"),
                                                 ("heute", "heute", "Interface 4")}
    computed_tree = compiled_rule.compute(bi_aggregation.computation_options)
    assert computed_tree.assumed_result is None
    assert computed_tree.actual_result.state == 1
    assert computed_tree.actual_result.downtime_state == 0
    assert not computed_tree.actual_result.acknowledged
    assert computed_tree.actual_result.in_service_period

    # Apply assumed states
    bi_status_fetcher.set_assumed_states({
        ("heute", "heute", "Interface 2"): 0,
        ("heute", "heute", "Interface 3"): 0,
        ("heute", "heute", "Interface 4"): 0,
    })

    computed_tree = compiled_rule.compute(bi_aggregation.computation_options, use_assumed=True)
    assert computed_tree.assumed_result is not None
    assert computed_tree.assumed_result.state == 0
    assert computed_tree.assumed_result.downtime_state == 0
    assert not computed_tree.assumed_result.acknowledged
    assert computed_tree.assumed_result.in_service_period

    #
