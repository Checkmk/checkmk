#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import threading
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
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


# Like the buffer for UDP datagrams, so a message is at most as long via TCP, the event pipe and
# from spool files. Buffering more for an incomplete message would let a client use up our memory.
MAX_MESSAGE_SIZE = 65535

# The OpenTelemetry collector sends each log record as a message to the event socket. With the
# default limits of its OTLP receivers, a record takes at most 20 MiB via HTTP and 4 MiB via gRPC,
# or a third more if its body is bytes, which it sends as base64. Only the site user and its group
# may connect to the event socket, so buffering that much for each connection is OK.
MAX_EVENT_SOCKET_MESSAGE_SIZE = 32 * 1024 * 1024

# RFC 6587 doesn't limit MSG-LEN, but int() refuses more than 4300 digits, and no syslog message
# comes near the gigabyte of 9 digits. Matching no more digits than that, a longer number takes no
# time to refuse, even when its line is parsed again for each new part of it.
_MSG_LEN = re.compile(rb"([1-9][0-9]{0,8}) ")


def parse_msg_len(tokens: Tokens) -> ParseResult[int]:
    """MSG-LEN = NONZERO-DIGIT *DIGIT, see RFC 6587, but a longer number than 9 digits fails"""
    if (match := _MSG_LEN.match(tokens)) is None:
        return Failure, tokens
    return int(match[1]), tokens[match.end() :]


_NEWLINE = re.compile(b"\n")


def parse_non_transparent_frame(tokens: Tokens) -> ParseResult[bytes]:
    # Searching in C, the rest of a long line doesn't take long to search again for more data.
    if (newline := _NEWLINE.search(tokens)) is None:
        return Failure, tokens
    return bytes(tokens[: newline.start()]), tokens[newline.end() :]


_PRI = re.compile(rb"<[0-9]{1,3}>")


def parse_pri(tokens: Tokens) -> ParseResult[bytes]:
    """PRI = "<" PRIVAL ">", PRIVAL = 1*3DIGIT, see RFC 5424"""
    if (match := _PRI.match(tokens)) is None:
        return Failure, tokens
    return match[0], tokens[match.end() :]


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


# The longest start of a message which can decide about octet counting: A number of 9 digits, a
# space and a priority, see parse_msg_len() and parse_syslog_msg_len(). So if a start at least that
# long isn't octet-counted, it is the start of a line, whatever comes after it.
_OCTET_COUNTING_LOOKAHEAD = len(b"999999999 <999>")


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


@dataclass(frozen=True)
class Incomplete:
    """The start of a message, too short to tell whether it is octet-counted, waiting for its rest"""

    data: bytes = b""


@dataclass
class IncompleteLine:
    """
    The start of a line without a newline, too long to be octet-counted, so only the next data
    needs to be searched for its newline. next_messages() extends it in place, so a long line
    arriving in many small parts takes linear time.
    """

    data: bytearray


@dataclass
class IncompleteOctetCounted:
    """
    The start of an octet-counted message of the given length, waiting for its rest, but at most
    as long as the maximum message size. next_messages() extends it in place, like a line.
    """

    length: int
    data: bytearray


@dataclass(frozen=True)
class Skipping:
    """The rest of an overlong octet-counted message, skipped by its count"""

    count: int


@dataclass(frozen=True)
class Discarding:
    """The rest of an overlong line, discarded up to the next newline"""


# What a stream of messages keeps for its next data
type Unprocessed = Incomplete | IncompleteLine | IncompleteOctetCounted | Skipping | Discarding


def unprocessed_size(unprocessed: Unprocessed) -> int:
    """How many bytes of an incomplete message the stream keeps"""
    match unprocessed:
        case Incomplete(data=data) | IncompleteLine(data=data) | IncompleteOctetCounted(data=data):
            return len(data)
        case Skipping() | Discarding():
            return 0


class Truncated(bytes):
    """The start of a message longer than its maximum size, so that its receiver can tell"""


def _truncated(message: bytes, max_size: int) -> bytes:
    """The message, or only its start if it is longer than the maximum size"""
    return Truncated(message[:max_size]) if len(message) > max_size else message


def _incomplete_line(line: bytes | Tokens, max_size: int) -> tuple[Sequence[bytes], Unprocessed]:
    """The start of a line without a newline so far, truncated as soon as it is overlong"""
    if len(line) > max_size:
        return [Truncated(line[:max_size])], Discarding()
    if len(line) < _OCTET_COUNTING_LOOKAHEAD:  # More data may make it octet-counted.
        return [], Incomplete(bytes(line))
    return [], IncompleteLine(bytearray(line))


