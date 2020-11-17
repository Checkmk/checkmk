#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes defining the check helper protocol."""

import abc
import enum
import json
import logging
import pickle
import struct
from typing import Final, Type, Union

import cmk.utils.log as log
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import MKTimeout
from cmk.utils.type_defs import result, SectionName
from cmk.utils.type_defs.protocol import Protocol

from cmk.snmplib.type_defs import AbstractRawData, SNMPRawData

from . import FetcherType

__all__ = [
    "L3Message",
    "PayloadType",
    "FetcherHeader",
    "FetcherMessage",
    "CMCHeader",
    "CMCMessage",
    "make_result_answer",
    "make_log_answer",
    "make_end_of_reply_answer",
    "make_fetcher_timeout_message",
]


class CMCLogLevel(str, enum.Enum):
    """The CMC logging level from `Logger.h::LogLevel`."""
    EMERGENCY = "emergenc"  # truncated!
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"

    @staticmethod
    def from_level(level: int) -> "CMCLogLevel":
        return {
            logging.CRITICAL: CMCLogLevel.CRITICAL,
            logging.ERROR: CMCLogLevel.ERROR,
            logging.WARNING: CMCLogLevel.WARNING,
            logging.INFO: CMCLogLevel.NOTICE,
            log.VERBOSE: CMCLogLevel.INFO,
            logging.DEBUG: CMCLogLevel.DEBUG,
        }[level]


class Header(Protocol):
    pass


class L3Message(Protocol):
    fmt = "!HQ"
    length = struct.calcsize(fmt)

    @property
    @abc.abstractmethod
    def payload_type(self) -> "PayloadType":
        raise NotImplementedError

    @abc.abstractmethod
    def result(self) -> result.Result[AbstractRawData, Exception]:
        raise NotImplementedError


class L3Stats(Protocol):
    def __init__(self, duration: Snapshot) -> None:
        self.duration: Final = duration

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self.duration)

    def __bytes__(self) -> bytes:
        return json.dumps({"duration": self.duration.serialize()}).encode("ascii")

    @classmethod
    def from_bytes(cls, data: bytes) -> "L3Stats":
        return L3Stats(Snapshot.deserialize(json.loads(data.decode("ascii"))["duration"]))


class PayloadType(enum.Enum):
    ERROR = enum.auto()
    AGENT = enum.auto()
    SNMP = enum.auto()

    def make(self) -> Type[L3Message]:
        # This typing error is a false positive.  There are tests to demonstrate that.
        return {  # type: ignore[return-value]
            PayloadType.ERROR: ErrorPayload,
            PayloadType.AGENT: AgentPayload,
            PayloadType.SNMP: SNMPPayload,
        }[self]


class AgentPayload(L3Message):
    payload_type = PayloadType.AGENT

    def __init__(self, value: bytes) -> None:
        self._value: Final = value

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._value)

    def __bytes__(self) -> bytes:
        return struct.pack(L3Message.fmt, self.payload_type.value, len(self._value)) + self._value

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentPayload":
        _type, length, *_rest = struct.unpack(
            L3Message.fmt,
            data[:L3Message.length],
        )
        try:
            return cls(data[L3Message.length:L3Message.length + length])
        except SyntaxError as exc:
            raise ValueError(repr(data)) from exc

    def result(self) -> result.Result[AbstractRawData, Exception]:
        return result.OK(self._value)


