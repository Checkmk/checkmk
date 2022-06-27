#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "oid_value,expected",
    [
        ([0, 0, 0, 0, 0, 0, 0, 0], 0),
        ([0, 0, 0, 0, 0, 0, 1, 0], 256),
        ([0, 0, 0, 0, 0, 0, 0, 203], 203),
        ([0, 0, 0, 0, 0, 0, 2, 91], 603),
        ([0, 0, 88, 227, 183, 248, 226, 240], 97735067362032),
        ([0, 1, 43, 110, 15, 207, 84, 124], 329226688353404),
        (
            [
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
            ],
            0,
        ),  # "00 00 00 00 00 00 00 00"
        (
            [
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                51,
            ],
            3,
        ),  # "00 00 00 00 00 00 00 03"
        (
            [
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                68,
                65,
                32,
                56,
                52,
                32,
                70,
                70,
            ],
            14320895,
        ),  # "00 00 00 00 00 DA 84 FF"
        (
            [
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                48,
                48,
                32,
                68,
                65,
                32,
                56,
                53,
                32,
                48,
                48,
            ],
            14320896,
        ),  # "00 00 00 00 00 DA 85 00"
    ],
)
def test_services_split(oid_value, expected) -> None:
    check = Check("fc_port")
    fc_parse_counter = check.context["fc_parse_counter"]
    actual = fc_parse_counter(oid_value)
    assert actual == expected
