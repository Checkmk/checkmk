#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.f5os_rseries.agent_based.psu import (
    check_f5os_rseries_psu,
    discover_f5os_rseries_psu,
)
from cmk.plugins.f5os_rseries.lib.psu import parse_f5os_rseries_psu

# Walk: psu-1 active, psu-2 standby
_PSU_STRING_TABLE = [
    # name, serial, model, currentIn, currentOut, voltageIn, voltageOut, temp1, powerIn, powerOut
    [
        "psu-1",
        "S92341RE0201",
        "PWR-0306-09",
        "1656",
        "28625",
        "230000",
        "11984",
        "360",
        "352000",
        "343000",
    ],
    ["psu-2", "S92341RE0923", "PWR-0306-09", "0", "0", "0", "1453", "360", "0", "0"],
]


def test_parse_f5os_rseries_psu() -> None:
    section = parse_f5os_rseries_psu(_PSU_STRING_TABLE)
    assert section is not None
    assert "psu-1" in section
    assert "psu-2" in section
    psu1 = section["psu-1"]
    assert abs(psu1.power_in - 352.0) < 0.1
    assert abs(psu1.voltage_in - 230.0) < 0.1
    assert abs(psu1.temp1 - 36.0) < 0.1
    psu2 = section["psu-2"]
    assert psu2.power_in == 0.0
    assert abs(psu2.voltage_out - 1.453) < 0.001


def test_parse_f5os_rseries_psu_empty() -> None:
    assert parse_f5os_rseries_psu([]) is None


def test_discover_f5os_rseries_psu() -> None:
    section = parse_f5os_rseries_psu(_PSU_STRING_TABLE)
    assert section is not None
    services = sorted(discover_f5os_rseries_psu(section), key=lambda s: s.item or "")
    assert [s.item for s in services] == ["psu-1", "psu-2"]


def test_check_f5os_rseries_psu_active() -> None:
    section = parse_f5os_rseries_psu(_PSU_STRING_TABLE)
    assert section is not None
    results = list(check_f5os_rseries_psu("psu-1", section))
    assert any(
        isinstance(r, Result) and r.state == State.OK and "Active" in (r.summary or "")
        for r in results
    )
    assert any(isinstance(r, Metric) and r.name == "psu_power_out" for r in results)


def test_check_f5os_rseries_psu_standby() -> None:
    section = parse_f5os_rseries_psu(_PSU_STRING_TABLE)
    assert section is not None
    results = list(check_f5os_rseries_psu("psu-2", section))
    assert any(
        isinstance(r, Result) and r.state == State.OK and "Standby" in (r.summary or "")
        for r in results
    )
    assert not any(isinstance(r, Metric) for r in results)


def test_check_f5os_rseries_psu_dead_is_crit() -> None:
    # No input power AND no housekeeping voltage -> dead/removed unit, must be CRIT
    # (not silently reported as a healthy standby unit).
    section = parse_f5os_rseries_psu(
        [["psu-2", "S92341RE0923", "PWR-0306-09", "0", "0", "0", "0", "360", "0", "0"]]
    )
    assert section is not None
    results = list(check_f5os_rseries_psu("psu-2", section))
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)


def test_check_f5os_rseries_psu_output_without_input_is_crit() -> None:
    # Output rail up but no input power -> inconsistent, must be CRIT.
    section = parse_f5os_rseries_psu(
        [["psu-1", "S92341RE0201", "PWR-0306-09", "0", "0", "0", "11984", "360", "0", "0"]]
    )
    assert section is not None
    results = list(check_f5os_rseries_psu("psu-1", section))
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)


def test_check_f5os_rseries_psu_missing_item() -> None:
    section = parse_f5os_rseries_psu(_PSU_STRING_TABLE)
    assert section is not None
    results = list(check_f5os_rseries_psu("psu-3", section))
    assert results == []


def test_parse_f5os_rseries_psu_malformed_raises() -> None:
    # The MIB always populates the PSU telemetry columns with a number (standby reports a
    # genuine 0). An unreadable value is unexpected: we surface it (crash report) rather
    # than coerce it to 0, which would page a healthy standby unit as a dead one.
    with pytest.raises(ValueError):
        parse_f5os_rseries_psu(
            [["psu-2", "S92341RE0923", "PWR-0306-09", "0", "0", "0", "", "360", "0", "0"]]
        )
