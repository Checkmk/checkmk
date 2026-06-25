#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ups.agent_based.ups_socomec_in_voltage import (
    check_socomec_ups_in_voltage,
    discover_socomec_ups_in_voltage,
    parse_ups_socomec_in_voltage,
)


def test_ups_socomec_in_voltage_parse_function() -> None:
    assert parse_ups_socomec_in_voltage([["1", "2300"], ["2", "2250"]]) == [
        ["1", "2300"],
        ["2", "2250"],
    ]


def test_ups_socomec_in_voltage_discovery() -> None:
    assert list(discover_socomec_ups_in_voltage([["1", "2300"]])) == [Service(item="1")]


def test_ups_socomec_in_voltage_discovery_zero_voltage() -> None:
    assert list(discover_socomec_ups_in_voltage([["1", "0"]])) == []


def test_ups_socomec_in_voltage_check_ok() -> None:
    assert list(
        check_socomec_ups_in_voltage("1", {"levels_lower": (210, 180)}, [["1", "2300"]])
    ) == [
        Result(state=State.OK, summary="In voltage: 230V"),
        Metric("in_voltage", 230.0, boundaries=(150.0, None)),
    ]


def test_ups_socomec_in_voltage_check_warning() -> None:
    results = list(check_socomec_ups_in_voltage("1", {"levels_lower": (240, 200)}, [["1", "2300"]]))
    assert results[0] == Result(
        state=State.WARN, summary="In voltage: 230V (warn/crit below 240V/200V)"
    )
    assert Metric("in_voltage", 230.0, boundaries=(150.0, None)) in results


def test_ups_socomec_in_voltage_check_critical() -> None:
    results = list(check_socomec_ups_in_voltage("1", {"levels_lower": (250, 240)}, [["1", "2300"]]))
    assert results[0] == Result(
        state=State.CRIT, summary="In voltage: 230V (warn/crit below 250V/240V)"
    )


def test_ups_socomec_in_voltage_check_missing_item() -> None:
    assert (
        list(check_socomec_ups_in_voltage("2", {"levels_lower": (210, 180)}, [["1", "2300"]])) == []
    )
