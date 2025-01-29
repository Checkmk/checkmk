#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from unittest import mock

import pytest

from cmk.agent_based.v2 import CheckResult, Result, State, StringTable
from cmk.plugins.collection.agent_based.printer_alerts import (
    check_printer_alerts,
    discovery_printer_alerts,
    parse_printer_alerts,
)


def test_discover_always() -> None:
    assert list(discovery_printer_alerts(()))


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
        (
            [[["1", "5", "-1", "23", "Bereitschafts-\nmodus ein"]]],
            [Result(state=State.OK, summary="generalPrinter: Bereitschaftsmodus ein")],
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
    "cmk.plugins.collection.agent_based.printer_alerts.PRINTER_ALERTS_TEXT_MAP",
    {
        "Energiesparen": State.OK,
        "Critical Error": State.CRIT,
    },
)
def test_check_printer_alerts(info: Sequence[StringTable], expected_result: CheckResult) -> None:
    data = parse_printer_alerts(info)
    result = check_printer_alerts(data)
    assert list(result) == expected_result
