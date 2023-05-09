#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes defining the check helper protocol.

We call "message" a header followed by the corresponding payload.

+---------------+----------------+---------------+----------------+
| Layer         | Message type   | Header type   | Payload type   |
+===============+================+===============+================+
| CMC Layer     | CMCMessage     | CMCHeader     | CMCPayload     |
+---------------+----------------+---------------+----------------+
| Fetcher Layer | FetcherMessage | FetcherHeader | ResultMessage  |
|               |                |               | + ResultStats  |
+---------------+----------------+---------------+----------------+
|               |                |      AgentResultMessage        |
| Result Layer  | ResultMessage  |      SNMPResultMessage         |
|               |                |      ErrorResultMessage        |
+---------------+----------------+--------------------------------+

.. uml::

    abstract CMCPayload
    CMCPayload <|-- CMCResults
    CMCPayload <|-- CMCLogging
    CMCPayload <|-- CMCEndOfReply
    CMCMessage o--  CMCHeader
    CMCMessage o-- CMCPayload

    CMCResults o-- "*" FetcherMessage

    abstract ResultMessage
    ResultMessage <|-- AgentResultMessage
    ResultMessage <|-- SNMPResultMessage
    ResultMessage <|-- ErrorResultMessage
    FetcherMessage o-- FetcherHeader
    FetcherMessage o-- ResultMessage
    FetcherMessage o-- ResultStats

    note as N1
    Every class implements
    the <i>Prototype</i> interface,
    not shown for clarity
    end note

"""

from __future__ import annotations

import abc
import enum
import json
import logging
import math
import pickle
import struct
from typing import Final, Iterator, Sequence, Type, Union

import cmk.utils.log as log
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import MKTimeout
from cmk.utils.type_defs import AgentRawData, result, SectionName
from cmk.utils.type_defs.protocol import Protocol
from ._base import MKFetcherError

from cmk.snmplib.type_defs import AbstractRawData, SNMPRawData

from . import FetcherType

__all__ = [
    "CMCHeader",
    "CMCMessage",
    "CMCPayload",
    "FetcherHeader",
    "FetcherMessage",
    "PayloadType",
    "ResultMessage",
]
"""Defines a layered protocol.

We call "message" a header followed by the corresponding payload.

+---------------+----------------+---------------+----------------+
| Layer         | Message type   | Header type   | Payload type   |
+===============+================+===============+================+
| CMC Layer     | CMCMessage     | CMCHeader     | FetcherMessage |
+---------------+----------------+---------------+----------------+
| Fetcher Layer | FetcherMessage | FetcherHeader | ResultMessage  |
|               |                |               | + ResultStats  |
+---------------+----------------+---------------+----------------+
|               |                |      AgentResultMessage        |
| Result Layer  | ResultMessage  |      SNMPResultMessage         |
|               |                |      ErrorResultMessage        |
+---------------+----------------+--------------------------------+

