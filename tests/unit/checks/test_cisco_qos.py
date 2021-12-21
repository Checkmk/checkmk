#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string_table, expected_check_result",
    [
        pytest.param(
            [
                [
                    # ifs
                    # [policy_id, iid2/if_id]
                    ["7", "456"],
                ],
                [
                    # policies
                    # [policy_map_id, policy_name]
                    ["123", "mypolicy"],
                ],
                [
                    # classes
                    # [class_id, cname]
                    ["123", "c-out-q3"],
                ],
                [
                    # config
                    # [policy_id + . + objects_id, class_id/policy_map_id]
                    # derives parent_value_cache: {"123": "0005"}
                    # also contains b_key; value is used for lookup in qos_unit
                    # and qos_bandwidth
                    ["7.0005", "123"],
                    ["999.9", "666"],
                ],
                [
                    # post_bytes
                    # [objects_id, post_b]
                    ["0005", "0"],
                ],
                [
                    # drop_bytes
                    # [objects_id, drop_b]
                    ["0005", "0"],
                ],
                [
                    # if_names
                    # [if_id, if_name]
                    ["456", "QoS Ethernet1/8"],
                ],
                [
                    # if_speeds
                    # [if_id, speed]
                    ["456", "4294967295"],
                ],
                [
                    # parents
                    # [class_id, objects_id]
                    #  b_key     b_value
                    ["999.9", "0005"],
                ],
                [
                    # if_qos_bandwidth
                    ["666", "100"],
                ],
                [
                    # if_qos_bandwidth_units
                    ["666", "3"],
                ],
                [
                    # object_types
                    # [policy_id or class_id, ? but needs to match 1 and 4 respectively]
                    ["7.0005", "1"],
                    ["999.9", "4"],
                ],
            ],
            (
                0,
                "post: 0 bit/s, drop: 0 bit/s, Policy-Name: mypolicy, Int-Bandwidth: 0 bit/s",
                [
                    ("post", 0.0, None, None, 0.0, 0.0),
                    ("drop", 0.0, 0.0, 0.0, 0.0, 0.0),
                ],
            ),
            id="Service is not critical when at 0 speed (i.e. 0 post, 0 dropped and bandwidth at "
            "100% remaining (bandwidth unit = 3); Also test no issues due to floating point precision "
            "when calculating percentages: (7 / 100) * 100 != 7 * (100 / 100)",
        ),
    ],
)
def test_check_cisco_qos(string_table, expected_check_result):
    check = Check("cisco_qos")
    assert (
        check.run_check("QoS Ethernet1/8: c-out-q3", {"drop": (0.01, 0.01)}, string_table)
        == expected_check_result
    )
