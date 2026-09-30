#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum

import pytest

from cmk.agent_based.v3_unstable import parse_as, ParseFailure


class _Status(enum.Enum):
    OK = "1"
    WARNING = "2"


def _failure(value: object) -> ParseFailure:
    assert isinstance(value, ParseFailure)
    return value


def test_a_convertible_value_is_converted_normally() -> None:
    assert parse_as(float, "23.5", field="temperature") == 23.5


def test_a_known_enum_value_is_converted_normally() -> None:
    assert parse_as(_Status, "2", field="status") is _Status.WARNING


def test_an_unconvertible_value_becomes_a_failure_for_its_field() -> None:
    assert _failure(parse_as(float, "N/A", field="temperature")).field == "temperature"


def test_a_failure_keeps_the_exception_that_caused_it() -> None:
    assert isinstance(_failure(parse_as(_Status, "9", field="status")).exception, ValueError)


def test_a_failure_names_its_field_and_its_cause() -> None:
    assert str(_failure(parse_as(_Status, "9", field="status"))) == (
        "Could not parse 'status': '9' is not a valid _Status"
    )


def test_a_whole_row_can_be_parsed_at_once() -> None:
    failure = _failure(parse_as(lambda row: (_Status(row[0]), float(row[1])), ["1"], field="row"))

    assert isinstance(failure.exception, IndexError)


def test_an_unexpected_exception_is_not_turned_into_a_failure() -> None:
    def converter(_value: str) -> int:
        raise RuntimeError("bug in the converter")

    with pytest.raises(RuntimeError):
        parse_as(converter, "1", field="status")
