#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, result", [
    ([["", "", "", ""]], (None, None, None)),
    ([["", 0, "", ""]], (None, None, None)),
    ([[0, "", "", ""]], (None, None, None)),
    ([[0, 0, "", ""]], (0.0, 0.0, [("total", {})])),
    ([[1, 0, "", ""]], (1.0, 0.0, [("total", {})])),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_f5_bigip_mem_discovery(info, result):
    mem_total, mem_used, items = result
    check = Check("f5_bigip_mem")
    parsed = check.run_parse(info)

    assert check.run_discovery(parsed) == items

    if items:
        assert parsed["total"] == (mem_total, mem_used)


@pytest.mark.parametrize("info, result", [
    ([["", "", "", ""]], []),
    ([["", "", 0, ""]], []),
    ([["", "", "", 0]], []),
    ([["", "", 0, 0]], []),
    ([["", "", 1, 0]], [("TMM", {})]),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_f5_bigip_mem_tmm_discovery(info, result):
    parsed = Check("f5_bigip_mem").run_parse(info)
    check = Check("f5_bigip_mem.tmm")

    assert list(check.run_discovery(parsed)) == result

    if result:
        assert parsed["TMM"] == (1024.0, 0.0)
