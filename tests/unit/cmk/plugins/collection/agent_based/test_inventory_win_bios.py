#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from datetime import datetime, UTC
from typing import Final

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.inventory_win_bios import inventory_win_bios, parse_win_bios

OUTPUT: Final = """Manufacturer       : innotek GmbH
Name               : Default System BIOS
BIOSVersion        : {VBOX   - 1}
ListOfLanguages    :
PrimaryBIOS        : True
ReleaseDate        : 20061201000000.000000+000
SMBIOSBIOSVersion  : VirtualBox
SMBIOSMajorVersion : 2
SMBIOSMinorVersion : 5
"""


def _utc_to_unix_seconds(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> int:
    """The instant the BIOS date denotes, spelled out in UTC."""
    return int(datetime(year, month, day, hour, minute, second, tzinfo=UTC).timestamp())


# A firmware that does not populate the SMBIOS release date: CIM returns $null and the
# plug-in renders it as an empty value. Common on virtual machines.
# See: SUP-30953
OUTPUT_WITHOUT_RELEASE_DATE: Final = """BIOSVersion: NOCHS  - 1 20260522 Company - 10000
InstallDate:
ListOfLanguages:
Manufacturer: Company
Name: 20260522
PrimaryBIOS: True
ReleaseDate:
SerialNumber: A3dc7555-22f2-aaaa-9999-983d2d9e3bfE
SMBIOSBIOSVersion: 20260522
SMBIOSMajorVersion: 2
SMBIOSMinorVersion: 8
"""


@pytest.fixture(name="section")
def _get_section() -> Mapping[str, str | int]:
    return parse_win_bios([line.split(":") for line in OUTPUT.split("\n")])


def test_inventory_win_bios(section: Mapping[str, str | int]) -> None:
    assert list(inventory_win_bios(section)) == [
        Attributes(
            path=["software", "bios"],
            inventory_attributes={
                "date": _utc_to_unix_seconds(2006, 12, 1),
                "model": "Default System BIOS",
                "vendor": "innotek GmbH",
                "version": "VirtualBox 2.5",
            },
        )
    ]


@pytest.mark.parametrize(
    "release_date, expected",
    [
        pytest.param("20061201000000.000000+000", _utc_to_unix_seconds(2006, 12, 1), id="utc"),
        # The offset belongs to the reported local time, so a positive one puts the instant
        # earlier in UTC and a negative one later.
        pytest.param(
            "20061201000000.000000+060",
            _utc_to_unix_seconds(2006, 11, 30, 23),
            id="positive_offset",
        ),
        pytest.param(
            "20061201000000.000000-480",
            _utc_to_unix_seconds(2006, 12, 1, 8),
            id="negative_offset",
        ),
        pytest.param(
            "20061201134502.000000+000",
            _utc_to_unix_seconds(2006, 12, 1, 13, 45, 2),
            id="with_time_of_day",
        ),
        # Offset and time of day together: 13:45:02 at UTC-05:30 is 19:15:02 UTC.
        pytest.param(
            "20061201134502.000000-330",
            _utc_to_unix_seconds(2006, 12, 1, 19, 15, 2),
            id="time_of_day_with_offset",
        ),
        # Microseconds are not part of a release date, so whatever they hold is ignored.
        pytest.param(
            "20061201134502.******+000",
            _utc_to_unix_seconds(2006, 12, 1, 13, 45, 2),
            id="unknown_microseconds",
        ),
        # WMI reports a digit the firmware did not specify as "*", which reads as zero.
        pytest.param(
            "2006120100000*.000000+000", _utc_to_unix_seconds(2006, 12, 1), id="unknown_second"
        ),
        pytest.param(
            "200612011345**.000000+000",
            _utc_to_unix_seconds(2006, 12, 1, 13, 45),
            id="unknown_seconds_field",
        ),
        # Microsoft's own example of a date without a time of day.
        pytest.param(
            "19980416******.000000+***", _utc_to_unix_seconds(1998, 4, 16), id="date_only"
        ),
        # An unspecified offset is UTC, and must not be confused with "+000" arithmetic.
        pytest.param(
            "20061201134502.000000+***",
            _utc_to_unix_seconds(2006, 12, 1, 13, 45, 2),
            id="unknown_offset",
        ),
    ],
)
def test_parse_win_bios_release_date_does_not_depend_on_the_local_timezone(
    release_date: str, expected: int
) -> None:
    section = parse_win_bios([["ReleaseDate", release_date]])

    assert section["date"] == expected


@pytest.mark.parametrize(
    "release_date",
    [
        pytest.param("20061201000000", id="without_fraction_and_offset"),
        pytest.param("20061201000000.000000", id="without_offset"),
        pytest.param("20061201000000,000000+000", id="wrong_separator"),
        pytest.param("20061201000000.000000 000", id="offset_without_sign"),
        # Rejected on width before any offset is read, so timedelta() cannot overflow.
        pytest.param("20061201000000.000000+99999999999999999999", id="too_long"),
        pytest.param("20061201000000.000000+1440", id="one_character_too_long"),
        # The fields run from most to least significant, so only trailing ones can be
        # unspecified. A "*" with a digit behind it must not be resolved into a date that
        # the firmware never reported, here the first of the month.
        pytest.param("2006**01000000.000000+000", id="unknown_month"),
        pytest.param("200612*1000000.000000+000", id="half_unknown_day"),
        pytest.param("200612********.000000+000", id="year_and_month_only"),
        pytest.param("**************.000000+000", id="everything_unspecified"),
    ],
)
def test_parse_win_bios_rejects_a_release_date_that_breaks_the_contract(release_date: str) -> None:
    with pytest.raises(ValueError):
        parse_win_bios([["ReleaseDate", release_date]])


def test_parse_win_bios_skips_an_empty_release_date() -> None:
    """Firmware that reports no date at all is normal, not a broken contract."""
    section = parse_win_bios([["Manufacturer", "Company"], ["ReleaseDate", ""]])

    assert section == {"vendor": "Company"}


def test_inventory_win_bios_without_release_date() -> None:
    section = parse_win_bios([line.split(":") for line in OUTPUT_WITHOUT_RELEASE_DATE.split("\n")])

    assert "date" not in section
    assert list(inventory_win_bios(section)) == [
        Attributes(
            path=["software", "bios"],
            inventory_attributes={
                "model": "20260522",
                "vendor": "Company",
                "version": "20260522 2.8",
            },
        )
    ]
