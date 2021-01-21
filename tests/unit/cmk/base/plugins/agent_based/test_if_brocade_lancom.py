#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.if_brocade_lancom import parse_if_brocade_lancom


@pytest.mark.parametrize("if_table,name_map,ignore,expected_results", [
    (
        [
            [
                '1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                '11', '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'Local0'
            ],
            [
                '1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                '11', '12', '13', 'eth1', [0, 12, 206, 149, 55, 128], 'Logical Network'
            ],
        ],
        {
            'eth0': 'LAN'
        },
        {'Local'},
        (('1', 'eth0 Logical LAN', 'eth1', '2', 30000000),),
    ),
])
def test_parse_if_brocade_lancom(if_table, name_map, ignore, expected_results) -> None:
    results = tuple((r.index, r.descr, r.alias, r.type, r.speed)
                    for r in parse_if_brocade_lancom(if_table, name_map, ignore))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import os
    from testlib.utils import cmk_path  # type: ignore[import]
    assert not pytest.main([
        "--doctest-modules",
        os.path.join(cmk_path(), "cmk/base/plugins/agent_based/if_brocade_lancom.py")
    ])
    pytest.main(["-T=unit", "-vvsx", __file__])