"""


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
        # Table from `cmk.utils.log._level`.
        return {
            logging.CRITICAL: CMCLogLevel.CRITICAL,
            logging.ERROR: CMCLogLevel.ERROR,
            logging.WARNING: CMCLogLevel.WARNING,
            logging.INFO: CMCLogLevel.INFO,
            log.VERBOSE: CMCLogLevel.DEBUG,
            logging.DEBUG: CMCLogLevel.DEBUG,
        }[level]


class ResultMessage(Protocol):
    fmt = "!HQ"
    length = struct.calcsize(fmt)

    @property
    def header(self) -> bytes:
        return struct.pack(ResultMessage.fmt, self.payload_type.value, len(self.payload))

    @property
    @abc.abstractmethod
    def payload(self) -> bytes:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def payload_type(self) -> "PayloadType":
        raise NotImplementedError

    @abc.abstractmethod
    def result(self) -> result.Result[AbstractRawData, Exception]:
        raise NotImplementedError


class ResultStats(Protocol):
    def __init__(self, duration: Snapshot) -> None:
        self.duration: Final = duration

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self.duration)

    def __iter__(self) -> Iterator[bytes]:
        yield json.dumps({"duration": self.duration.serialize()}).encode("ascii")

    @classmethod
    def from_bytes(cls, data: bytes) -> "ResultStats":
        return ResultStats(Snapshot.deserialize(json.loads(data.decode("ascii"))["duration"]))


class PayloadType(enum.Enum):
    ERROR = enum.auto()
    AGENT = enum.auto()
    SNMP = enum.auto()

    def make(self) -> Type[ResultMessage]:
        # This typing error is a false positive.  There are tests to demonstrate that.
        return {  # type: ignore[return-value]
            PayloadType.ERROR: ErrorResultMessage,
            PayloadType.AGENT: AgentResultMessage,
            PayloadType.SNMP: SNMPResultMessage,
        }[self]


class AgentResultMessage(ResultMessage):
    payload_type = PayloadType.AGENT

    def __init__(self, value: AgentRawData) -> None:
        self._value: Final = value

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._value)

    def __len__(self) -> int:
        return ResultMessage.length + len(self._value)

    def __iter__(self) -> Iterator[bytes]:
        yield self.header
        yield self.payload

    @property
    def payload(self) -> bytes:
        return self._value

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentResultMessage":
        _type, length, *_rest = struct.unpack(
            ResultMessage.fmt,
            data[:ResultMessage.length],
        )
        try:
            return cls(AgentRawData(data[ResultMessage.length:ResultMessage.length + length]))
        except SyntaxError as exc:
            raise ValueError(repr(data)) from exc

    def result(self) -> result.Result[AbstractRawData, Exception]:
        return result.OK(self._value)


class SNMPResultMessage(ResultMessage):
    payload_type = PayloadType.SNMP

    def __init__(self, value: SNMPRawData) -> None:
        self._value: Final[SNMPRawData] = value

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._value)

    def __len__(self) -> int:
        return ResultMessage.length + len(self.payload)

    def __iter__(self) -> Iterator[bytes]:
        payload = self.payload
        yield struct.pack(ResultMessage.fmt, self.payload_type.value, len(payload))
        yield payload

    @property
    def payload(self) -> bytes:
        return self._serialize(self._value)

    @classmethod
    def from_bytes(cls, data: bytes) -> "SNMPResultMessage":
        _type, length, *_rest = struct.unpack(
            ResultMessage.fmt,
            data[:ResultMessage.length],
        )
        try:
            return cls(cls._deserialize(data[ResultMessage.length:ResultMessage.length + length]))
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
            return SNMPRawData(
                {SectionName(k): v for k, v in json.loads(data.decode("utf8")).items()})
        except json.JSONDecodeError:
            raise ValueError(repr(data))


class ErrorResultMessage(ResultMessage):
    payload_type = PayloadType.ERROR

    def __init__(self, error: Exception) -> None:
        self._error: Final = error

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._error)

    def __iter__(self) -> Iterator[bytes]:
        payload = self.payload
        yield struct.pack(ResultMessage.fmt, self.payload_type.value, len(payload))
        yield payload

    @property
    def payload(self) -> bytes:
        return self._serialize(self._error)

    @classmethod
    def from_bytes(cls, data: bytes) -> "ErrorResultMessage":
        _type, length, *_rest = struct.unpack(
            ResultMessage.fmt,
            data[:ResultMessage.length],
        )
        try:
            return cls(cls._deserialize(data[ResultMessage.length:ResultMessage.length + length]))
        except SyntaxError as exc:
            raise ValueError(repr(data)) from exc

    def result(self) -> result.Result[AbstractRawData, Exception]:
        return result.Error(self._error)

    @staticmethod
    def _serialize(error: Exception) -> bytes:
        return pickle.dumps({"exc_type": type(error), "exc_args": error.args})

    @staticmethod
    def _deserialize(data: bytes) -> Exception:
        try:
            ser = pickle.loads(data)
            return ser["exc_type"](*ser["exc_args"])
        except pickle.UnpicklingError as exc:
            raise ValueError(data) from exc


class FetcherHeader(Protocol):
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

    def __iter__(self) -> Iterator[bytes]:
        yield struct.pack(
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
        payload: ResultMessage,
        stats: ResultStats,
    ) -> None:
        self.header: Final[FetcherHeader] = header
        self.payload: Final[ResultMessage] = payload
        self.stats: Final[ResultStats] = stats

    def __repr__(self) -> str:
        return "%s(%r, %r, %r)" % (type(self).__name__, self.header, self.payload, self.stats)

    def __len__(self) -> int:
        return len(self.header) + self.header.payload_length + self.header.stats_length

    def __iter__(self) -> Iterator[bytes]:
        yield from self.header
        yield from self.payload
        yield from self.stats

    @classmethod
    def from_bytes(cls, data: bytes) -> "FetcherMessage":
        header = FetcherHeader.from_bytes(data)
        payload = header.payload_type.make().from_bytes(
            data[len(header):len(header) + header.payload_length],)
        stats = ResultStats.from_bytes(data[len(header) + header.payload_length:len(header) +
                                            header.payload_length + header.stats_length])
        return cls(header, payload, stats)

    @classmethod
    def from_raw_data(
        cls,
        raw_data: result.Result[AbstractRawData, Exception],
        duration: Snapshot,
        fetcher_type: FetcherType,
    ) -> "FetcherMessage":
        stats = ResultStats(duration)
        if raw_data.is_error():
            error_payload = ErrorResultMessage(raw_data.error)
            return cls(
                FetcherHeader(
                    fetcher_type,
                    payload_type=PayloadType.ERROR,
                    status=logging.INFO
                    if isinstance(raw_data.error, MKFetcherError) else logging.CRITICAL,
                    payload_length=len(error_payload),
                    stats_length=len(stats),
                ),
                error_payload,
                stats,
            )

        if fetcher_type is FetcherType.SNMP:
            assert isinstance(raw_data.ok, dict)
            snmp_payload = SNMPResultMessage(raw_data.ok)
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
        agent_payload = AgentResultMessage(raw_data.ok)
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

    @classmethod
    def error(cls, fetcher_type: FetcherType, exc: Exception) -> "FetcherMessage":
        stats = ResultStats(Snapshot.null())
        payload = ErrorResultMessage(exc)
        return cls(
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

    @classmethod
    def timeout(
        cls,
        fetcher_type: FetcherType,
        exc: MKTimeout,
        duration: Snapshot,
    ) -> "FetcherMessage":
        stats = ResultStats(duration)
        payload = ErrorResultMessage(exc)
        return cls(
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

    @property
    def fetcher_type(self) -> FetcherType:
        return self.header.fetcher_type

    @property
    def raw_data(self) -> result.Result[AbstractRawData, Exception]:
        return self.payload.result()


class CMCHeader(Protocol):
    """Header is fixed size(6+8+9+9 = 32 bytes) bytes in format

      header: <ID>:<'RESULT '|'LOG    '|'ENDREPL'>:<LOGLEVEL>:<SIZE>:
      ID       - 5 bytes protocol id, "fetch" at the start
      LOGLEVEL - 8 bytes log level, '        ' for 'RESULT' and 'ENDREPL',
                 for 'LOG' one of 'emergenc', 'alert   ', 'critical',
                 'error   ', 'warning ', 'notice  ', 'info    ', 'debug   '
      SIZE     - 16 bytes text 0..9  (54 bits, unsigned)

    Example:
        b"base0:RESULT :        :1234567812345678:"

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

    fmt = "{:<5}:{:<7}:{:<8}:{:<16}:"
    length = 40

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
    def __iter__(self) -> Iterator[bytes]:  # pylint: disable=E0308
        yield CMCHeader.fmt.format(
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


class CMCPayload(Protocol):
    pass


class CMCResultsStats(Protocol):
    fmt = "!I"
    length = struct.calcsize(fmt)

    def __init__(self, timeout: int, duration: Snapshot) -> None:
        self.timeout: Final = timeout
        self.duration: Final = duration

    @property
    def remaining_time(self) -> int:
        return max(0, self.timeout - math.ceil(self.duration.process.elapsed))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.timeout!r}, {self.duration!r})"

    def __iter__(self) -> Iterator[bytes]:
        conf = json.dumps({
            "duration": self.duration.serialize(),
            "timeout": self.timeout
        }).encode("ascii")
        yield struct.pack(type(self).fmt, len(conf))
        yield conf

    @classmethod
    def from_bytes(cls, data: bytes) -> CMCResultsStats:
        conf_len = struct.unpack(cls.fmt, data[:cls.length])[0]
        conf = json.loads(data[cls.length:cls.length + conf_len].decode("ascii"))
        return cls(conf["timeout"], Snapshot.deserialize(conf["duration"]))


