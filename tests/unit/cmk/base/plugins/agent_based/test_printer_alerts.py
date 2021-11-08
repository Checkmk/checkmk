#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import mock
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.printer_alerts import (
    check_printer_alerts,
    discovery_printer_alerts,
    parse_printer_alerts,
)


@pytest.mark.parametrize("info, expected_result", [([[["1", "2", "15", "3", ""]]], [Service()])])
def test_zypper_discovery(info, expected_result):
    _section = parse_printer_alerts(info)
    result = discovery_printer_alerts(info)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        ([[["3", "0", "0", "0", ""]]], [Result(state=State.OK, summary="No alerts present")]),
        (
            [[["1", "2", "15", "3", "Alert desc"]]],
            [Result(state=State.WARN, summary="unknown alert group 2#15: Alert desc")],
        ),
        (
            [[["1", "2", "15", "3", ""]]],
            [Result(state=State.WARN, summary="unknown alert group 2#15: coverOpen")],
        ),
        (
            [[["1", "-1", "15", "1111111", ""]]],
            [
                Result(
                    state=State.OK, summary="unknown alert group -1#15: unknown alert code: 1111111"
                )
            ],
        ),
        (
            [[["2", "2", "15", "-1", ""]]],
            [Result(state=State.UNKNOWN, summary="unknown alert group 2#15: ")],
        ),
        (
            [[["1", "-1", "5", "-1", "Energiesparen"]]],
            [Result(state=State.OK, summary="No alerts found")],
        ),
        ([[["2", "5", "-1", "-1", ""]]], [Result(state=State.UNKNOWN, summary="generalPrinter: ")]),
        (
            [[["2", "5", "-1", "11", ""]]],
            [Result(state=State.CRIT, summary="generalPrinter: subunitLifeOver")],
        ),
        (
            [[["1", "-1", "5", "-1", "Critical Error"]]],
            [Result(state=State.CRIT, summary="Critical Error")],
        ),
    ],
)
@mock.patch.dict(
    "cmk.base.plugins.agent_based.printer_alerts.PRINTER_ALERTS_TEXT_MAP",
    {
        "Energiesparen": State.OK,
        "Critical Error": State.CRIT,
    },
)
def test_check_printer_alerts(info, expected_result):
    data = parse_printer_alerts(info)
    result = check_printer_alerts(data)
    assert list(result) == expected_result
