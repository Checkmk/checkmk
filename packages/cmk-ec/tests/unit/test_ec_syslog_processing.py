#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

import pytest

from cmk.ec.helpers import (
    Discarding,
    EVENT_PIPE,
    EVENT_SOCKET,
    Framing,
    Incomplete,
    MAX_EVENT_SOCKET_MESSAGE_SIZE,
    MAX_MESSAGE_SIZE,
    next_messages,
    parse_spool_file,
    Skipping,
    SYSLOG_VIA_TCP,
    Truncated,
    Unprocessed,
)

# Syslog via TCP and the event socket take octet counting, the event pipe takes only lines, see
# EVENT_PIPE.
_FRAMINGS = (
    pytest.param(SYSLOG_VIA_TCP, id="syslog via TCP"),
    pytest.param(EVENT_PIPE, id="event pipe"),
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
    assert framing(_lines(*lines)) == (lines, Incomplete())


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
    assert SYSLOG_VIA_TCP(_lines(line)) == ([line], Incomplete())


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
    assert SYSLOG_VIA_TCP(data) == (messages, Incomplete())


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize(
    "data, messages",
    (
        pytest.param(b"\n", [], id="empty line"),
        pytest.param(b"foo\n\nbar\n", [b"foo", b"bar"], id="empty line between lines"),
    ),
)
def test_empty_line_is_no_message(framing: Framing, data: bytes, messages: list[bytes]) -> None:
    assert framing(data) == (messages, Incomplete())


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

    assert SYSLOG_VIA_TCP(data) == ([b"<13>hello!", b"<13>world!"], Incomplete())


_DISK_FULL = b"<14>disk \nfull"


@pytest.mark.parametrize(
    "data, received_first, message",
    (
        pytest.param(b"foo\n", len(b"foo"), b"foo", id="line"),
        pytest.param(_octet_counted(_DISK_FULL), len(b"14 "), _DISK_FULL, id="number"),
        pytest.param(_octet_counted(_DISK_FULL), len(b"14 <1"), _DISK_FULL, id="priority"),
        pytest.param(
            _octet_counted(_DISK_FULL),
            len(_octet_counted(_DISK_FULL)) - 1,
            _DISK_FULL,
            id="octet-counted syslog message",
        ),
    ),
)
def test_incomplete_syslog_message_waits_for_its_rest(
    data: bytes, received_first: int, message: bytes
) -> None:
    first, rest = b"done\n" + data[:received_first], data[received_first:]

    assert _messages_from(SYSLOG_VIA_TCP, first, rest) == [b"done", message]


def test_number_with_9_digits_is_an_octet_count() -> None:
    data = b"999999999 <14>x\n"

    assert SYSLOG_VIA_TCP(data)[0] == []


@pytest.mark.parametrize(
    "number",
    (
        pytest.param(b"1234567890", id="10 digits"),
        pytest.param(b"1" * 4301, id="more digits than int() takes"),
    ),
)
def test_number_with_more_than_9_digits_is_part_of_a_line(number: bytes) -> None:
    line = number + b" <14>x"

    assert SYSLOG_VIA_TCP(line + b"\n") == ([line], Incomplete())


def _in_parts(data: bytes) -> list[bytes]:
    """The data in small parts, like the event server reads it from the event pipe"""
    return [data[i : i + 4096] for i in range(0, len(data), 4096)]


def _messages_from(framing: Framing, *data: bytes) -> list[bytes]:
    """The messages from data received one after the other"""
    messages: list[bytes] = []
    unprocessed: Unprocessed = Incomplete()
    for each in data:
        new_messages, unprocessed = next_messages(framing, unprocessed, each)
        messages += new_messages
    return messages


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize(
    "parts, messages",
    (
        pytest.param((b"fo", b"o\nb", b"ar\n"), [b"foo", b"bar"], id="short lines"),
        pytest.param(
            (b"x" * 100, b"y" * 100, b"z\nnext\n"),
            [b"x" * 100 + b"y" * 100 + b"z", b"next"],
            id="line too long for an octet count",
        ),
    ),
)
def test_message_received_in_parts_is_put_together(
    framing: Framing, parts: tuple[bytes, ...], messages: list[bytes]
) -> None:
    assert _messages_from(framing, *parts) == messages


def test_octet_counted_message_as_long_as_the_max_message_size_is_taken_whole() -> None:
    message = b"<14>" + b"x" * (MAX_MESSAGE_SIZE - len(b"<14>"))

    assert _messages_from(SYSLOG_VIA_TCP, *_in_parts(_octet_counted(message))) == [message]


def test_overlong_octet_counted_message_is_truncated_and_its_rest_skipped_by_its_count() -> None:
    # So long that whole parts of its rest arrive after its start was taken
    message = b"<14>" + b"x" * (2 * MAX_MESSAGE_SIZE)
    data = _octet_counted(message) + _octet_counted(b"<14>next")

    assert _messages_from(SYSLOG_VIA_TCP, *_in_parts(data)) == [
        message[:MAX_MESSAGE_SIZE],
        b"<14>next",
    ]


def test_nothing_of_an_overlong_octet_counted_message_is_kept_for_more_data() -> None:
    data = _octet_counted(b"<14>" + b"x" * MAX_MESSAGE_SIZE)[: -len(b"<14>")]

    assert next_messages(SYSLOG_VIA_TCP, Incomplete(), data)[1] == Skipping(len(b"<14>"))


_OVERLONG_LINE_IN_PARTS = (
    pytest.param(
        (b"x" * (MAX_MESSAGE_SIZE + 1), b"x" * 10, b"x\nnext\n"), id="overlong in its first part"
    ),
    pytest.param(
        (b"x" * 100, b"x" * MAX_MESSAGE_SIZE, b"x\nnext\n"), id="overlong in a later part"
    ),
    pytest.param(
        (b"x" * 100, b"x" * MAX_MESSAGE_SIZE + b"\nnext\n"), id="overlong in the part ending it"
    ),
)


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize("parts", _OVERLONG_LINE_IN_PARTS)
def test_overlong_line_is_truncated_and_its_rest_discarded_up_to_the_next_newline(
    framing: Framing, parts: tuple[bytes, ...]
) -> None:
    assert _messages_from(framing, *parts) == [b"x" * MAX_MESSAGE_SIZE, b"next"]


@pytest.mark.parametrize("framing", _FRAMINGS)
def test_complete_line_longer_than_the_max_message_size_is_truncated(framing: Framing) -> None:
    data = b"x" * (MAX_MESSAGE_SIZE + 1) + b"\nnext\n"

    assert _messages_from(framing, data) == [b"x" * MAX_MESSAGE_SIZE, b"next"]


@pytest.mark.parametrize("framing", _FRAMINGS)
def test_nothing_of_an_overlong_line_is_kept_for_more_data(framing: Framing) -> None:
    data = b"x" * (MAX_MESSAGE_SIZE + 1)

    assert next_messages(framing, Incomplete(), data)[1] == Discarding()


def test_overlong_line_of_a_spool_file_is_truncated() -> None:
    data = b"x" * (MAX_MESSAGE_SIZE + 1) + b"\nnext\n"

    assert list(parse_spool_file(data)) == [b"x" * MAX_MESSAGE_SIZE, b"next"]


def _marked_as_truncated(messages: Iterable[bytes]) -> list[bool]:
    return [isinstance(message, Truncated) for message in messages]


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize(
    "parts",
    (
        *_OVERLONG_LINE_IN_PARTS,
        pytest.param((b"x" * (MAX_MESSAGE_SIZE + 1) + b"\nnext\n",), id="overlong in one part"),
    ),
)
def test_truncated_line_is_marked_as_truncated(framing: Framing, parts: tuple[bytes, ...]) -> None:
    assert _marked_as_truncated(_messages_from(framing, *parts)) == [True, False]


@pytest.mark.parametrize(
    "length",
    (
        pytest.param(MAX_MESSAGE_SIZE + 1, id="its end in the part making it overlong"),
        pytest.param(2 * MAX_MESSAGE_SIZE, id="its end in a later part"),
    ),
)
def test_truncated_octet_counted_message_is_marked_as_truncated(length: int) -> None:
    data = _octet_counted(b"<14>" + b"x" * (length - len(b"<14>"))) + _octet_counted(b"<14>next")

    messages = _messages_from(SYSLOG_VIA_TCP, *_in_parts(data))

    assert _marked_as_truncated(messages) == [True, False]


def test_truncated_line_of_a_spool_file_is_marked_as_truncated() -> None:
    data = b"x" * (MAX_MESSAGE_SIZE + 1) + b"\nnext\n"

    assert _marked_as_truncated(parse_spool_file(data)) == [True, False]


@pytest.mark.parametrize("framing", _FRAMINGS)
@pytest.mark.parametrize(
    "parts",
    (
        pytest.param((b"x" * MAX_MESSAGE_SIZE + b"\nnext\n",), id="in one part"),
        pytest.param((b"x" * 100, b"x" * (MAX_MESSAGE_SIZE - 100) + b"\nnext\n"), id="in parts"),
    ),
)
def test_line_as_long_as_the_max_message_size_is_not_marked_as_truncated(
    framing: Framing, parts: tuple[bytes, ...]
) -> None:
    assert _marked_as_truncated(_messages_from(framing, *parts)) == [False, False]


@pytest.mark.parametrize(
    "data, message",
    (
        pytest.param(
            _octet_counted(b"<14>" + b"x" * MAX_MESSAGE_SIZE),
            b"<14>" + b"x" * MAX_MESSAGE_SIZE,
            id="octet-counted syslog message",
        ),
        pytest.param(
            b"x" * (MAX_MESSAGE_SIZE + 1) + b"\n", b"x" * (MAX_MESSAGE_SIZE + 1), id="line"
        ),
    ),
)
def test_message_from_the_event_socket_longer_than_one_via_tcp_is_taken_whole(
    data: bytes, message: bytes
) -> None:
    # Like the syslog exporter of the OpenTelemetry collector sends a long log record
    assert _messages_from(EVENT_SOCKET, *_in_parts(data)) == [message]


def test_overlong_octet_counted_message_from_the_event_socket_is_truncated_to_its_max_size() -> (
    None
):
    message = b"<14>" + b"x" * MAX_EVENT_SOCKET_MESSAGE_SIZE
    data = _octet_counted(message) + _octet_counted(b"<14>next")

    assert _messages_from(EVENT_SOCKET, *_in_parts(data)) == [
        message[:MAX_EVENT_SOCKET_MESSAGE_SIZE],
        b"<14>next",
    ]
