#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import time

import pytest

from cmk.agent_based.v2 import GetRateError, Metric, Result, Service, State, StringTable
from cmk.plugins.fireeye.agent_based import fireeye_mail


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    return [
        [
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "04/06/17 12:00:00",
            "04/06/17 12:01:00",
            "120",
        ]
    ]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[str]]) -> list[list[str]]:
    return fireeye_mail.parse_fireeye_mail(string_table)


def test_parse_fireeye_mail(string_table: list[list[str]]) -> None:
    result = fireeye_mail.parse_fireeye_mail(string_table)
    assert result == string_table


def test_discover_fireeye_mail(parsed: list[list[str]]) -> None:
    assert list(fireeye_mail.discover_fireeye_mail(parsed)) == [Service()]


def test_check_fireeye_mail(parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    # get_rate raises GetRateError on the first call with an empty value store
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(GetRateError):
        list(fireeye_mail.check_fireeye_mail({}, parsed))


def test_discover_fireeye_mail_attachment(parsed: list[list[str]]) -> None:
    assert list(fireeye_mail.discover_fireeye_mail_attachment(parsed)) == [Service()]


def test_check_fireeye_mail_attachment(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # get_rate raises GetRateError on the first call with an empty value store
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(GetRateError):
        list(fireeye_mail.check_fireeye_attachment({}, parsed))


def test_discover_fireeye_mail_url(parsed: list[list[str]]) -> None:
    assert list(fireeye_mail.discover_fireeye_mail_url(parsed)) == [Service()]


def test_check_fireeye_mail_url(parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    # get_rate raises GetRateError on the first call with an empty value store
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(GetRateError):
        list(fireeye_mail.check_fireeye_url({}, parsed))


def test_discover_fireeye_mail_statistics(parsed: list[list[str]]) -> None:
    assert list(fireeye_mail.discover_fireeye_mail_statistics(parsed)) == [Service()]


def test_check_fireeye_mail_statistics(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # get_rate raises GetRateError on the first call with an empty value store
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(GetRateError):
        list(fireeye_mail.check_fireeye_mail_statistics({}, parsed))


def test_discover_fireeye_mail_received(parsed: list[list[str]]) -> None:
    assert list(fireeye_mail.discover_fireeye_mail_received(parsed)) == [Service()]


def test_check_fireeye_mail_received(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    params = {"rate": (6000.0, 7000.0)}
    # Pre-populate value store for rate calculation
    # Parsed contains 120 emails received over 60 seconds (04/06/17 12:00:00 to 12:01:00)
    # To get rate of 2.00/s, we need to set up proper previous values
    current_time = time.mktime(time.strptime("04/06/17 12:01:00", "%d/%m/%y %H:%M:%S"))
    value_store: dict[str, object] = {"mail_received": (current_time - 60, 0)}  # 60s ago, 0 mails
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)

    assert list(fireeye_mail.check_fireeye_mail_received(params, parsed)) == [
        Result(
            state=State.OK,
            summary="Mails received between 04/06/17 12:00:00 and 04/06/17 12:01:00: 120",
        ),
        Result(state=State.OK, summary="Rate: 2.00/s"),
        Metric("mail_received_rate", 2.0, levels=(6000.0, 7000.0)),
    ]


def test_check_fireeye_mail_received_no_thresholds(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store for rate calculation
    current_time = time.mktime(time.strptime("04/06/17 12:01:00", "%d/%m/%y %H:%M:%S"))
    value_store: dict[str, object] = {"mail_received": (current_time - 60, 0)}  # 60s ago, 0 mails
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)

    assert list(fireeye_mail.check_fireeye_mail_received({}, parsed)) == [
        Result(
            state=State.OK,
            summary="Mails received between 04/06/17 12:00:00 and 04/06/17 12:01:00: 120",
        ),
        Result(state=State.OK, summary="Rate: 2.00/s"),
        Metric("mail_received_rate", 2.0),
    ]


def test_fireeye_mail_comprehensive_discovery(parsed: list[list[str]]) -> None:
    # Test that all services are discovered
    assert list(fireeye_mail.discover_fireeye_mail(parsed)) == [Service()]
    assert list(fireeye_mail.discover_fireeye_mail_attachment(parsed)) == [Service()]
    assert list(fireeye_mail.discover_fireeye_mail_url(parsed)) == [Service()]
    assert list(fireeye_mail.discover_fireeye_mail_statistics(parsed)) == [Service()]
    assert list(fireeye_mail.discover_fireeye_mail_received(parsed)) == [Service()]


def test_fireeye_mail_empty_info() -> None:
    # Test behavior with empty info
    empty_info: StringTable = []

    # Discovery functions should return empty lists for empty info
    assert list(fireeye_mail.discover_fireeye_mail(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_attachment(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_url(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_statistics(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_received(empty_info)) == []
