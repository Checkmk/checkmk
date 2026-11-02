#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import threading
from collections.abc import Callable, Iterable, Iterator
from logging import Logger
from types import TracebackType
from typing import Literal

# Our tokens are bytes, so we use a memoryview as a stream of bytes.
type Tokens = memoryview

# No error reporting, we just state that we failed.
Failure = None
type FailureType = None

# The result of the parser is the value it parsed + the still unparsed tokens.
type ParseResult[T] = tuple[T | FailureType, Tokens]

# It would be nice if we could reuse this for defs, but Python is too restricted for this.
type Parser[T] = Callable[[Tokens], ParseResult[T]]


def parse_bytes(length: int, tokens: Tokens) -> ParseResult[bytes]:
    msg = tokens[:length]
    if len(msg) != length:
        return Failure, tokens
    return bytes(msg), tokens[length:]


def parse_one_of(expected: bytes, tokens: Tokens) -> ParseResult[bytes]:
    byte, rest = parse_bytes(1, tokens)
    if byte is Failure or byte not in expected:
        return Failure, tokens
    return byte, rest


# Shorter: partial(parse_one_of, b"0123456789")
def parse_digit(tokens: Tokens) -> ParseResult[bytes]:
    return parse_one_of(b"0123456789", tokens)


def zero_or_more[T](parser: Parser[T], tokens: Tokens) -> ParseResult[list[T]]:
    result: list[T] = []
    while True:
        value, tokens = parser(tokens)
        if value is Failure:
            return result, tokens
        result.append(value)


def parse_msg_len(tokens: Tokens) -> ParseResult[int]:
    digit, rest1 = parse_one_of(b"123456789", tokens)
    if digit is Failure:
        return Failure, tokens
    digits, rest2 = zero_or_more(parse_digit, rest1)
    if digits is Failure:
        return Failure, tokens
    spc, rest3 = parse_one_of(b" ", rest2)
    if spc is Failure:
        return Failure, tokens
    return int(b"".join([digit] + digits)), rest3


def parse_non_transparent_frame(tokens: Tokens) -> ParseResult[bytes]:
    for i, b in enumerate(tokens):
        if b == ord(b"\n"):
            return bytes(tokens[:i]), tokens[i + 1 :]
    return Failure, tokens


def parse_pri(tokens: Tokens) -> ParseResult[bytes]:
    """PRI = "<" PRIVAL ">", PRIVAL = 1*3DIGIT, see RFC 5424"""
    opening, rest1 = parse_one_of(b"<", tokens)
    if opening is Failure:
        return Failure, tokens
    digits, rest2 = zero_or_more(parse_digit, rest1)
    if digits is Failure or not 1 <= len(digits) <= 3:
        return Failure, tokens
    closing, rest3 = parse_one_of(b">", rest2)
    if closing is Failure:
        return Failure, tokens
    return b"".join([opening, *digits, closing]), rest3


def parse_syslog_msg_len(tokens: Tokens) -> ParseResult[int]:
    """
    Like parse_msg_len(), but only for syslog messages, i.e. if a syslog priority like "<14>"
    follows: Only syslog messages come with octet counting, e.g. from rsyslog or from the syslog
    exporter of the OpenTelemetry collector to keep the newlines in log messages, and they start
    with a priority. So a message like "2 disks failed" is a line, and so is a syslog message
    without a priority like "2016 May 26 15:41:47 IST host app: text".
    """
    msg_len, rest = parse_msg_len(tokens)
    if msg_len is Failure or parse_pri(rest)[0] is Failure:
        return Failure, tokens
    return msg_len, rest


def parse_message(msg_len_parser: Parser[int], tokens: Tokens) -> ParseResult[bytes]:
    """
    A message with octet counting if the given parser takes its start for the length of the
    message, otherwise a line
    """
    msg_len, rest1 = msg_len_parser(tokens)
    if msg_len is Failure:
        return parse_non_transparent_frame(tokens)
    msg, rest2 = parse_bytes(msg_len, rest1)
    if msg is Failure:
        return Failure, tokens
    return msg, rest2


