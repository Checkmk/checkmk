#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.apc_netshelterpdu_power import (
    _parse_rated_va,
    check_apc_netshelterpdu_power,
    CurrentReading,
    discover_apc_netshelterpdu_power,
    NetShelterPDUItem,
    parse_apc_netshelterpdu_power,
)


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("43.5kVA", 43500.0),
        ("10kVA", 10000.0),
        ("5.5kva", 5500.0),
        ("2300VA", 2300.0),
        ("invalid", None),
        ("", None),
    ],
)
def test_parse_rated_va(input_str: str, expected: float | None) -> None:
    assert _parse_rated_va(input_str) == expected


def test_parse_3phase_no_banks() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["mymagicpdu"]],
            [["4583", "4605"]],
            [["3"]],
            [
                ["1", "5", "620", "1431"],
                ["2", "5", "623", "1436"],
                ["3", "5", "747", "1715"],
            ],
            [],
            [
                ["1", "5700", "4500"],
                ["2", "5700", "4500"],
                ["3", "5700", "4500"],
            ],
            [["43.5kVA"]],
        ]
    )
    assert section is not None
    assert set(section) == {"Device mymagicpdu", "Phase 1", "Phase 2", "Phase 3"}
    assert section["Device mymagicpdu"].power == 4583.0
    # Multi-phase: device does not get current
    assert section["Device mymagicpdu"].current is None
    # Total load: 4605 VA / 43500 VA * 100 = 10.586...%
    assert section["Device mymagicpdu"].output_load is not None
    assert section["Device mymagicpdu"].output_load == pytest.approx(10.586, abs=0.01)
    # Current in hundredths of Amps: 620 / 100 = 6.20
    assert section["Phase 1"].current is not None
    assert section["Phase 1"].current.value == 6.20
    assert section["Phase 1"].power == 1431.0
    # Phases have no output_load
    assert section["Phase 1"].output_load is None


def test_parse_single_phase() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["mypdu"]],
            [["1000", "1010"]],
            [["1"]],
            [["1", "5", "200", "500"]],
            [],
            [["1", "5700", "4500"]],
            [["10kVA"]],
        ]
    )
    assert section is not None
    assert section["Device mypdu"].power == 1000.0
    assert section["Device mypdu"].current is not None
    assert section["Device mypdu"].current.value == 2.0
    assert section["Phase 1"].current is not None
    assert section["Phase 1"].current.value == 2.0


def test_parse_with_banks() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["my-magic-apdu-15"]],
            [["4583", "4605"]],
            [["3"]],
            [
                ["1", "5", "620", "1431"],
                ["2", "5", "623", "1436"],
                ["3", "5", "747", "1715"],
            ],
            [
                ["B1", "5", "231"],
                ["B2", "5", "231"],
                ["B3", "5", "237"],
            ],
            [
                ["1", "5700", "4500"],
                ["2", "5700", "4500"],
                ["3", "5700", "4500"],
            ],
            [["43.5kVA"]],
        ]
    )
    assert section is not None
    assert "Bank B1" in section
    assert section["Bank B1"].current is not None
    assert section["Bank B1"].current.value == 2.31


def test_parse_skips_na_banks() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["my-magic-apdu-15"]],
            [["0", "0"]],
            [["1"]],
            [],
            [["B1", "5", "231"], ["NA", "0", "0"]],
            [],
            [],
        ]
    )
    assert section is not None
    assert "Bank NA" not in section


def test_parse_empty() -> None:
    assert parse_apc_netshelterpdu_power([[], [], [], [], [], [], []]) is None


def test_parse_phase_thresholds() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["mypdu"]],
            [["1000", "1010"]],
            [["2"]],
            [
                ["1", "5", "200", "500"],
                ["2", "5", "300", "700"],
            ],
            [],
            [
                ["1", "5700", "4500"],
                ["2", "6000", "5000"],
            ],
            [],
        ]
    )
    assert section is not None
    assert section["Phase 1"].warn_current == 45.00
    assert section["Phase 1"].crit_current == 57.00
    assert section["Phase 2"].warn_current == 50.00
    assert section["Phase 2"].crit_current == 60.00
    assert section["Device mypdu"].warn_current is None


