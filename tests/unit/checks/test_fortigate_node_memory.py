#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "data, expected",
    [(
        [[["1", "ebnfwa02"]], [["ebnfwa02-1", "22", "21", "7036", "1"]]],
        {
            "cluster_info": ["1", "ebnfwa02"],
            "nodes": {
                "Cluster": {
                    "cpu": 22.0,
                    "memory": 21,
                    "sessions": 7036
                }
            }
        },
    ),
     (
         [[["1", "ebnfwa02"]],
          [["", "22", "21", "7036", "1"], ["ebnfwa02-2", "0", "11", "7533", "2"]]],
         {
             "cluster_info": ["1", "ebnfwa02"],
             "nodes": {
                 "Node 1": {
                     "cpu": 22.0,
                     "memory": 21,
                     "sessions": 7036
                 },
                 "ebnfwa02-2": {
                     "cpu": 0.0,
                     "memory": 11,
                     "sessions": 7533
                 }
             }
         },
     )],
)
def test_parse_fortigate_node(data, expected):
    parsed_data = Check("fortigate_node").run_parse(data)
    assert parsed_data == expected


@pytest.mark.parametrize(
    "data, expected",
    [(
        [[["1", "ebnfwa02"]], [["ebnfwa02-1", "22", "21", "7036", "1"]]],
        [("Cluster", {})],
    ),
     (
         [[["1", "ebnfwa02"]],
          [["", "22", "21", "7036", "1"], ["ebnfwa02-2", "0", "11", "7533", "2"]]],
         [("Node 1", {}), ("ebnfwa02-2", {})],
     )],
)
def test_inventory_fortigate_node(data, expected):
    parsed_data = Check("fortigate_node").run_parse(data)
    services = Check("fortigate_node.memory").run_discovery(parsed_data)
    assert list(services) == expected


@pytest.mark.parametrize(
    "item, params, data, expected",
    [(
        "ebnfwa02",
        {
            "levels": (70.0, 80.0)
        },
        [[["1", "ebnfwa02"]],
         [["ebnfwa02-1", "22", "21", "7036", "1"], ["ebnfwa02-2", "0", "11", "7533", "2"]]],
        [],
    ),
     (
         "ebnfwa02-1",
         {
             "levels": (70.0, 80.0)
         },
         [[["1", "ebnfwa02"]],
          [["ebnfwa02-1", "22", "21", "7036", "1"], ["ebnfwa02-2", "0", "11", "7533", "2"]]],
         [(0, "Usage: 21.0%", [("mem_usage", 21, 70.0, 80.0)])],
     ),
     (
         "ebnfwa02-2",
         (70.0, 80.0),
         [[["1", "ebnfwa02"]],
          [["ebnfwa02-1", "22", "21", "7036", "1"], ["ebnfwa02-2", "0", "99", "7533", "2"]]],
         [(2, "Usage: 99.0% (warn/crit at 70.0%/80.0%)", [("mem_usage", 99, 70.0, 80.0)])],
     )],
)
def test_check_fortigate_node_memory(item, params, data, expected):
    parsed_data = Check("fortigate_node").run_parse(data)
    memory_check = Check("fortigate_node.memory")
    check_output = memory_check.run_check(item, params, parsed_data)
    assert list(check_output) == expected
