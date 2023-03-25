#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import pytest

from cmk.base.api.agent_based.checking_classes import CheckFunction, DiscoveryFunction
from cmk.base.plugins.agent_based import etherbox
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.fixture(name="discovery", scope="module")
def _discovery() -> DiscoveryFunction:
    return etherbox.discovery_temp


@pytest.fixture(name="check_smoke", scope="module")
def _check_smoke() -> CheckFunction:
    return etherbox.check_etherbox_smoke


@pytest.fixture(name="check_switch", scope="module")
def _check_switch() -> CheckFunction:
    return etherbox.check_etherbox_switch_contact


@pytest.fixture(name="check_humidity", scope="module")
def _check_humidity() -> CheckFunction:
    return etherbox.check_etherbox_humidity


@pytest.fixture(name="check_temp", scope="module")
def _check_temp() -> CheckFunction:
    return etherbox.check_etherbox_temp


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


def test_discovery(discovery: DiscoveryFunction) -> None:
    # ignore second entry
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "ImpfKS 1", "1", "74"],
            ],
        ]
    )
    services = list(discovery(section))
    assert services == [Service(item="9.1")]


def test_sensor_type_not_found(check_smoke: CheckFunction) -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "ImpfKS 1", "1", "74"],
            ],
        ]
    )
    results = list(check_smoke(item="9.6", section=section, params={"levels": (0, 0)}))
    assert set(results) == {
        Result(state=State.UNKNOWN, summary="Sensor type changed 9.6"),
    }


def test_sensor_not_found(check_smoke: CheckFunction) -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "4", "n", "1", "74"],
            ],
        ]
    )
    results = list(check_smoke(item="9.6", section=section, params={"levels": (0, 0)}))
    assert set(results) == {
        Result(state=State.UNKNOWN, summary="Sensor not found"),
    }


def test_check_smoke(check_smoke: CheckFunction) -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "6", "42"],
            ],
        ]
    )
    results = list(check_smoke(item="9.6", section=section, params={"levels": (0, 0)}))
    assert set(results) == {
        Result(state=State.CRIT, summary="Smoke Alarm: 42.00 (warn/crit at 0.00/0.00)"),
        Metric("smoke", 42.0, levels=(0, 0)),
    }


def test_check_switch(check_switch: CheckFunction) -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "3", "42"],
            ],
        ]
    )
    results = list(check_switch(item="9.3", section=section, params={"state": "closed"}))
    assert set(results) == {
        Result(state=State.OK, summary="[n] Switch contact closed"),
        Metric("switch_contact", 42.0),
    }


def test_check_humidity(check_humidity: CheckFunction) -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "4", "42"],
            ],
        ]
    )
    results = list(check_humidity(item="9.4", section=section, params={}))
    assert set(results) == {
        Result(state=State.OK, summary="[n] 4.20%"),
        Metric("humidity", 4.2, boundaries=(0, 100.0)),
    }


@pytest.mark.usefixtures("initialised_item_state")
def test_check_temp(check_temp: CheckFunction) -> None:
    section = etherbox.etherbox_convert(
        [
            [["0"]],
            [
                ["1", "9", "n", "1", "42"],
            ],
        ]
    )
    results = list(
        check_temp(
            item="9.1",
            section=section,
            params={},
        )
    )
    assert set(results) == {
        Result(state=State.OK, summary="[n] Temperature: 4.2°C"),
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
        etherbox.check_etherbox_voltage(item="9.1", section=section, params={"levels": (0, 0)})
    )
    assert set(results) == {
        Metric("voltage", 42.0, levels=(0.0, 0.0)),
        Result(state=State.CRIT, summary="42.00 (warn/crit at 0.00/0.00)"),
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