class SNMPPayload(L3Message):
    payload_type = PayloadType.SNMP

    def __init__(self, value: SNMPRawData) -> None:
        self._value: Final[SNMPRawData] = value

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._value)

    def __bytes__(self) -> bytes:
        payload = self._serialize(self._value)
        return struct.pack(SNMPPayload.fmt, self.payload_type.value, len(payload)) + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "SNMPPayload":
        _type, length, *_rest = struct.unpack(
            SNMPPayload.fmt,
            data[:L3Message.length],
        )
        try:
            return cls(cls._deserialize(data[L3Message.length:L3Message.length + length]))
        except SyntaxError as exc:
            raise ValueError(repr(data)) from exc

    def result(self) -> result.Result[SNMPRawData, Exception]:
        return result.OK(self._value)

    @staticmethod
    def _serialize(value: SNMPRawData) -> bytes:
        return json.dumps({str(k): v for k, v in value.items()}).encode("utf8")

    @staticmethod
    def _deserialize(data: bytes) -> SNMPRawData:
        try:
            return {SectionName(k): v for k, v in json.loads(data.decode("utf8")).items()}
        except json.JSONDecodeError:
            raise ValueError(repr(data))


class ErrorPayload(L3Message):
    payload_type = PayloadType.ERROR

    def __init__(self, error: Exception) -> None:
        self._error: Final = error

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._error)

    def __bytes__(self) -> bytes:
        payload = self._serialize(self._error)
        return struct.pack(L3Message.fmt, self.payload_type.value, len(payload)) + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "ErrorPayload":
        _type, length, *_rest = struct.unpack(
            L3Message.fmt,
            data[:L3Message.length],
        )
        try:
            return cls(cls._deserialize(data[L3Message.length:L3Message.length + length]))
        except SyntaxError as exc:
            raise ValueError(repr(data)) from exc

    def result(self) -> result.Result[AbstractRawData, Exception]:
        return result.Error(self._error)

    @staticmethod
    def _serialize(error: Exception) -> bytes:
        return pickle.dumps(error)

    @staticmethod
    def _deserialize(data: bytes) -> Exception:
        try:
            return pickle.loads(data)
        except pickle.UnpicklingError as exc:
            raise ValueError(data) from exc


