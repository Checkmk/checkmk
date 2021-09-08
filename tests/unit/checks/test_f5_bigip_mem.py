#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, result",
    [
        ([["", "", "", ""]], (None, None, [])),
        ([["", 0, "", ""]], (None, None, [])),
        ([[0, "", "", ""]], (None, None, [])),
        ([[0, 0, "", ""]], (0.0, 0.0, [("total", {})])),
        ([[1, 0, "", ""]], (1.0, 0.0, [("total", {})])),
    ],
)
def test_f5_bigip_mem_discovery(info, result):
    mem_total, mem_used, items = result
    check = Check("f5_bigip_mem")
    parsed = check.run_parse(info)

    assert list(check.run_discovery(parsed)) == items

    if items:
        assert parsed["total"] == (mem_total, mem_used)


@pytest.mark.parametrize(
    "info, result",
    [
        ([["", "", "", ""]], []),
        ([["", "", 0, ""]], []),
        ([["", "", "", 0]], []),
        ([["", "", 0, 0]], []),
        ([["", "", 1, 0]], [("TMM", {})]),
    ],
)
def test_f5_bigip_mem_tmm_discovery(info, result):
    parsed = Check("f5_bigip_mem").run_parse(info)
    check = Check("f5_bigip_mem.tmm")

    assert list(check.run_discovery(parsed)) == result

    if result:
        assert parsed["TMM"] == (1024.0, 0.0)


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        (
            {
                "total": (50586898432.0, 13228459584.0),
                "TMM": (20497563648.0, 885875712.0),
            },
            (
                0,
                "Usage: 26.15% - 12.32 GB of 47.11 GB",
                [("mem_used", 13228459584.0, None, None, 0, 50586898432.0)],
            ),
        ),
    ],
)
def test_f5_bigip_mem_check(parsed, expected_result):
    check = Check("f5_bigip_mem")
    assert check.run_check(None, {}, parsed) == expected_result


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        (
            {
                "total": (50586898432.0, 13228459584.0),
                "TMM": (20497563648.0, 885875712.0),
            },
            (
                0,
                "Usage: 4.32% - 844.84 MB of 19.09 GB",
                [("mem_used", 885875712.0, None, None, 0, 20497563648.0)],
            ),
        ),
    ],
)
def test_f5_bigip_mem_tmm_check(parsed, expected_result):
    check = Check("f5_bigip_mem.tmm")
    assert check.run_check(None, {}, parsed) == expected_result
