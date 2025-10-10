#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest
from dateutil.parser import isoparse

from cmk.gui.form_specs.generators.absolute_date import AbsoluteTimestamp, DateTimeFormat
from cmk.rulesets.v1 import Title


def test_converts_unix_timestamp_to_date_string():
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).from_disk(
        1700000000
    )
    assert result == ["2023-11-14"]


def test_converts_unix_timestamp_to_datetime_string():
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATETIME).from_disk(
        1700000000
    )
    assert result == ["2023-11-14", "23:13:20"]


def test_converts_time_list_to_time_string():
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.TIME).from_disk(
        [12, 30]
    )
    assert result == ["12:30:0"]


def test_converts_date_string_to_unix_timestamp():
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).to_disk(
        "2023-11-14"
    )
    assert result == int(isoparse("2023-11-14").timestamp())


def test_converts_time_string_to_time_list():
    result = AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.TIME).to_disk("12:30")
    assert result == [12, 30]


def test_raises_error_for_invalid_format_in_from_disk():
    with pytest.raises(TypeError):
        AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).from_disk("invalid")


def test_raises_error_for_invalid_format_in_to_disk():
    with pytest.raises(TypeError):
        AbsoluteTimestamp(title=Title("Test"), use_format=DateTimeFormat.DATE).to_disk(12345)
