#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.hp_msa.agent_based.hp_msa_psu import (
    agent_section_hp_msa_psu_health,
    check_hp_msa_psu_temp_testable,
    check_plugin_hp_msa_psu_health,
    check_plugin_hp_msa_psu_sensor,
    check_plugin_hp_msa_psu_temp,
)
from cmk.plugins.hp_msa.agent_based.lib import Section


def _section() -> Section:
    assert (
        section := agent_section_hp_msa_psu_health.parse_function(
            [
                ["power-supplies", "3", "durable-id", "psu_1.2"],
                ["power-supplies", "3", "url", "/power-supplies/psu_1.2"],
                ["power-supplies", "3", "enclosures-url", "/enclosures/1"],
                ["power-supplies", "3", "enclosure-id", "1"],
                ["power-supplies", "3", "dom-id", "2"],
                ["power-supplies", "3", "serial-number", "7CE849T228"],
                ["power-supplies", "3", "part-number", "814665-001"],
                ["power-supplies", "3", "description", "FRU,Pwr", "Sply,595W,AC,2U,LC,HP", "ES"],
                ["power-supplies", "3", "name", "PSU", "2,", "Right"],
                ["power-supplies", "3", "fw-revision", "N/A"],
                ["power-supplies", "3", "revision", "C1"],
                ["power-supplies", "3", "model", "814665-001"],
                ["power-supplies", "3", "vendor"],
                ["power-supplies", "3", "location", "Enclosure", "1", "-", "Right"],
                ["power-supplies", "3", "position", "Right"],
                ["power-supplies", "3", "position-numeric", "1"],
                ["power-supplies", "3", "dash-level"],
                ["power-supplies", "3", "fru-shortname", "AC", "Power", "Supply"],
                ["power-supplies", "3", "mfg-date", "2018-11-14", "16:44:48"],
                ["power-supplies", "3", "mfg-date-numeric", "1542213888"],
                ["power-supplies", "3", "mfg-location", "Zhongshan,Guangdong,CN"],
                ["power-supplies", "3", "mfg-vendor-id"],
                ["power-supplies", "3", "configuration-serialnumber", "7CE849T228"],
                ["power-supplies", "3", "dc12v", "0"],
                ["power-supplies", "3", "dc5v", "0"],
                ["power-supplies", "3", "dc33v", "0"],
                ["power-supplies", "3", "dc12i", "0"],
                ["power-supplies", "3", "dc5i", "0"],
                ["power-supplies", "3", "dctemp", "0"],
                ["power-supplies", "3", "health", "OK"],
                ["power-supplies", "3", "health-numeric", "0"],
                ["power-supplies", "3", "health-reason"],
                ["power-supplies", "3", "health-recommendation"],
                ["power-supplies", "3", "status", "Up"],
                ["power-supplies", "3", "status-numeric", "0"],
            ]
        )
    )
    return section


def test_discovery_health() -> None:
    assert list(check_plugin_hp_msa_psu_health.discovery_function(_section())) == [
        Service(item="Enclosure 1 Right"),
    ]


def test_discovery_sensor() -> None:
    assert not list(check_plugin_hp_msa_psu_sensor.discovery_function(_section()))


def test_discovery_temp() -> None:
    assert not list(check_plugin_hp_msa_psu_temp.discovery_function(_section()))


DEFAULT_PARAMS = {
    "levels_12v_lower": (11.9, 11.8),
    "levels_12v_upper": (12.1, 12.2),
    "levels_33v_lower": (3.25, 3.2),
    "levels_33v_upper": (3.4, 3.45),
    "levels_5v_lower": (4.9, 4.8),
    "levels_5v_upper": (5.1, 5.2),
}


def test_check_health() -> None:
    assert list(check_plugin_hp_msa_psu_health.check_function("Enclosure 1 Right", _section())) == [
        Result(state=State.OK, summary="Status: OK")
    ]


def test_check_sensor() -> None:
    assert list(
        check_plugin_hp_msa_psu_sensor.check_function(
            "Enclosure 1 Right", DEFAULT_PARAMS, _section()
        )
    ) == [
        Result(state=State.CRIT, summary="12 V: 0.00 V (warn/crit below 11.90 V/11.80 V)"),
        Result(state=State.CRIT, summary="5 V: 0.00 V (warn/crit below 4.90 V/4.80 V)"),
        Result(state=State.CRIT, summary="3.3 V: 0.00 V (warn/crit below 3.25 V/3.20 V)"),
    ]


def test_check_temp() -> None:
    assert list(
        check_hp_msa_psu_temp_testable("Enclosure 1 Right", {"levels": (40, 45)}, _section(), {})
    ) == [
        Metric("temp", 0.0, levels=(40, 45)),
        Result(state=State.OK, summary="Temperature: 0.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]
