#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.innovaphone.agent_based.innovaphone_licenses import check_innovaphone_licenses


def test_check_innovaphone_licenses_metric_boundaries() -> None:
    value = list(check_innovaphone_licenses({"levels": (90.0, 95.0)}, [["100", "50"]]))
    expected = [
        Result(state=State.OK, summary="Used 50/100 Licences (50%)"),
        Metric("licenses", 50.0, boundaries=(0.0, 100.0)),
    ]
    assert value == expected


def test_check_innovaphone_licenses_zero_total() -> None:
    value = list(check_innovaphone_licenses({"levels": (90.0, 95.0)}, [["0", "0"]]))
    expected = [
        Result(state=State.UNKNOWN, summary="Used 0/0 Licences"),
        Metric("licenses", 0.0, boundaries=(0.0, 0.0)),
    ]
    assert value == expected