class CMCResults(CMCPayload):
    fmt = "!I"
    length = struct.calcsize(fmt)

    def __init__(self, messages: Sequence[FetcherMessage], stats: CMCResultsStats) -> None:
        self.messages: Final = messages
        self.stats: Final = stats

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.messages!r}, {self.stats!r})"

    def __iter__(self) -> Iterator[bytes]:
        yield struct.pack(type(self).fmt, self.message_count)
        yield from (bytes(msg) for msg in self.messages)
        yield from self.stats

    @classmethod
    def from_bytes(cls, data: bytes) -> CMCResults:
        messages = []
        index = cls.length
        for _n in range(struct.unpack(cls.fmt, data[:cls.length])[0]):
            message = FetcherMessage.from_bytes(data[index:])
            messages.append(message)
            index += len(message)
        return cls(messages, CMCResultsStats.from_bytes(data[index:]))


class CMCLogging(CMCPayload):
    def __init__(self, message: str) -> None:
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r})"

    def __iter__(self) -> Iterator[bytes]:
        yield self.message.encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> CMCLogging:
        return cls(data.decode("utf-8"))


class CMCEndOfReply(CMCPayload):
    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def __len__(self) -> int:
        return 0

    def __bytes__(self) -> bytes:
        return b""

    def __iter__(self) -> Iterator[bytes]:
        yield from ()

    @classmethod
    def from_bytes(cls, data: bytes) -> CMCEndOfReply:
        return _END_OF_REPLY_PAYLOAD


