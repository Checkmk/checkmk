#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringByteTable
from cmk.plugins.audiocodes.agent_based.leds import (
    check_audiocodes_leds,
    discover_audiocodes_leds,
    parse_audiocodes_leds,
)
from cmk.plugins.audiocodes.agent_based.module_names import (
    parse_module_names,
)

_MEDIAPACK_124 = "3"
_MEDIAPACK_118 = "56"
_MEDIANT_4000_CPU = "280"
_MEDIANT_4000_MP = "295"


def _leds(*octets: int) -> list[int]:
    return [*octets, *[0xEE] * (20 - len(octets))]


_GREEN = _leds(0xE2)

_MEDIAPACK_124_WITH_SRTP = _leds(0, 0, 0, 0, 0, 0, 0, 0, 0, 0x44, 0x44, 0x44, 0x00, 0x22)

_MODULE_NAMES = parse_module_names(
    [
        ["67387393", "Mediant-4000 Media Processing Module"],
        ["67907585", "Mediant-4000 CPU Module"],
    ]
)


def _mediant_4000(*, cpu_module_leds: list[int] = _GREEN) -> Sequence[StringByteTable]:
    return [
        [
            ["67387393", _MEDIANT_4000_MP, _GREEN, "0"],
            ["67907585", _MEDIANT_4000_CPU, cpu_module_leds, "8"],
        ],
        [["1", "M4K's Fan-Tray ID 1", _GREEN]],
        [["1", _GREEN]],
        [],
        [],
    ]


def _mediapack(module_type: str, leds: list[int], *, num_ports: str) -> Sequence[StringByteTable]:
    return [[["1", module_type, leds, num_ports]], [], [], [], []]


def _check(string_table: Sequence[StringByteTable]) -> CheckResult:
    return check_audiocodes_leds(_MODULE_NAMES, parse_audiocodes_leds(string_table))


def test_discovery_function() -> None:
    section_leds = parse_audiocodes_leds(_mediant_4000())

    services = list(discover_audiocodes_leds(_MODULE_NAMES, section_leds))

    assert services == [Service()]


def test_parse_audiocodes_leds() -> None:
    assert parse_audiocodes_leds([]) is None
    assert parse_audiocodes_leds([[], [], [], [], []]) is None


def test_all_tables_with_one_lit_led_per_row() -> None:
    string_table: Sequence[StringByteTable] = [
        [
            ["67387393", _MEDIANT_4000_MP, _GREEN, "0"],
            ["67907585", _MEDIANT_4000_CPU, _GREEN, "8"],
        ],
        [
            ["1", "M4K's Fan-Tray ID 1", _GREEN],
            ["2", "M4K's Fan-Tray ID 2", _GREEN],
        ],
        [
            ["1", _GREEN],
            ["2", _GREEN],
        ],
        [
            ["1", "M4K's Fan-Tray ID 1", _GREEN],
            ["2", "M4K's Fan-Tray ID 2", _GREEN],
        ],
        [
            ["1", _GREEN],
            ["2", _GREEN],
        ],
    ]

    results = list(_check(string_table))

    assert results == [
        Result(state=State.OK, notice="Mediant-4000 Media Processing Module LED: on-green"),
        Result(state=State.OK, notice="Mediant-4000 CPU Module LED: on-green"),
        Result(state=State.OK, notice="M4K's Fan-Tray ID 1 LED: on-green"),
        Result(state=State.OK, notice="M4K's Fan-Tray ID 2 LED: on-green"),
        Result(state=State.OK, notice="M4K's Fan-Tray ID 1 (redundant) LED: on-green"),
        Result(state=State.OK, notice="M4K's Fan-Tray ID 2 (redundant) LED: on-green"),
        Result(state=State.OK, notice="Power supply 1 LED: on-green"),
        Result(state=State.OK, notice="Power supply 2 LED: on-green"),
        Result(state=State.OK, notice="Power supply 1 (redundant) LED: on-green"),
        Result(state=State.OK, notice="Power supply 2 (redundant) LED: on-green"),
        Result(state=State.OK, summary="10 green LEDs"),
    ]


@pytest.mark.parametrize(
    "cpu_module_leds, expected",
    [
        pytest.param(
            _leds(0xE4),
            Result(state=State.CRIT, notice="Mediant-4000 CPU Module LED: on-red"),
            id="steady red is CRIT",
        ),
        pytest.param(
            _leds(0xE5),
            Result(state=State.CRIT, notice="Mediant-4000 CPU Module LED: flashing-red"),
            id="flashing red is CRIT",
        ),
        pytest.param(
            _leds(0xE6),
            Result(state=State.WARN, notice="Mediant-4000 CPU Module LED: on-yellow"),
            id="yellow is WARN",
        ),
        pytest.param(
            _leds(0xE9),
            Result(state=State.WARN, notice="Mediant-4000 CPU Module LED: flashing-orange"),
            id="orange is WARN",
        ),
        pytest.param(
            _leds(0xEB),
            Result(state=State.WARN, notice="Mediant-4000 CPU Module LED: flashing-blue"),
            id="blue is WARN",
        ),
        pytest.param(
            _leds(0xEC),
            Result(state=State.UNKNOWN, notice="Mediant-4000 CPU Module LED: on-undefined"),
            id="undefined colour is UNKNOWN",
        ),
    ],
)
def test_led_color_sets_the_state(cpu_module_leds: list[int], expected: Result) -> None:
    results = list(_check(_mediant_4000(cpu_module_leds=cpu_module_leds)))

    assert results[1] == expected


