#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.f5_bigip_vcmpguests import (
    check_f5_bigip_vcmpguests,
    parse_f5_bigip_vcmpguests,
)


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [[["easl2001", "Active"], ["pasl2001", "Active"], ["tasl2001", "Active"]]],
            {"easl2001": "active", "pasl2001": "active", "tasl2001": "active"},
        ),
        ([[]], None),
    ],
)
def test_parse_f5_bigip_vcmpguests(string_table, expected_parsed_data):
    assert parse_f5_bigip_vcmpguests(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section,result",
    [
        (
            {"easl2001": "active", "pasl2001": "active", "tasl2001": "active"},
            [
                Result(state=state.OK, summary="Guest [easl2001] is active"),
                Result(state=state.OK, summary="Guest [pasl2001] is active"),
                Result(state=state.OK, summary="Guest [tasl2001] is active"),
            ],
        ),
    ],
)
def test_check_f5_bigip_vcmpguests(section, result):
    assert list(check_f5_bigip_vcmpguests(section)) == result