class CMCMessage(Protocol):
    def __init__(
        self,
        header: CMCHeader,
        payload: CMCPayload,
    ) -> None:
        self.header: Final = header
        self.payload: Final = payload

    def __repr__(self) -> str:
        return "%s(%r, %r)" % (type(self).__name__, self.header, self.payload)

    def __len__(self) -> int:
        return len(self.header) + self.header.payload_length

    def __iter__(self) -> Iterator[bytes]:
        yield from self.header
        yield from self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> CMCMessage:
        header = CMCHeader.from_bytes(data)
        if header.state is CMCHeader.State.RESULT:
            return CMCMessage(
                header,
                CMCResults.from_bytes(data[len(header):len(header) + header.payload_length]),
            )
        if header.state is CMCHeader.State.LOG:
            return CMCMessage(
                header,
                CMCLogging.from_bytes(data[len(header):len(header) + header.payload_length]),
            )
        assert header.state is CMCHeader.State.END_OF_REPLY
        return cls.end_of_reply()

    @classmethod
    def result_answer(cls, messages: Sequence[FetcherMessage], timeout: int,
                      duration: Snapshot) -> CMCMessage:
        payload = CMCResults(messages, CMCResultsStats(timeout, duration))
        return cls(
            CMCHeader(
                name=CMCHeader.default_protocol_name(),
                state=CMCHeader.State.RESULT,
                log_level=" ",
                payload_length=len(payload),
            ),
            payload,
        )

    @classmethod
    def log_answer(cls, message: str, level: int) -> CMCMessage:
        """Logs data using logging facility of the microcore.

        Args:
            message: The log message.
            level: The numeric level of the logging event (one of DEBUG, INFO, etc.)

        """
        return cls(
            CMCHeader(
                name=CMCHeader.default_protocol_name(),
                state=CMCHeader.State.LOG,
                log_level=CMCLogLevel.from_level(level),
                payload_length=len(message),
            ),
            CMCLogging(message),
        )

    @classmethod
    def end_of_reply(cls) -> CMCMessage:
        return _END_OF_REPLY


_END_OF_REPLY_PAYLOAD = CMCEndOfReply()
_END_OF_REPLY = CMCMessage(  # Singleton
    CMCHeader(
        name=CMCHeader.default_protocol_name(),
        state=CMCHeader.State.END_OF_REPLY,
        log_level=" ",
        payload_length=0,
    ),
    _END_OF_REPLY_PAYLOAD,
)
