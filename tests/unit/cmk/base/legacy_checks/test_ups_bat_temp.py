#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.ups_bat_temp import check_ups_bat_temp, parse_ups_bat_temp


def test_check_ups_bat_temp_ok() -> None:
    section = parse_ups_bat_temp([["1", "25"], ["2", "27"]])
    status, infotext, _perfdata = check_ups_bat_temp("Battery 1", {"levels": (40.0, 50.0)}, section)
    assert status == 0
    assert "25" in infotext


def test_check_ups_bat_temp_crit() -> None:
    section = parse_ups_bat_temp([["1", "60"]])
    status, _infotext, _perfdata = check_ups_bat_temp(
        "Battery 1", {"levels": (40.0, 50.0)}, section
    )
    assert status == 2


def test_check_ups_bat_temp_item_not_found() -> None:
    assert (
        check_ups_bat_temp("Battery 9", {"levels": (40.0, 50.0)}, parse_ups_bat_temp([["1", "25"]]))
        is None
    )


def test_check_ups_bat_temp_empty_temperature() -> None:
    # Some UPS devices (e.g. the CS141 SNMP/WEB Adapter) report an empty battery
    # temperature. The check must skip instead of crashing.
    section = parse_ups_bat_temp([["CS141 SNMP/WEB Adapter", ""]])
    assert (
        check_ups_bat_temp("Battery CS141 SNMP/WEB Adapter", {"levels": (40.0, 50.0)}, section)
        is None
    )
