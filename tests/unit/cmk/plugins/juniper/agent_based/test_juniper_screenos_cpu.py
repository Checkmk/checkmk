#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.juniper.agent_based.juniper_screenos_cpu import (
    check_juniper_screenos_cpu,
    discover_juniper_screenos_cpu,
    parse_juniper_screenos_cpu,
    Section,
)


def test_parse_juniper_screenos_cpu() -> None:
    assert parse_juniper_screenos_cpu([["15", "12"]]) == Section(util1=15.0, util15=12.0)


def test_parse_juniper_screenos_cpu_zero_utilization() -> None:
    assert parse_juniper_screenos_cpu([["0", "0"]]) == Section(util1=0.0, util15=0.0)


def test_parse_juniper_screenos_cpu_no_data() -> None:
    assert parse_juniper_screenos_cpu([]) is None


def test_discover_juniper_screenos_cpu() -> None:
    assert list(discover_juniper_screenos_cpu(Section(util1=15.0, util15=12.0))) == [Service()]


def test_check_juniper_screenos_cpu_below_levels() -> None:
    params = {"util": (80.0, 90.0)}
    section = Section(util1=15.0, util15=12.0)

    assert list(check_juniper_screenos_cpu(params, section)) == [
        Result(state=State.OK, summary="1min: 15.00%"),
        Metric("util1", 15.0),
        Result(state=State.OK, summary="15min: 12.00%"),
        Metric("util15", 12.0, levels=(80.0, 90.0)),
    ]


def test_check_juniper_screenos_cpu_warn_levels() -> None:
    params = {"util": (80.0, 90.0)}
    section = Section(util1=15.0, util15=85.0)

    assert list(check_juniper_screenos_cpu(params, section)) == [
        Result(state=State.OK, summary="1min: 15.00%"),
        Metric("util1", 15.0),
        Result(state=State.WARN, summary="15min: 85.00% (warn/crit at 80.00%/90.00%)"),
        Metric("util15", 85.0, levels=(80.0, 90.0)),
    ]


def test_check_juniper_screenos_cpu_crit_levels() -> None:
    params = {"util": (80.0, 90.0)}
    section = Section(util1=15.0, util15=95.0)

    assert list(check_juniper_screenos_cpu(params, section)) == [
        Result(state=State.OK, summary="1min: 15.00%"),
        Metric("util1", 15.0),
        Result(state=State.CRIT, summary="15min: 95.00% (warn/crit at 80.00%/90.00%)"),
        Metric("util15", 95.0, levels=(80.0, 90.0)),
    ]


def test_check_juniper_screenos_cpu_no_levels_on_one_minute_average() -> None:
    params = {"util": (80.0, 90.0)}
    section = Section(util1=100.0, util15=5.0)

    assert list(check_juniper_screenos_cpu(params, section)) == [
        Result(state=State.OK, summary="1min: 100.00%"),
        Metric("util1", 100.0),
        Result(state=State.OK, summary="15min: 5.00%"),
        Metric("util15", 5.0, levels=(80.0, 90.0)),
    ]
