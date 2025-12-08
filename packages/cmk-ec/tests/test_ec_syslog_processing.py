#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ec.helpers import (
    Failure,
    parse_bytes_into_syslog_messages,
    parse_syslog_message,
    ParseResult,
)


@pytest.mark.parametrize(
    "message, result",
    (
        pytest.param(b"", (Failure, b"")),
        pytest.param(b"2", (Failure, b"2")),
        pytest.param(b"42 foo\nbar", (Failure, b"42 foo\nbar")),
    ),
)
def test_parse_syslog_message_incomplete_data(message: bytes, result: ParseResult[bytes]) -> None:
    assert parse_syslog_message(memoryview(message)) == result


@pytest.mark.parametrize(
    "message, result",
    (
        pytest.param(b"12TheQuickBrownFox", (Failure, b"12TheQuickBrownFox")),
        pytest.param(b" 12 TheQuickBrownFox", (Failure, b" 12 TheQuickBrownFox")),
        pytest.param(b"+12 TheQuickBrownFox", (Failure, b"+12 TheQuickBrownFox")),
        pytest.param(b"1_2 TheQuickBrownFox", (Failure, b"1_2 TheQuickBrownFox")),
        pytest.param(b"12\t TheQuickBrownFox", (Failure, b"12\t TheQuickBrownFox")),
    ),
)
def test_parse_syslog_message_incorrect_msg_len_without_newline(
    message: bytes, result: ParseResult[bytes]
) -> None:
    assert parse_syslog_message(memoryview(message)) == result


@pytest.mark.parametrize(
    "message, result",
    (
        pytest.param(b"12TheQuickBrown\nFox", (b"12TheQuickBrown", b"Fox")),
        pytest.param(b" 12 TheQuickBrown\nFox", (b" 12 TheQuickBrown", b"Fox")),
        pytest.param(b"+12 TheQuickBrown\nFox", (b"+12 TheQuickBrown", b"Fox")),
        pytest.param(b"1_2 TheQuickBrown\nFox", (b"1_2 TheQuickBrown", b"Fox")),
        pytest.param(b"12\t TheQuickBrown\nFox", (b"12\t TheQuickBrown", b"Fox")),
    ),
)
def test_parse_syslog_message_incorrect_msg_len_with_newline(
    message: bytes, result: ParseResult[bytes]
) -> None:
    assert parse_syslog_message(memoryview(message)) == result


@pytest.mark.parametrize(
    "message, result",
    (
        pytest.param(b"1 x", (b"x", b"")),
        pytest.param(b"1 xy", (b"x", b"y")),
        pytest.param(b"1 xy\n", (b"x", b"y\n")),
        pytest.param(b"12 TheQuickBrownFox", (b"TheQuickBrow", b"nFox")),
        pytest.param(
            b"45 May 26 13:45:01 Klapprechner CRON[8046]: octet message\n",
            (b"May 26 13:45:01 Klapprechner CRON[8046]: octe", b"t message\n"),
        ),
    ),
)
def test_parse_syslog_message_octet_counting(message: bytes, result: ParseResult[bytes]) -> None:
    assert parse_syslog_message(memoryview(message)) == result


@pytest.mark.parametrize(
    "message, result",
    (
        pytest.param(b"\n", (b"", b"")),
        pytest.param(b"\nx", (b"", b"x")),
        pytest.param(b"foo\nis\nnot\nbar", (b"foo", b"is\nnot\nbar")),
    ),
)
def test_parse_syslog_message_transparent_framing(
    message: bytes, result: ParseResult[bytes]
) -> None:
    assert parse_syslog_message(memoryview(message)) == result


@pytest.mark.parametrize(
    "data, unprocessed",
    (
        pytest.param(
            b"May 26 13:45:01 Klapprechner CRON[8046]:  message\n",
            b"",
            id="transparent framing",
        ),
        pytest.param(
            b"45 May 26 13:45:01 Klapprechner CRON[8046]: octet message\n",
            b"",
            id="octet counting longer than needed, the second half becomes a next message",
        ),
        pytest.param(
            b"58 May 26 13:45:01 Klapprechner CRON[8046]: octet message\n",
            b"58 May 26 13:45:01 Klapprechner CRON[8046]: octet message\n",
            id="octet counting incomplete",
        ),
    ),
)
def test_return_unprocessed(data: bytes, unprocessed: bytes) -> None:
    """
    Unprocessed bytes returned correctly
    """
    assert parse_bytes_into_syslog_messages(data)[1] == unprocessed


def test_process_spool_file() -> None:
    """
    Spool files correctly handle each line as a message
    """
    file_to_process = b""""May 26 13:45:01 Klapprechner CRON[8046]:  message\n55 May 26 13:45:01 Klapprechner CRON[8046]: octet message\n"""
    for data in file_to_process.splitlines(keepends=True):
        assert parse_bytes_into_syslog_messages(data)[1] == b""
