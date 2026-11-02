#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ec.helpers import (
    Framing,
    parse_bytes_into_lines,
    parse_bytes_into_syslog_messages,
    parse_spool_file,
)

# Syslog via TCP and the event socket take octet counting, the event pipe takes only lines, see
# parse_bytes_into_lines().
_FRAMINGS = (
    pytest.param(parse_bytes_into_syslog_messages, id="syslog via TCP or event socket"),
    pytest.param(parse_bytes_into_lines, id="event pipe"),
)


def _lines(*lines: bytes) -> bytes:
    return b"".join(line + b"\n" for line in lines)


def _octet_counted(message: bytes) -> bytes:
    return b"%d %s" % (len(message), message)


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize(
    "lines",
    (
        pytest.param([b"foo", b"bar"], id="lines"),
        pytest.param(
            [
                b"2016 May 26 15:41:47 IST XYZ Ebra: %LINEPROTO-5-UPDOWN: up",
                b"2016 May 26 15:41:48 IST XYZ Ebra: second",
            ],
            id="syslog messages without a priority starting with a year",
        ),
        pytest.param(
            [b"1 2016-06-02T12:49:05.181+02:00 host App - - text"],
            id="RFC 5424 syslog message without a priority",
        ),
        pytest.param([b"3 disks failed"], id="text starting with a number"),
        pytest.param([b"3 <b>x</b>"], id="number before a tag"),
        pytest.param([b"6 <1234>x"], id="number before too big a priority"),
    ),
)
def test_each_line_is_a_message_also_starting_with_a_number(
    framing: Framing, lines: list[bytes]
) -> None:
    assert framing(_lines(*lines)) == (lines, b"")


@pytest.mark.parametrize(
    "line",
    (
        pytest.param(b"12<14>x", id="no space"),
        pytest.param(b" 12 <14>x", id="space before it"),
        pytest.param(b"+12 <14>x", id="sign"),
        pytest.param(b"1_2 <14>x", id="underscore"),
        pytest.param(b"12\t <14>x", id="tab"),
        pytest.param(b"0 <14>x", id="zero"),
    ),
)
def test_invalid_octet_count_is_part_of_a_line(line: bytes) -> None:
    assert parse_bytes_into_syslog_messages(_lines(line)) == ([line], b"")


@pytest.mark.parametrize(
    "data, messages",
    (
        pytest.param(_octet_counted(b"<14>x"), [b"<14>x"], id="message"),
        pytest.param(
            _octet_counted(b"<14>disk \nfull"), [b"<14>disk \nfull"], id="newline within it"
        ),
        pytest.param(
            _octet_counted(b"<14>x") + _octet_counted(b"<14>y"),
            [b"<14>x", b"<14>y"],
            id="next message right after it",
        ),
        pytest.param(_octet_counted(b"<14>x") + b"y\n", [b"<14>x", b"y"], id="line right after it"),
    ),
)
def test_octet_counted_syslog_message_ends_after_its_count(
    data: bytes, messages: list[bytes]
) -> None:
    assert parse_bytes_into_syslog_messages(data) == (messages, b"")


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize(
    "data, messages",
    (
        pytest.param(b"\n", [], id="empty line"),
        pytest.param(b"foo\n\nbar\n", [b"foo", b"bar"], id="empty line between lines"),
    ),
)
def test_empty_line_is_no_message(framing: Framing, data: bytes, messages: list[bytes]) -> None:
    assert framing(data) == (messages, b"")


def test_empty_line_of_a_spool_file_is_no_message() -> None:
    assert list(parse_spool_file(b"\nfoo\n\nbar\n")) == [b"foo", b"bar"]


@pytest.mark.parametrize(
    "data",
    (
        pytest.param(b"foo\nbar", id="no newline after the last line"),
        pytest.param(b"foo\rbar\r", id="carriage returns"),
        pytest.param(b"foo\r\nbar\r\n", id="carriage returns and newlines"),
    ),
)
def test_each_line_of_a_spool_file_is_a_message_whatever_ends_it(data: bytes) -> None:
    assert list(parse_spool_file(data)) == [b"foo", b"bar"]


def test_newline_after_an_octet_counted_syslog_message_is_no_message() -> None:
    # A common mistake of senders: The count doesn't include the newline they add.
    data = b"10 <13>hello!\n10 <13>world!\n"

    assert parse_bytes_into_syslog_messages(data) == ([b"<13>hello!", b"<13>world!"], b"")


@pytest.mark.parametrize(
    "data",
    (
        pytest.param(b"foo", id="line"),
        pytest.param(b"15 ", id="number"),
        pytest.param(b"15 <1", id="priority"),
        pytest.param(_octet_counted(b"<14>disk \nfull")[:-1], id="octet-counted syslog message"),
    ),
)
def test_incomplete_syslog_message_waits_for_its_rest(data: bytes) -> None:
    assert parse_bytes_into_syslog_messages(b"done\n" + data) == ([b"done"], data)
