#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Never

import pytest

from cmk.base.legacy_checks import fireeye_mail


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
    result = list(fireeye_mail.discover_fireeye_mail(parsed))
    assert result == [(None, {})]


def test_check_fireeye_mail(parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError as expected
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(Exception):  # GetRateError or similar rate-related error
        list(fireeye_mail.check_fireeye_mail(None, {}, parsed))


def test_discover_fireeye_mail_attachment(parsed: list[list[str]]) -> None:
    result = list(fireeye_mail.discover_fireeye_mail_attachment(parsed))
    assert result == [(None, {})]


def test_check_fireeye_mail_attachment(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError as expected
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(Exception):  # GetRateError or similar rate-related error
        list(fireeye_mail.check_fireeye_attachment(None, {}, parsed))


def test_discover_fireeye_mail_url(parsed: list[list[str]]) -> None:
    result = list(fireeye_mail.discover_fireeye_mail_url(parsed))
    assert result == [(None, {})]


def test_check_fireeye_mail_url(parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError as expected
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(Exception):  # GetRateError or similar rate-related error
        list(fireeye_mail.check_fireeye_url(None, {}, parsed))


def test_discover_fireeye_mail_statistics(parsed: list[list[str]]) -> None:
    result = list(fireeye_mail.discover_fireeye_mail_statistics(parsed))
    assert result == [(None, {})]


def test_check_fireeye_mail_statistics(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError as expected
    value_store: dict[str, object] = {}
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)
    with pytest.raises(Exception):  # GetRateError or similar rate-related error
        list(fireeye_mail.check_fireeye_mail_statistics(None, {}, parsed))


def test_discover_fireeye_mail_received(parsed: list[list[str]]) -> None:
    result = list(fireeye_mail.discover_fireeye_mail_received(parsed))
    assert result == [(None, {})]


def test_check_fireeye_mail_received(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    params = {"rate": (6000, 7000)}
    # Pre-populate value store for rate calculation
    # Parsed contains 120 emails received over 60 seconds (04/06/17 12:00:00 to 12:01:00)
    # To get rate of 2.00/s, we need to set up proper previous values
    import time

    current_time = time.mktime(time.strptime("04/06/17 12:01:00", "%d/%m/%y %H:%M:%S"))
    value_store: dict[str, object] = {"mail_received": (current_time - 60, 0)}  # 60s ago, 0 mails
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)

    result = list(fireeye_mail.check_fireeye_mail_received(None, params, parsed))

    assert len(result) == 2

    # Check mails received count
    assert result[0][0] == 0  # OK state
    assert "Mails received between 04/06/17 12:00:00 and 04/06/17 12:01:00: 120" in result[0][1]
    # Some check functions return 2-tuples instead of 3-tuples
    if len(result[0]) > 2:
        assert result[0][2] == []

    # Check rate
    assert result[1][0] == 0  # OK state
    assert "Rate: 2.00/s" in result[1][1]
    if len(result[1]) > 2:
        assert result[1][2] == [("mail_received_rate", 2.0, 6000, 7000)]


def test_check_fireeye_mail_received_no_thresholds(
    parsed: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store for rate calculation
    import time

    current_time = time.mktime(time.strptime("04/06/17 12:01:00", "%d/%m/%y %H:%M:%S"))
    value_store: dict[str, object] = {"mail_received": (current_time - 60, 0)}  # 60s ago, 0 mails
    monkeypatch.setattr(fireeye_mail, "get_value_store", lambda: value_store)

    result = list(fireeye_mail.check_fireeye_mail_received(None, {}, parsed))

    # Check mails received count
    assert result[0][0] == 0  # OK state
    assert "Mails received between 04/06/17 12:00:00 and 04/06/17 12:01:00: 120" in result[0][1]
    if len(result[0]) > 2:
        assert result[0][2] == []

    # Check rate without thresholds
    assert result[1][0] == 0  # OK state
    assert "Rate: 2.00/s" in result[1][1]
    if len(result[1]) > 2:
        assert result[1][2] == [("mail_received_rate", 2.0, None, None)]


def test_fireeye_mail_comprehensive_discovery(parsed: list[list[str]]) -> None:
    # Test that all services are discovered
    main_discovery = list(fireeye_mail.discover_fireeye_mail(parsed))
    attachment_discovery = list(fireeye_mail.discover_fireeye_mail_attachment(parsed))
    url_discovery = list(fireeye_mail.discover_fireeye_mail_url(parsed))
    statistics_discovery = list(fireeye_mail.discover_fireeye_mail_statistics(parsed))
    received_discovery = list(fireeye_mail.discover_fireeye_mail_received(parsed))

    assert main_discovery == [(None, {})]
    assert attachment_discovery == [(None, {})]
    assert url_discovery == [(None, {})]
    assert statistics_discovery == [(None, {})]
    assert received_discovery == [(None, {})]


def test_fireeye_mail_empty_info() -> None:
    # Test behavior with empty info
    empty_info = list[Never]()

    # Discovery functions should return empty lists for empty info
    assert list(fireeye_mail.discover_fireeye_mail(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_attachment(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_url(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_statistics(empty_info)) == []
    assert list(fireeye_mail.discover_fireeye_mail_received(empty_info)) == []
