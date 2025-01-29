#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based import etherbox


def test_parsing() -> None:
    string_table = [
        [["0"]],
        [
            ["1", "1", "ImpfKS 1", "1", "74"],
            ["2", "2", "Sensor 2", "1", "0"],
            ["3", "3", "Sensor 3", "1", "0"],
            ["4", "4", "Sensor 4", "1", "0"],
            ["5", "5", "Sensor 5", "3", "0"],
            ["6", "6", "Sensor 6", "3", "0"],
            ["7", "7", "Sensor 7", "3", "0"],
            ["8", "8", "Sensor 8", "3", "0"],
            ["9", "9", "Sensor 9", "0", "0"],
            ["10", "10", "Sensor 10", "0", "0"],
            ["11", "11", "Sensor 11", "0", "0"],
            ["12", "12", "Sensor 12", "0", "0"],
        ],
    ]
    etherbox.etherbox_convert(string_table)


def test_discovery_temp() -> None:
    # ignore second entry
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "ImpfKS 1", "1", "74"],
            ],
        ]
    )
    assert section
    services = list(etherbox.discovery_temp(section))
    assert services == [Service(item="9.1")]


def test_check_smoke_sensor_type_not_found() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "ImpfKS 1", "1", "74"],
            ],
        ]
    )
    assert section
    results = list(
        etherbox.check_etherbox_smoke(
            item="9.6",
            section=section,
            params={"smoke_handling": ("binary", (0, 2))},
        )
    )
    assert set(results) == {
        Result(state=State.UNKNOWN, summary="Sensor type changed 9.6"),
    }


def test_check_smoke_sensor_not_found() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "4", "n", "1", "74"],
            ],
        ]
    )
    assert section
    results = list(
        etherbox.check_etherbox_smoke(
            item="9.6",
            section=section,
            params={"smoke_handling": ("binary", (0, 2))},
        )
    )
    assert set(results) == {
        Result(state=State.UNKNOWN, summary="Sensor not found"),
    }


@pytest.mark.parametrize(
    ["section", "params", "expected_result"],
    [
        pytest.param(
            etherbox.Section(
                unit_of_measurement="c",
                sensor_data={"9": {"6": etherbox.SensorData(name="n", value=0)}},
            ),
            {"smoke_handling": ("binary", (0, 2))},
            [
                Result(state=State.OK, summary="No smoke detected"),
                Metric("smoke", 0.0),
            ],
            id="binary, no smoke detected",
        ),
        pytest.param(
            etherbox.Section(
                unit_of_measurement="c",
                sensor_data={"9": {"6": etherbox.SensorData(name="n", value=42)}},
            ),
            {"smoke_handling": ("binary", (0, 2))},
            [
                Result(state=State.CRIT, summary="Smoke detected"),
                Metric("smoke", 42.0),
            ],
            id="binary, smoke detected",
        ),
        pytest.param(
            etherbox.Section(
                unit_of_measurement="c",
                sensor_data={"9": {"6": etherbox.SensorData(name="n", value=42)}},
            ),
            {"smoke_handling": ("levels", (0, 0))},
            [
                Result(state=State.CRIT, summary="Smoke level: 42.00 (warn/crit at 0.00/0.00)"),
                Metric("smoke", 42.0, levels=(0, 0)),
            ],
            id="levels",
        ),
    ],
)
def test_check_smoke(
    section: etherbox.Section,
    params: etherbox.SmokeParams,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            etherbox.check_etherbox_smoke(
                item="9.6",
                section=section,
                params=params,
            )
        )
        == expected_result
    )


def test_check_switch() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "3", "42"],
            ],
        ]
    )
    assert section
    results = list(
        etherbox.check_etherbox_switch_contact(
            item="9.3", section=section, params={"state": "closed"}
        )
    )
    assert set(results) == {
        Result(state=State.OK, summary="[n] Switch contact closed"),
        Metric("switch_contact", 42.0),
    }


def test_check_humidity() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "4", "42"],
            ],
        ]
    )
    assert section
    results = list(etherbox.check_etherbox_humidity(item="9.4", section=section, params={}))
    assert set(results) == {
        Result(state=State.OK, summary="[n] 4.20%"),
        Metric("humidity", 4.2, boundaries=(0, 100.0)),
    }


@pytest.mark.usefixtures("initialised_item_state")
def test_check_temp() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "1", "42"],
            ],
        ]
    )
    assert section
    results = list(
        etherbox.check_etherbox_temp(
            item="9.1",
            section=section,
            params={},
        )
    )
    assert set(results) == {
        Result(state=State.OK, summary="[n] Temperature: 4.2 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
        Metric("temp", 4.2),
    }


def test_check_voltage() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "1", "42"],
            ],
        ]
    )
    assert section
    results = list(
        etherbox.check_etherbox_voltage(
            item="9.1", section=section, params={"levels": ("fixed", (0, 0))}
        )
    )
    assert set(results) == {
        Metric("voltage", 42.0, levels=(0.0, 0.0)),
        Result(state=State.CRIT, summary="42.00 V (warn/crit at 0.00 V/0.00 V)"),
    }


def test_check_nosensor() -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "0", "42"],
            ],
        ]
    )
    assert section
    results = list(etherbox.check_etherbox_nosensor(item="9.0", section=section))
    assert set(results) == {
        Result(state=State.OK, summary="[n] no sensor connected"),
    }