def test_parse_load_state_normal() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["mypdu"]],
            [["0", "0"]],
            [["1"]],
            [["1", "5", "200", "500"]],
            [],
            [],
            [],
        ]
    )
    assert section is not None
    assert section["Phase 1"].current is not None
    assert section["Phase 1"].current.state == State.OK
    assert section["Phase 1"].current.state_text == "normal"


def test_parse_load_state_upper_warning() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["mypdu"]],
            [["0", "0"]],
            [["1"]],
            [["1", "2", "200", "500"]],
            [],
            [],
            [],
        ]
    )
    assert section is not None
    assert section["Phase 1"].current is not None
    assert section["Phase 1"].current.state == State.WARN
    assert section["Phase 1"].current.state_text == "upper warning"


# --- discovery function tests ---


def test_discover_all_items() -> None:
    section = parse_apc_netshelterpdu_power(
        [
            [["mypdu"]],
            [["4583", "4605"]],
            [["3"]],
            [
                ["1", "5", "620", "1431"],
                ["2", "5", "623", "1436"],
                ["3", "5", "747", "1715"],
            ],
            [
                ["B1", "5", "231"],
                ["B2", "5", "231"],
                ["NA", "0", "0"],
            ],
            [
                ["1", "5700", "4500"],
                ["2", "5700", "4500"],
                ["3", "5700", "4500"],
            ],
            [["43.5kVA"]],
        ]
    )
    assert section is not None
    discovered = sorted(discover_apc_netshelterpdu_power(section), key=lambda s: s.item or "")
    assert discovered == [
        Service(item="Bank B1"),
        Service(item="Bank B2"),
        Service(item="Device mypdu"),
        Service(item="Phase 1"),
        Service(item="Phase 2"),
        Service(item="Phase 3"),
    ]


# --- check function tests ---


def _make_phase_section(
    current: float = 6.2,
    power: float = 1431.0,
    warn: float | None = 45.0,
    crit: float | None = 57.0,
) -> dict[str, NetShelterPDUItem]:
    return {
        "Phase 1": NetShelterPDUItem(
            current=CurrentReading(value=current),
            power=power,
            warn_current=warn,
            crit_current=crit,
        ),
    }


def _make_device_section(power: float = 4583.0, load: float = 10.5) -> dict[str, NetShelterPDUItem]:
    return {
        "Device mypdu": NetShelterPDUItem(
            power=power,
            output_load=load,
        ),
    }


def test_check_missing_item() -> None:
    section = _make_phase_section()
    results = list(check_apc_netshelterpdu_power("nonexistent", {}, section))
    assert results == []


def test_check_device_thresholds_applied_as_defaults() -> None:
    section = _make_phase_section(current=50.0, warn=45.0, crit=57.0)
    results = list(check_apc_netshelterpdu_power("Phase 1", {}, section))
    assert any(
        isinstance(r, Result) and r.state == State.WARN and "50.0 A" in r.summary for r in results
    )


def test_check_user_params_override_device_thresholds() -> None:
    section = _make_phase_section(current=50.0, warn=45.0, crit=57.0)
    results = list(check_apc_netshelterpdu_power("Phase 1", {"current": (55.0, 60.0)}, section))
    assert any(
        isinstance(r, Result) and r.state == State.OK and "50.0 A" in r.summary for r in results
    )


def test_check_output_load_default_thresholds() -> None:
    section = _make_device_section(load=85.0)
    results = list(check_apc_netshelterpdu_power("Device mypdu", {}, section))
    assert any(
        isinstance(r, Result) and r.state == State.WARN and "85.0" in r.summary for r in results
    )
    assert any(isinstance(r, Metric) and r.name == "output_load" for r in results)


def test_check_output_load_user_override() -> None:
    section = _make_device_section(load=85.0)
    results = list(
        check_apc_netshelterpdu_power("Device mypdu", {"output_load": (90, 95)}, section)
    )
    assert any(
        isinstance(r, Result) and r.state == State.OK and "85.0" in r.summary for r in results
    )


def test_check_no_device_thresholds() -> None:
    section = _make_phase_section(current=50.0, warn=None, crit=None)
    results = list(check_apc_netshelterpdu_power("Phase 1", {}, section))
    assert any(
        isinstance(r, Result) and r.state == State.OK and "50.0 A" in r.summary for r in results
    )
