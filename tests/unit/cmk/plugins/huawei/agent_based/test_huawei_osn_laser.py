#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.huawei.agent_based import huawei_osn_laser
from cmk.plugins.huawei.agent_based.huawei_osn_laser import HuaweiOsnLaserParams

# item, laser output in 0.1 dBm, laser input in 0.1 dBm, FEC before, FEC after
STRING_TABLE: StringTable = [["1", "-300", "-1200", "1e-9", "1e-12"]]

PARAMS = HuaweiOsnLaserParams(
    levels_low_in=("fixed", (-160, -180)), levels_low_out=("fixed", (-35, -40))
)


def test_parse_keeps_the_string_table() -> None:
    assert huawei_osn_laser.parse_huawei_osn_laser(STRING_TABLE) == STRING_TABLE


def test_discover_one_service_per_laser() -> None:
    assert list(huawei_osn_laser.discover_huawei_osn_laser(STRING_TABLE)) == [Service(item="1")]


def test_discover_without_any_laser() -> None:
    assert list(huawei_osn_laser.discover_huawei_osn_laser([])) == []


def test_check_reports_input_output_and_fec() -> None:
    """The device reports tenths of a dBm, so every reading is scaled by 10."""
    assert list(huawei_osn_laser.check_huawei_osn_laser("1", PARAMS, STRING_TABLE)) == [
        Result(state=State.OK, summary="In: -120.0 dBm"),
        Metric("input_signal_power_dBm", -120.0),
        Result(state=State.OK, summary="Out: -30.0 dBm"),
        Metric("output_signal_power_dBm", -30.0),
        Result(state=State.OK, summary="FEC Correction before/after: 1e-9/1e-12"),
    ]


def test_check_applies_the_lower_levels() -> None:
    """Only lower levels are checked: the signal must not get too weak."""
    section: StringTable = [["1", "-500", "-2000", "", ""]]

    assert list(huawei_osn_laser.check_huawei_osn_laser("1", PARAMS, section)) == [
        Result(
            state=State.CRIT,
            summary="In: -200.0 dBm (warn/crit below -160.0 dBm/-180.0 dBm)",
        ),
        Metric("input_signal_power_dBm", -200.0),
        Result(
            state=State.CRIT,
            summary="Out: -50.0 dBm (warn/crit below -35.0 dBm/-40.0 dBm)",
        ),
        Metric("output_signal_power_dBm", -50.0),
    ]


def test_check_omits_fec_when_the_device_does_not_report_it() -> None:
    section: StringTable = [["1", "-300", "-1200", "", ""]]

    results = list(huawei_osn_laser.check_huawei_osn_laser("1", PARAMS, section))

    assert not any(isinstance(result, Result) and "FEC" in result.summary for result in results)


def test_check_of_a_laser_the_device_no_longer_reports() -> None:
    assert list(huawei_osn_laser.check_huawei_osn_laser("9", PARAMS, STRING_TABLE)) == []