class FetcherHeader(Header):
    """Header is fixed size bytes in format:

    <FETCHER_TYPE><PAYLOAD_TYPE><STATUS><PAYLOAD_SIZE><STATS_SIZE>

    This is an application layer protocol used to transmit data
    from the fetcher to the checker.

    """
    fmt = "!HHHII"
    length = struct.calcsize(fmt)

    def __init__(
        self,
        fetcher_type: FetcherType,
        payload_type: PayloadType,
        *,
        status: int,
        payload_length: int,
        stats_length: int,
    ) -> None:
        self.fetcher_type: Final[FetcherType] = fetcher_type
        self.payload_type: Final[PayloadType] = payload_type
        self.status: Final[int] = status
        self.payload_length: Final[int] = payload_length
        self.stats_length: Final[int] = stats_length

    @property
    def name(self) -> str:
        return self.fetcher_type.name

    def __repr__(self) -> str:
        return "%s(%r, %r, status=%r, payload_length=%r, stats_length=%r)" % (
            type(self).__name__,
            self.fetcher_type,
            self.payload_type,
            self.status,
            self.payload_length,
            self.stats_length,
        )

    def __len__(self) -> int:
        return FetcherHeader.length

    def __bytes__(self) -> bytes:
        return struct.pack(
            FetcherHeader.fmt,
            self.fetcher_type.value,
            self.payload_type.value,
            self.status,
            self.payload_length,
            self.stats_length,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'FetcherHeader':
        try:
            fetcher_type, payload_type, status, payload_length, stats_length = struct.unpack(
                FetcherHeader.fmt,
                data[:cls.length],
            )
            return cls(
                FetcherType(fetcher_type),
                PayloadType(payload_type),
                status=status,
                payload_length=payload_length,
                stats_length=stats_length,
            )
        except struct.error as exc:
            raise ValueError(data) from exc


class FetcherMessage(Protocol):
    def __init__(
        self,
        header: FetcherHeader,
        payload: L3Message,
        stats: L3Stats,
    ) -> None:
        self.header: Final[FetcherHeader] = header
        self.payload: Final[L3Message] = payload
        self.stats: Final[L3Stats] = stats

    def __repr__(self) -> str:
        return "%s(%r, %r, %r)" % (type(self).__name__, self.header, self.payload, self.stats)

    def __bytes__(self) -> bytes:
        return self.header + self.payload + self.stats

    @classmethod
    def from_bytes(cls, data: bytes) -> "FetcherMessage":
        header = FetcherHeader.from_bytes(data)
        payload = header.payload_type.make().from_bytes(
            data[len(header):len(header) + header.payload_length],)
        stats = L3Stats.from_bytes(data[len(header) + header.payload_length:len(header) +
                                        header.payload_length + header.stats_length])
        return cls(header, payload, stats)

    @classmethod
    def from_raw_data(
        cls,
        raw_data: result.Result[AbstractRawData, Exception],
        duration: Snapshot,
        fetcher_type: FetcherType,
    ) -> "FetcherMessage":
        stats = L3Stats(duration)
        if raw_data.is_error():
            error_payload = ErrorPayload(raw_data.error)
            return cls(
                FetcherHeader(
                    fetcher_type,
                    payload_type=PayloadType.ERROR,
                    status=50,
                    payload_length=len(error_payload),
                    stats_length=len(stats),
                ),
                error_payload,
                stats,
            )

        if fetcher_type is FetcherType.SNMP:
            assert isinstance(raw_data.ok, dict)
            snmp_payload = SNMPPayload(raw_data.ok)
            return cls(
                FetcherHeader(
                    fetcher_type,
                    payload_type=PayloadType.SNMP,
                    status=0,
                    payload_length=len(snmp_payload),
                    stats_length=len(stats),
                ),
                snmp_payload,
                stats,
            )

        assert isinstance(raw_data.ok, bytes)
        agent_payload = AgentPayload(raw_data.ok)
        return cls(
            FetcherHeader(
                fetcher_type,
                payload_type=PayloadType.AGENT,
                status=0,
                payload_length=len(agent_payload),
                stats_length=len(stats),
            ),
            agent_payload,
            stats,
        )

    @property
    def fetcher_type(self) -> FetcherType:
        return self.header.fetcher_type

    @property
    def raw_data(self) -> result.Result[AbstractRawData, Exception]:
        return self.payload.result()


class CMCHeader(Header):
    """Header is fixed size(6+8+9+9 = 32 bytes) bytes in format

      header: <ID>:<'RESULT '|'LOG    '|'ENDREPL'>:<LOGLEVEL>:<SIZE>:
      ID       - 5 bytes protocol id, "fetch" at the start
      LOGLEVEL - 8 bytes log level, '        ' for 'RESULT' and 'ENDREPL',
                 for 'LOG' one of 'emergenc', 'alert   ', 'critical',
                 'error   ', 'warning ', 'notice  ', 'info    ', 'debug   '
      SIZE     - 8 bytes text 0..9

    Example:
        b"base0:RESULT :        :12345678:"

    This is first(transport) layer protocol.
    Used to
    - transmit data (as opaque payload) from fetcher through Microcore to the checker.
    - provide centralized logging facility if the field loglevel is not empty
    ATTENTION: This protocol must 100% of time synchronised with microcore code.
    """
    class State(str, enum.Enum):
        RESULT = "RESULT "
        LOG = "LOG    "
        END_OF_REPLY = "ENDREPL"

    fmt = "{:<5}:{:<7}:{:<8}:{:<8}:"
    length = 32

    def __init__(
        self,
        name: str,
        state: Union['CMCHeader.State', str],
        log_level: str,
        payload_length: int,
    ) -> None:
        self.name = name
        self.state = CMCHeader.State(state) if isinstance(state, str) else state
        self.log_level = log_level  # contains either log_level or empty field
        self.payload_length = payload_length

    def __repr__(self) -> str:
        return "%s(%r, %r, %r, %r)" % (
            type(self).__name__,
            self.name,
            self.state,
            self.log_level,
            self.payload_length,
        )

    def __len__(self) -> int:
        return CMCHeader.length

    # E0308: false positive, see https://github.com/PyCQA/pylint/issues/3599
    def __bytes__(self) -> bytes:  # pylint: disable=E0308
        return CMCHeader.fmt.format(
            self.name[:5],
            self.state[:7],
            self.log_level[:8],
            self.payload_length,
        ).encode("ascii")

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CMCHeader':
        try:
            # to simplify parsing we are using ':' as a splitter
            name, state, log_level, payload_length = data[:CMCHeader.length].split(b":")[:4]
            return cls(
                name.decode("ascii"),
                state.decode("ascii"),
                log_level.decode("ascii"),
                int(payload_length.decode("ascii"), base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self) -> 'CMCHeader':
        return CMCHeader(self.name, self.state, self.log_level, self.payload_length)

    @staticmethod
    def default_protocol_name() -> str:
        return "fetch"


class CMCMessage(Protocol):
    def __init__(
        self,
        header: CMCHeader,
        *payload: FetcherMessage,
    ) -> None:
        self.header: Final = header
        self.payload: Final = payload

    def __repr__(self) -> str:
        return "%s(%r, %r)" % (type(self).__name__, self.header, self.payload)

    def __bytes__(self) -> bytes:
        return self.header + b"".join(bytes(msg) for msg in self.payload)

    @classmethod
    def from_bytes(cls, data: bytes) -> "CMCMessage":
        header = CMCHeader.from_bytes(data)
        index = len(header)
        messages = []
        while index < len(header) + header.payload_length:
            message = FetcherMessage.from_bytes(data[index:])
            index += len(message)
            messages.append(message)
        return CMCMessage(header, *messages)

    @classmethod
    def end_of_reply(cls) -> "CMCMessage":
        return _END_OF_REPLY


_END_OF_REPLY = CMCMessage(  # Singleton
    CMCHeader(
        name=CMCHeader.default_protocol_name(),
        state=CMCHeader.State.END_OF_REPLY,
        log_level=" ",
        payload_length=0,
    ), *())


def make_result_answer(*messages: FetcherMessage) -> bytes:
    """ Provides valid binary payload to be send from fetcher to checker"""
    return bytes(
        CMCMessage(
            CMCHeader(
                name=CMCHeader.default_protocol_name(),
                state=CMCHeader.State.RESULT,
                log_level=" ",
                payload_length=sum(len(msg) for msg in messages),
            ), *messages))


def make_log_answer(message: str, level: int) -> bytes:
    """Logs data using logging facility of the microcore.

    Args:
        message: The log message.
        level: The numeric level of the logging event (one of DEBUG, INFO, etc.)

    """
    return CMCHeader(
        name=CMCHeader.default_protocol_name(),
        state=CMCHeader.State.LOG,
        log_level=CMCLogLevel.from_level(level),
        payload_length=len(message),
    ) + message.encode("utf-8")


def make_end_of_reply_answer() -> bytes:
    return bytes(CMCMessage.end_of_reply())


def make_error_message(fetcher_type: FetcherType, exc: Exception) -> FetcherMessage:
    stats = L3Stats(Snapshot.null())
    payload = ErrorPayload(exc)
    return FetcherMessage(
        FetcherHeader(
            fetcher_type,
            PayloadType.ERROR,
            status=logging.CRITICAL,
            payload_length=len(payload),
            stats_length=len(stats),
        ),
        payload,
        stats,
    )


def make_fetcher_timeout_message(
    fetcher_type: FetcherType,
    exc: MKTimeout,
    duration: Snapshot,
) -> FetcherMessage:
    stats = L3Stats(duration)
    payload = ErrorPayload(exc)
    return FetcherMessage(
        FetcherHeader(
            fetcher_type,
            PayloadType.ERROR,
            status=logging.ERROR,
            payload_length=len(payload),
            stats_length=len(stats),
        ),
        payload,
        stats,
    )
