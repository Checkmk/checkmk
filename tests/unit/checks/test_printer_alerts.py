#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import mock

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [([None], [(None, None)])])
def test_zypper_discovery(info, expected_result):
    result = Check("printer_alerts").run_discovery(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    ([["3", "0", "0", "0", ""]], (0, "No alerts present")),
    ([["1", "2", "15", "3", "Alert desc"]], (1, "unknown alert group 2#15: Alert desc")),
    ([["1", "2", "15", "3", ""]], (1, "unknown alert group 2#15: coverOpen")),
    ([["1", "-1", "15", "1111111", ""]],
     (0, "unknown alert group -1#15: unknown alert code: 1111111")),
    ([["2", "2", "15", "-1", ""]], (3, "unknown alert group 2#15: ")),
    ([["1", "-1", "5", "-1", "Energiesparen"]], (0, "No alerts found")),
    ([["2", "5", "-1", "-1", ""]], (3, "generalPrinter: ")),
    ([["2", "5", "-1", "11", ""]], (2, "generalPrinter: subunitLifeOver")),
])
def test_check_printer_alerts(info, expected_result):
    data = Check("printer_alerts").run_parse(info)
    result = Check("printer_alerts").run_check(None, {}, data)
    assert result == expected_result
