#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils import hp_hh3c


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            [[["1234", "1"], ["333", "2"], ["3456", "3"], ["aa", "4"]]],
            [Service(item="1234"), Service(item="333")],
        )
    ],
)
def test_hp_device_discover(string_table, expected_result):
    section = hp_hh3c.parse_hp_hh3c_device(string_table)
    assert list(hp_hh3c.discover_hp_hh3c_device(section)) == expected_result


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            [[["1234", "1"], ["3456", "3"], ["aa", "4"]]],
            "1234",
            [Result(state=State.OK, summary="Status: active")],
        ),
        (
            [[["333", "2"], ["3456", "3"], ["aa", "4"]]],
            "333",
            [Result(state=State.CRIT, summary="Status: deactive")],
        ),
        (
            [[["333", "2"], ["3456", "3"], ["aa", "4"]]],
            "55",
            [],
        ),
    ],
)
def test_hp_device_check(string_table, item, expected_result):
    section = hp_hh3c.parse_hp_hh3c_device(string_table)
    assert list(hp_hh3c.check_hp_hh3c_device(item, section)) == expected_result