@dataclass(frozen=True)
class Framing:
    """How to split the bytes received from a source into messages, see next_messages()"""

    # The octet count at the start of a message, or Failure for a line
    msg_len_parser: Parser[int]
    # A longer message is truncated and marked as Truncated, and its rest is skipped.
    max_message_size: int

    def __call__(self, data: bytes) -> tuple[Sequence[bytes], Unprocessed]:
        """
        Splits a bunch of bytes into messages and what to keep for the next data. Truncates an
        incomplete message as soon as enough of it is there, so the rest of it is skipped with the
        next data. Drops empty messages like rsyslog, e.g. from a newline which a sender adds
        after an octet-counted message.
        """
        max_size = self.max_message_size
        messages: list[bytes] = []
        tokens = memoryview(data)
        while tokens:
            message, rest = parse_message(self.msg_len_parser, tokens)
            if message is Failure:
                break
            if message:
                messages.append(_truncated(message, max_size))
            tokens = rest
        msg_len, rest = self.msg_len_parser(tokens)
        if msg_len is Failure:  # a line, with no newline so far
            line_start, unprocessed = _incomplete_line(tokens, max_size)
            return [*messages, *line_start], unprocessed
        if len(rest) < max_size:  # an octet-counted message, waiting for more of it
            return messages, IncompleteOctetCounted(msg_len, bytearray(rest))
        # An overlong octet-counted message, so take its start and skip its rest by its count.
        return [*messages, Truncated(rest[:max_size])], Skipping(msg_len - len(rest))


# Syslog via TCP takes Octet counting (if a message starts with a number of at most 9 digits, a
# space and a syslog priority, see parse_syslog_msg_len()) and Non-Transparent framing (if '\n' is
# used as a separator), see https://www.rfc-editor.org/rfc/rfc6587#section-3.4:
#
#     TCP-DATA = *SYSLOG-FRAME
#     SYSLOG-FRAME = MSG-LEN SP SYSLOG-MSG   ; Octet-counting method
#     MSG-LEN = NONZERO-DIGIT *DIGIT
#     NONZERO-DIGIT = %d49-57
SYSLOG_VIA_TCP = Framing(parse_syslog_msg_len, MAX_MESSAGE_SIZE)

# Like syslog via TCP, but for longer messages, see MAX_EVENT_SOCKET_MESSAGE_SIZE
EVENT_SOCKET = Framing(parse_syslog_msg_len, MAX_EVENT_SOCKET_MESSAGE_SIZE)


def _parse_no_msg_len(tokens: Tokens) -> ParseResult[int]:
    """No octet counting at all, so each message is a line"""
    return Failure, tokens


# Unlike the event socket, the event pipe takes no octet counting at all, not even for syslog
# messages: All local programs write into the same pipe, and anybody may (its mode is 0662), so a
# wrong octet count, by mistake or on purpose, would hold back or swallow the messages of all
# programs after it, while on the event socket, it only affects the connection of its sender. And as
# writes to a pipe are atomic only up to PIPE_BUF, i.e. 4096 bytes, longer octet-counted messages of
# concurrent writers could get mixed up anyway. No sender needs it there: mkevent, and with it the
# notification plug-in, as well as the CREATE command of the status socket write a line each, and
# the OpenTelemetry collector sends its octet-counted syslog messages to the event socket.
EVENT_PIPE = Framing(_parse_no_msg_len, MAX_MESSAGE_SIZE)


def parse_spool_file(data: bytes) -> Iterator[bytes]:
    """
    Parse the data of a spool file into messages, a line each, without empty ones and truncating
    longer ones than MAX_MESSAGE_SIZE like the other framings. Unlike the event pipe, it also ends a
    line at a carriage return, and it takes the last line without a newline, too.

    It splits the lines right away, so a lack of memory shows here, but drops and truncates them one
    by one, taking no memory for another list.
    """
    return (_truncated(line, MAX_MESSAGE_SIZE) for line in data.splitlines() if line)


def next_messages(
    framing: Framing, unprocessed: Unprocessed, data: bytes
) -> tuple[Sequence[bytes], Unprocessed]:
    """
    Splits the data received after what was unprocessed into messages. It extends the start of a
    long line or of an octet-counted message in place, and searches only the new data for the
    newline ending a long line, so a message arriving in many small parts takes linear time.
    """
    max_size = framing.max_message_size
    match unprocessed:
        case Incomplete(start):  # Shorter than _OCTET_COUNTING_LOOKAHEAD, so copying it is cheap
            return framing(start + data)
        case IncompleteLine(line):
            if (newline := data.find(b"\n")) == -1:
                line.extend(data[: max_size + 1 - len(line)])
                if len(line) > max_size:
                    return [Truncated(line[:max_size])], Discarding()
                return [], unprocessed
            messages, rest = framing(data[newline + 1 :])
            return [_truncated(bytes(line) + data[:newline], max_size), *messages], rest
        case IncompleteOctetCounted(length, start):
            missing = min(length, max_size) - len(start)
            start.extend(data[:missing])
            if len(data) < missing:
                return [], unprocessed
            if length <= max_size:
                messages, rest = framing(data[missing:])
                return [bytes(start), *messages], rest
            # An overlong one, so take its start and skip its rest by its count.
            messages, rest = next_messages(framing, Skipping(length - max_size), data[missing:])
            return [Truncated(start), *messages], rest
        case Skipping(count) if count > len(data):
            return [], Skipping(count - len(data))
        case Skipping(count):
            return framing(data[count:])
        case Discarding():
            if (newline := data.find(b"\n")) == -1:
                return [], unprocessed
            return framing(data[newline + 1 :])


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
