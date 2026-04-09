#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.plugins.lib.uptime import parse_snmp_uptime, parse_snmp_uptime_pair, Section


def test_parse_snmp_uptime_pair_with_empty_section_is_none() -> None:
    parsed_uptime = parse_snmp_uptime_pair([[]])
    assert parsed_uptime is None


def test_parse_snmp_uptime_pair_with_no_values_is_not_valid() -> None:
    parsed_uptime = parse_snmp_uptime_pair([["", ""]])

    assert parsed_uptime is not None
    assert not parsed_uptime
    with pytest.raises(ValueError):
        _ = parsed_uptime.max_uptime_sec
    assert parsed_uptime.sys_uptime_sec is None
    assert parsed_uptime.hr_sys_uptime_sec is None


def test_parse_snmp_uptime_pair_with_sys_uptime_only_has_parsed_value() -> None:
    parsed_uptime = parse_snmp_uptime_pair([["500000", ""]])

    assert parsed_uptime
    assert parsed_uptime.max_uptime_sec == 5000
    assert parsed_uptime.sys_uptime_sec == 5000
    assert parsed_uptime.hr_sys_uptime_sec is None


def test_parse_snmp_uptime_pair_with_hr_sys_uptime_only_has_parsed_value() -> None:
    parsed_uptime = parse_snmp_uptime_pair([["", "500000"]])

    assert parsed_uptime
    assert parsed_uptime.max_uptime_sec == 5000
    assert parsed_uptime.sys_uptime_sec is None
    assert parsed_uptime.hr_sys_uptime_sec == 5000


def test_parse_snmp_uptime_pair_with_both_uptime_values_has_parsed_values() -> None:
    parsed_uptime = parse_snmp_uptime_pair([["500000", "500500"]])

    assert parsed_uptime
    assert parsed_uptime.max_uptime_sec == 5005
    assert parsed_uptime.sys_uptime_sec == 5000
    assert parsed_uptime.hr_sys_uptime_sec == 5005


def test_parse_snmp_uptime_pair_with_both_values_but_hr_uptime_is_zero_second_value_is_not_none() -> (
    None
):
    parsed_uptime = parse_snmp_uptime_pair([["500000", "0"]])

    assert parsed_uptime
    assert parsed_uptime.max_uptime_sec == 5000
    assert parsed_uptime.sys_uptime_sec == 5000
    assert parsed_uptime.hr_sys_uptime_sec == 0


def test_parse_snmp_uptime_parses_with_zero_values() -> None:
    assert parse_snmp_uptime([["0", ""]]) == Section(uptime_sec=0, message=None)
    assert parse_snmp_uptime([["", "0"]]) == Section(uptime_sec=0, message=None)
    assert parse_snmp_uptime([["0", "0"]]) == Section(uptime_sec=0, message=None)


def test_parse_snmp_uptime_is_none_with_empty_data() -> None:
    assert parse_snmp_uptime([["", ""]]) is None


def test_parse_snmp_uptime_is_none_with_nonsense_data() -> None:
    assert parse_snmp_uptime([["", "Fortigate 80C"]]) is None
    assert parse_snmp_uptime([["Fortigate 80C", ""]]) is None


def test_parse_snmp_uptime_parses_with_only_sys_up_time() -> None:
    assert parse_snmp_uptime([["2297331594", ""]]) == Section(uptime_sec=22973315, message=None)


def test_parse_snmp_uptime_parses_with_only_hr_system_up_time() -> None:
    assert parse_snmp_uptime([["", "2297331594"]]) == Section(uptime_sec=22973315, message=None)


def test_parse_snmp_uptime_prefers_sys_up_time_with_unexpected_hr_system_up_time() -> None:
    # would have been None with the previous logic
    assert parse_snmp_uptime([["2297331594", "9"]]) == Section(uptime_sec=22973315, message=None)
    assert parse_snmp_uptime([["2297331594", "99"]]) == Section(uptime_sec=22973315, message=None)


def test_parse_snmp_uptime_prefers_hr_system_up_time_with_with_valid_hr_value() -> None:
    # keeping the old behavior and not trying to guess the correct value
    assert parse_snmp_uptime([["2297331594", "0"]]) == Section(uptime_sec=0, message=None)
    assert parse_snmp_uptime([["2297331594", "999"]]) == Section(uptime_sec=9, message=None)
    assert parse_snmp_uptime([["2297331594", "2297331"]]) == Section(uptime_sec=22973, message=None)

    assert parse_snmp_uptime([["0", "2297331694"]]) == Section(uptime_sec=22973316, message=None)
    assert parse_snmp_uptime([["9", "2297331694"]]) == Section(uptime_sec=22973316, message=None)
    assert parse_snmp_uptime([["99", "2297331694"]]) == Section(uptime_sec=22973316, message=None)
    assert parse_snmp_uptime([["999", "2297331694"]]) == Section(uptime_sec=22973316, message=None)
    assert parse_snmp_uptime([["2297331", "2297331694"]]) == Section(
        uptime_sec=22973316, message=None
    )


def test_parse_snmp_uptime_prefers_hr_system_up_time() -> None:
    assert parse_snmp_uptime([["2267331694", "2297331694"]]) == Section(
        uptime_sec=22973316, message=None
    )


def test_parse_snmp_uptime_parses_with_sys_up_timestamp_and_hr_system_up_timestamp() -> None:
    assert parse_snmp_uptime([["124:21:26:42.03", "124:21:29:01.14"]]) == Section(
        uptime_sec=10790941, message=None
    )


def test_parse_snmp_uptime_parses_mixed_formats() -> None:
    assert parse_snmp_uptime([["124:21:26:42.03", "1079094124"]]) == Section(
        uptime_sec=10790941, message=None
    )

    assert parse_snmp_uptime([["1079094124", "124:21:26:42.03"]]) == Section(
        uptime_sec=10790802, message=None
    )


def test_parse_snmp_uptime_parses_with_only_hr_system_up_timestamp() -> None:
    assert parse_snmp_uptime([["", "124:21:29:01.14"]]) == Section(
        uptime_sec=10790941, message=None
    )


def test_parse_snmp_uptime_parses_with_only_sys_up_timestamp() -> None:
    assert parse_snmp_uptime([["124:21:26:42.03", ""]]) == Section(
        uptime_sec=10790802, message=None
    )
