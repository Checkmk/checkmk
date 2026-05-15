#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.juniper.agent_based.juniper_trpz_cpu_util import (
    check_juniper_trpz_cpu_util,
    discovery_juniper_trpz_cpu_util,
    Params,
    parse_juniper_trpz_cpu_util,
    Section,
)


def test_parse_juniper_trpz_cpu_util() -> None:
    assert parse_juniper_trpz_cpu_util([["10", "15", "12"]]) == Section(
        utilc=10, util1=15, util5=12
    )


def test_parse_juniper_trpz_cpu_util_non_numeric_value() -> None:
    assert parse_juniper_trpz_cpu_util([["invalid", "20", "15"]]) == Section(
        utilc=0, util1=20, util5=15
    )


def test_parse_juniper_trpz_cpu_util_no_data() -> None:
    assert parse_juniper_trpz_cpu_util([]) is None


def test_discovery_juniper_trpz_cpu_util() -> None:
    assert list(discovery_juniper_trpz_cpu_util(Section(utilc=10, util1=15, util5=12))) == [
        Service()
    ]


def test_check_juniper_trpz_cpu_util_below_levels() -> None:
    params = Params(util=(80.0, 90.0))
    section = Section(utilc=10, util1=15, util5=12)

    assert list(check_juniper_trpz_cpu_util(params, section)) == [
        Result(state=State.OK, summary="10% current"),
        Metric("utilc", 10.0),
        Result(state=State.OK, summary="15% 1min"),
        Metric("util1", 15.0, levels=(80.0, 90.0)),
        Result(state=State.OK, summary="12% 5min"),
        Metric("util5", 12.0, levels=(80.0, 90.0)),
    ]


def test_check_juniper_trpz_cpu_util_warn_levels_on_five_minute_average() -> None:
    params = Params(util=(80.0, 90.0))
    section = Section(utilc=10, util1=50, util5=85)

    assert list(check_juniper_trpz_cpu_util(params, section)) == [
        Result(state=State.OK, summary="10% current"),
        Metric("utilc", 10.0),
        Result(state=State.OK, summary="50% 1min"),
        Metric("util1", 50.0, levels=(80.0, 90.0)),
        Result(state=State.WARN, summary="85% 5min (warn/crit at 80.0% 5min/90.0% 5min)"),
        Metric("util5", 85.0, levels=(80.0, 90.0)),
    ]


def test_check_juniper_trpz_cpu_util_crit_levels_on_one_minute_average() -> None:
    params = Params(util=(80.0, 90.0))
    section = Section(utilc=10, util1=95, util5=12)

    assert list(check_juniper_trpz_cpu_util(params, section)) == [
        Result(state=State.OK, summary="10% current"),
        Metric("utilc", 10.0),
        Result(state=State.CRIT, summary="95% 1min (warn/crit at 80.0% 1min/90.0% 1min)"),
        Metric("util1", 95.0, levels=(80.0, 90.0)),
        Result(state=State.OK, summary="12% 5min"),
        Metric("util5", 12.0, levels=(80.0, 90.0)),
    ]


def test_check_juniper_trpz_cpu_util_no_levels_on_current_utilization() -> None:
    params = Params(util=(80.0, 90.0))
    section = Section(utilc=100, util1=10, util5=5)

    assert list(check_juniper_trpz_cpu_util(params, section)) == [
        Result(state=State.OK, summary="100% current"),
        Metric("utilc", 100.0),
        Result(state=State.OK, summary="10% 1min"),
        Metric("util1", 10.0, levels=(80.0, 90.0)),
        Result(state=State.OK, summary="5% 5min"),
        Metric("util5", 5.0, levels=(80.0, 90.0)),
    ]
