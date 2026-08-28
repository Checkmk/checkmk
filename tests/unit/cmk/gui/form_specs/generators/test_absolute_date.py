#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Iterator
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.gui.form_specs.generators.absolute_date import AbsoluteTimestamp, DateTimeFormat
from cmk.rulesets.v1 import Title

UNIX_TIMESTAMP_2023_11_14_22_13_20_UTC = 1700000000


@pytest.fixture
def fixed_utc_timezone() -> Iterator[None]:
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))):
        yield


@pytest.mark.usefixtures("fixed_utc_timezone")
def test_converts_unix_timestamp_to_date_string() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).from_disk(
        UNIX_TIMESTAMP_2023_11_14_22_13_20_UTC
    )
    assert result == ["2023-11-14"]


@pytest.mark.usefixtures("fixed_utc_timezone")
def test_converts_unix_timestamp_to_datetime_string() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATETIME).from_disk(
        UNIX_TIMESTAMP_2023_11_14_22_13_20_UTC
    )
    assert result == ["2023-11-14", "22:13"]


def test_converts_time_list_to_time_string() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.TIME).from_disk(
        [12, 30]
    )
    assert result == ["12:30"]


def test_zero_pads_single_digit_hours_and_minutes() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.TIME).from_disk(
        [9, 5]
    )
    assert result == ["09:05"]


@pytest.mark.usefixtures("fixed_utc_timezone")
def test_converts_date_tuple_to_unix_timestamp() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).to_disk(
        ("2023-11-14",)
    )
    assert result == 1699920000


@pytest.mark.usefixtures("fixed_utc_timezone")
def test_converts_datetime_tuple_to_unix_timestamp() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATETIME).to_disk(
        ("2023-11-14", "22:13")
    )
    assert result == UNIX_TIMESTAMP_2023_11_14_22_13_20_UTC - 20


def test_converts_time_tuple_to_time_list() -> None:
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.TIME).to_disk(
        ("12:30",)
    )
    assert result == [12, 30]


def test_raises_error_for_invalid_format_in_from_disk() -> None:
    with pytest.raises(TypeError):
        AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).from_disk("invalid")


def test_raises_error_for_invalid_format_in_to_disk() -> None:
    with pytest.raises(TypeError, match="<class 'int'>"):
        AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).to_disk(12345)