def _parse_bytes_into_messages(
    msg_len_parser: Parser[int], data: bytes
) -> tuple[Iterable[bytes], bytes]:
    """
    Drops empty messages like rsyslog, e.g. from a newline which a sender adds after an
    octet-counted message.
    """
    messages: list[bytes] = []
    rest = memoryview(b"")
    tokens = memoryview(data)
    while tokens:
        complete, rest = parse_message(msg_len_parser, tokens)
        if complete is Failure:
            break
        if complete:
            messages.append(complete)
        tokens = rest
    return messages, bytes(rest)


# Splits a bunch of bytes into messages and an incomplete rest.
type Framing = Callable[[bytes], tuple[Iterable[bytes], bytes]]


def parse_bytes_into_syslog_messages(data: bytes) -> tuple[Iterable[bytes], bytes]:
    """
    Parse a bunch of bytes received via syslog over TCP or via the event socket into separate
    messages and an unparsed rest.

    This method handles Octet counting (if a message starts with a number, a space and a syslog
    priority, see parse_syslog_msg_len()) and Non-Transparent framing (if '\n' is used as a
    separator).
    See the RFC doc: https://www.rfc-editor.org/rfc/rfc6587#section-3.4:

    Octet counting:
        TCP-DATA = *SYSLOG-FRAME
        SYSLOG-FRAME = MSG-LEN SP SYSLOG-MSG   ; Octet-counting method
        MSG-LEN = NONZERO-DIGIT *DIGIT
        NONZERO-DIGIT = %d49-57

    Returns the remaining unprocessed bytes.
    """
    return _parse_bytes_into_messages(parse_syslog_msg_len, data)


def _parse_no_msg_len(tokens: Tokens) -> ParseResult[int]:
    """No octet counting at all, so each message is a line"""
    return Failure, tokens


def parse_bytes_into_lines(data: bytes) -> tuple[Iterable[bytes], bytes]:
    """
    Parse a bunch of bytes received via the event pipe into lines and an unparsed rest.

    Unlike the event socket, the event pipe takes no octet counting at all, not even for syslog
    messages: All local programs write into the same pipe, and anybody may (its mode is 0662), so
    a wrong octet count, by mistake or on purpose, would hold back or swallow the messages of all
    programs after it, while on the event socket, it only affects the connection of its sender.
    And as writes to a pipe are atomic only up to PIPE_BUF, i.e. 4096 bytes, longer octet-counted
    messages of concurrent writers could get mixed up anyway. No sender needs it there: mkevent,
    and with it the notification plug-in, as well as the CREATE command of the status socket write
    a line each, and the OpenTelemetry collector sends its octet-counted syslog messages to the
    event socket.
    """
    return _parse_bytes_into_messages(_parse_no_msg_len, data)


def parse_spool_file(data: bytes) -> Iterator[bytes]:
    """
    Parse the data of a spool file into messages, a line each, without empty ones like the other
    framings. Unlike the event pipe, it also ends a line at a carriage return, and it takes the last
    line without a newline, too.

    It splits the lines right away, so a lack of memory shows here, but drops the empty ones one by
    one, taking no memory for another list.
    """
    return (line for line in data.splitlines() if line)


class ECLock:
    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._lock = threading.Lock()

    def __enter__(self) -> None:
        self._logger.debug(
            "[%(thread_name)s] Trying to acquire lock",
            {"thread_name": threading.current_thread().name},
        )
        self._lock.acquire()
        self._logger.debug(
            "[%(thread_name)s] Acquired lock", {"thread_name": threading.current_thread().name}
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        self._logger.debug(
            "[%(thread_name)s] Releasing lock", {"thread_name": threading.current_thread().name}
        )
        self._lock.release()
        return False  # Do not swallow exceptions