def test_all_leds_of_a_module_are_evaluated() -> None:
    mp_118_leds = _leds(0x00, 0x33, 0x33, 0x33, 0x02, 0x22)

    results = list(_check(_mediapack(_MEDIAPACK_118, mp_118_leds, num_ports="2")))

    assert results == [
        Result(state=State.OK, notice="acMediaPack-118 LEDs: 6 flashing-green, 3 on-green"),
        Result(state=State.OK, summary="9 green LEDs"),
    ]


def test_summary_of_a_faulty_module_names_only_the_faulty_leds() -> None:
    results = list(_check(_mediant_4000(cpu_module_leds=_leds(0x44, 0x22))))

    assert results[1] == Result(
        state=State.CRIT,
        notice="Mediant-4000 CPU Module LEDs: 2 on-red",
        details="Mediant-4000 CPU Module LEDs: 2 on-red, 2 on-green",
    )


@pytest.mark.parametrize(
    "module_type, expected_name",
    [
        pytest.param(_MEDIAPACK_124, "acMediaPack-124", id="known module type"),
        pytest.param("0", "(unknown module)", id="module type acUnknown"),
        pytest.param("9999", "(unknown module)", id="module type not in the MIB"),
    ],
)
def test_module_without_name_uses_the_module_type(module_type: str, expected_name: str) -> None:
    results = list(_check(_mediapack(module_type, _GREEN, num_ports="")))

    assert results[0] == Result(state=State.OK, notice=f"{expected_name} LED: on-green")


def test_flashing_red_is_ok_on_mediapack_124() -> None:
    results = list(_check(_mediapack(_MEDIAPACK_124, _leds(0xE5), num_ports="24")))

    assert results[0] == Result(state=State.OK, notice="acMediaPack-124 LED: flashing-red")


def test_mediapack_124_ignores_channel_leds_of_unavailable_ports() -> None:
    results = list(_check(_mediapack(_MEDIAPACK_124, _MEDIAPACK_124_WITH_SRTP, num_ports="18")))

    assert results == [
        Result(state=State.OK, notice="acMediaPack-124 LEDs: 2 on-green"),
        Result(state=State.OK, summary="2 green LEDs"),
    ]


@pytest.mark.parametrize(
    "leds, num_ports, expected",
    [
        pytest.param(
            _leds(0x04),
            "18",
            Result(state=State.CRIT, notice="acMediaPack-124 LED: on-red"),
            id="channel of an available port",
        ),
        pytest.param(
            _leds(*[0x00] * 12, 0x04),
            "18",
            Result(state=State.CRIT, notice="acMediaPack-124 LED: on-red"),
            id="status LED after the channels",
        ),
        pytest.param(
            _MEDIAPACK_124_WITH_SRTP,
            "",
            Result(
                state=State.CRIT,
                notice="acMediaPack-124 LEDs: 6 on-red",
                details="acMediaPack-124 LEDs: 6 on-red, 2 on-green",
            ),
            id="port count not reported",
        ),
        pytest.param(
            _MEDIAPACK_124_WITH_SRTP,
            "-1",
            Result(
                state=State.CRIT,
                notice="acMediaPack-124 LEDs: 6 on-red",
                details="acMediaPack-124 LEDs: 6 on-red, 2 on-green",
            ),
            id="port count not applicable",
        ),
        pytest.param(
            _MEDIAPACK_124_WITH_SRTP,
            "24",
            Result(
                state=State.CRIT,
                notice="acMediaPack-124 LEDs: 6 on-red",
                details="acMediaPack-124 LEDs: 6 on-red, 2 on-green",
            ),
            id="all ports available",
        ),
    ],
)
def test_mediapack_124_evaluates_leds_outside_the_unavailable_channels(
    leds: list[int], num_ports: str, expected: Result
) -> None:
    results = list(_check(_mediapack(_MEDIAPACK_124, leds, num_ports=num_ports)))

    assert results[0] == expected


def test_rows_without_lit_led_are_skipped() -> None:
    string_table: Sequence[StringByteTable] = [
        [
            ["67387393", _MEDIANT_4000_MP, _leds(0x22, 0x22), "0"],
            ["67907585", _MEDIANT_4000_CPU, _leds(0x00, 0x00, 0x00, 0x00), "8"],
            ["70012929", "0", _leds(), "0"],
        ],
        [["1", "M4K's Fan-Tray ID 1", _leds(0xE0)]],
        [["1", _leds(0xE0)]],
        [],
        [],
    ]

    results = list(_check(string_table))

    assert results == [
        Result(state=State.OK, notice="Mediant-4000 Media Processing Module LEDs: 4 on-green"),
        Result(state=State.OK, summary="4 green LEDs"),
    ]


def test_no_lit_led() -> None:
    results = list(_check(_mediapack(_MEDIAPACK_118, _leds(), num_ports="2")))

    assert results == [Result(state=State.OK, summary="No LEDs lit")]
