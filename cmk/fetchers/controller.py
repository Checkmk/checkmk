#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Protocol fetcher -> core: <header><payload>

import abc
import contextlib
import enum
import json
import logging
import os
import pickle
import signal
import struct
from pathlib import Path
from types import FrameType
from typing import Any, Dict, Final, Iterator, List, Optional, Type, Union, NamedTuple

import cmk.utils.log as log
from cmk.utils.exceptions import MKTimeout
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.type_defs import (
    ConfigSerial,
    ErrorResult,
    HostName,
    OKResult,
    Protocol,
    Result,
    SectionName,
)

from cmk.snmplib.type_defs import AbstractRawData, SNMPRawData

from . import FetcherType
from .type_defs import Mode


class CmcLogLevel(str, enum.Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


def cmc_log_level_from_python(log_level: int) -> CmcLogLevel:
    try:
        return {
            logging.CRITICAL: CmcLogLevel.CRITICAL,
            logging.ERROR: CmcLogLevel.ERROR,
            logging.WARNING: CmcLogLevel.WARNING,
            logging.INFO: CmcLogLevel.INFO,
            log.VERBOSE: CmcLogLevel.INFO,
            logging.DEBUG: CmcLogLevel.DEBUG,
        }[log_level]
    except KeyError:
        return CmcLogLevel.WARNING


#
# Protocols
#


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
    def result(self) -> Result[AbstractRawData, Exception]:
        raise NotImplementedError


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

    def result(self) -> Result[AbstractRawData, Exception]:
        return OKResult(self._value)


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

    def result(self) -> Result[SNMPRawData, Exception]:
        return OKResult(self._value)

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

    def result(self) -> Result[AbstractRawData, Exception]:
        return ErrorResult(self._error)

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

    <FETCHER_TYPE><PAYLOAD_TYPE><STATUS><PAYLOAD_SIZE>

    This is an application layer protocol used to transmit data
    from the fetcher to the checker.

    """
    fmt = "!HHHI"
    length = struct.calcsize(fmt)

    def __init__(
        self,
        fetcher_type: FetcherType,
        payload_type: PayloadType,
        *,
        status: int,
        payload_length: int,
    ) -> None:
        self.fetcher_type: Final[FetcherType] = fetcher_type
        self.payload_type: Final[PayloadType] = payload_type
        self.status: Final[int] = status
        self.payload_length: Final[int] = payload_length

    @property
    def name(self) -> str:
        return self.fetcher_type.name

    def __repr__(self) -> str:
        return "%s(%r, %r, status=%r, payload_length=%r)" % (
            type(self).__name__,
            self.fetcher_type,
            self.payload_type,
            self.status,
            self.payload_length,
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
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'FetcherHeader':
        try:
            fetcher_type, payload_type, status, payload_length = struct.unpack(
                FetcherHeader.fmt,
                data[:cls.length],
            )
            return cls(
                FetcherType(fetcher_type),
                PayloadType(payload_type),
                status=status,
                payload_length=payload_length,
            )
        except struct.error as exc:
            raise ValueError(data) from exc


class FetcherMessage(Protocol):
    def __init__(self, header: FetcherHeader, payload: L3Message) -> None:
        self.header: Final[FetcherHeader] = header
        self.payload: Final[L3Message] = payload

    def __repr__(self) -> str:
        return "%s(%r, %r)" % (type(self).__name__, self.header, self.payload)

    def __bytes__(self) -> bytes:
        return self.header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "FetcherMessage":
        header = FetcherHeader.from_bytes(data)
        payload = header.payload_type.make().from_bytes(
            data[len(header):len(header) + header.payload_length],)
        return cls(header, payload)

    @classmethod
    def from_raw_data(
        cls,
        raw_data: Result[AbstractRawData, Exception],
        fetcher_type: FetcherType,
    ) -> "FetcherMessage":
        if raw_data.is_error():
            error_payload = ErrorPayload(raw_data.error)
            return cls(
                FetcherHeader(
                    fetcher_type,
                    payload_type=PayloadType.ERROR,
                    status=50,
                    payload_length=len(error_payload),
                ),
                error_payload,
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
                ),
                snmp_payload,
            )

        assert isinstance(raw_data.ok, bytes)
        agent_payload = AgentPayload(raw_data.ok)
        return cls(
            FetcherHeader(
                fetcher_type,
                payload_type=PayloadType.AGENT,
                status=0,
                payload_length=len(agent_payload),
            ),
            agent_payload,
        )

    @property
    def raw_data(self) -> Result[AbstractRawData, Exception]:
        return self.payload.result()


class CMCHeader(Header):
    """Header is fixed size(6+8+9+9 = 32 bytes) bytes in format

      header: <ID>:<'SUCCESS'|'FAILURE'>:<HINT>:<SIZE>:
      ID   - 5 bytes protocol id, "base0" at the start
      HINT - 8 bytes ascii text. Arbitrary data, usually some error info
      SIZE - 8 bytes text 0..9

    Example:
        b"base0:SUCCESS:        :12345678:"

    This is first(transport) layer protocol.
    Used to
    - transmit data (as opaque payload) from fetcher through Microcore to the checker.
    - provide centralized logging facility if the field severity is not empty
    ATTENTION: This protocol must 100% of time synchronised with microcore code.
    """
    class State(str, enum.Enum):
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"
        WAITING = "WAITING"

    fmt = "{:<5}:{:<7}:{:<8}:{:<8}:"
    length = 32

    def __init__(
        self,
        name: str,
        state: Union['CMCHeader.State', str],
        severity: str,
        payload_length: int,
    ) -> None:
        self.name = name
        self.state = CMCHeader.State(state) if isinstance(state, str) else state
        self.severity = severity  # contains either log_level or empty field
        self.payload_length = payload_length

    def __repr__(self) -> str:
        return "%s(%r, %r, %r, %r)" % (
            type(self).__name__,
            self.name,
            self.state,
            self.severity,
            self.payload_length,
        )

    def __len__(self) -> int:
        return CMCHeader.length

    # E0308: false positive, see https://github.com/PyCQA/pylint/issues/3599
    def __bytes__(self) -> bytes:  # pylint: disable=E0308
        return CMCHeader.fmt.format(
            self.name[:5],
            self.state[:7],
            self.severity[:8],
            self.payload_length,
        ).encode("ascii")

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CMCHeader':
        try:
            # to simplify parsing we are using ':' as a splitter
            name, state, hint, payload_length = data[:CMCHeader.length].split(b":")[:4]
            return cls(
                name.decode("ascii"),
                state.decode("ascii"),
                hint.decode("ascii"),
                int(payload_length.decode("ascii"), base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self) -> 'CMCHeader':
        return CMCHeader(self.name, self.state, self.severity, self.payload_length)

    @staticmethod
    def default_protocol_name() -> str:
        return "fetch"


def make_payload_answer(*messages: FetcherMessage) -> bytes:
    """ Provides valid binary payload to be send from fetcher to checker"""
    payload = b"".join(bytes(msg) for msg in messages)
    return CMCHeader(
        name=CMCHeader.default_protocol_name(),
        state=CMCHeader.State.SUCCESS,
        severity=" ",
        payload_length=len(payload),
    ) + payload


def make_logging_answer(message: str, log_level: CmcLogLevel) -> bytes:
    """ Logs data using logging facility of the microcore """
    return CMCHeader(
        name=CMCHeader.default_protocol_name(),
        state=CMCHeader.State.FAILURE,
        severity=log_level,
        payload_length=len(message),
    ) + message.encode("utf-8")


def make_waiting_answer() -> bytes:
    return bytes(
        CMCHeader(
            name=CMCHeader.default_protocol_name(),
            state=CMCHeader.State.WAITING,
            severity=" ",
            payload_length=0,
        ))


def _disable_timeout() -> None:
    """ Disable alarming and remove any running alarms"""

    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    signal.alarm(0)


def _enable_timeout(timeout: int) -> None:
    """ Raises MKTimeout exception after timeout seconds"""
    def _handler(signum: int, frame: Optional[FrameType]) -> None:
        raise MKTimeout("Fetcher timed out")

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout)


@contextlib.contextmanager
def timeout_control(timeout: int) -> Iterator[None]:
    _enable_timeout(timeout)
    try:
        yield
    finally:
        _disable_timeout()


class Command(NamedTuple):
    serial: ConfigSerial
    host_name: HostName
    mode: Mode
    timeout: int

    @staticmethod
    def from_str(command: str) -> "Command":
        raw_serial, host_name, mode_name, timeout = command.split(sep=";", maxsplit=3)
        return Command(
            serial=ConfigSerial(raw_serial),
            host_name=host_name,
            mode=Mode.CHECKING if mode_name == "checking" else Mode.DISCOVERY,
            timeout=int(timeout),
        )


def process_command(command: Command) -> None:
    with _confirm_command_processed():
        load_global_config(command.serial)
        run_fetchers(**command._asdict())


@contextlib.contextmanager
def _confirm_command_processed() -> Iterator[None]:
    try:
        yield
    finally:
        log.logger.info("Command done")
        write_bytes(make_waiting_answer())


def run_fetchers(serial: ConfigSerial, host_name: HostName, mode: Mode, timeout: int) -> None:
    """Entry point from bin/fetcher"""
    # check that file is present, because lack of the file is not an error at the moment
    json_file = build_json_file_path(serial=serial, host_name=host_name)

    if not json_file.exists():
        log.logger.warning("fetcher file for host '%s' and %s is absent", host_name, serial)
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(file_name=json_file, mode=mode, timeout=timeout)


def load_global_config(serial: ConfigSerial) -> None:
    global_json_file = build_json_global_config_file_path(serial)
    if not global_json_file.exists():
        log.logger.warning("fetcher global config %s is absent", serial)
        return

    with global_json_file.open() as f:
        config = json.load(f)["fetcher_config"]
        log.logger.setLevel(config["log_level"])


def run_fetcher(entry: Dict[str, Any], mode: Mode) -> FetcherMessage:
    """ Entrypoint to obtain data from fetcher objects.    """

    try:
        fetcher_type = FetcherType[entry["fetcher_type"]]
    except KeyError as exc:
        raise RuntimeError from exc

    log.logger.debug("Executing fetcher: %s", entry["fetcher_type"])

    try:
        fetcher_params = entry["fetcher_params"]
    except KeyError as exc:
        payload = ErrorPayload(exc)
        return FetcherMessage(
            FetcherHeader(
                fetcher_type,
                PayloadType.ERROR,
                status=logging.CRITICAL,
                payload_length=len(payload),
            ),
            payload,
        )

    try:
        with fetcher_type.from_json(fetcher_params) as fetcher:
            raw_data = fetcher.fetch(mode)
    except Exception as exc:
        raw_data = ErrorResult(exc)

    return FetcherMessage.from_raw_data(raw_data, fetcher_type)


def _make_fetcher_timeout_message(fetcher_type: FetcherType, exc: MKTimeout) -> FetcherMessage:
    payload = ErrorPayload(exc)
    return FetcherMessage(
        FetcherHeader(
            fetcher_type,
            PayloadType.ERROR,
            status=logging.ERROR,
            payload_length=len(payload),
        ),
        payload,
    )


def _run_fetchers_from_file(file_name: Path, mode: Mode, timeout: int) -> None:
    """ Writes to the stdio next data:
    Count Type            Content                     Action
    ----- -----           -------                     ------
    1     Success Answer  Fetcher Blob                Send to the checker
    0..n  Failure Answer  Exception of failed fetcher Log
    1     Waiting Answer  empty                       End IO
    *) Fetcher blob contains all answers from all fetcher objects including failed
    **) file_name is serial/host_name.json
    ***) timeout is not used at the moment"""
    with file_name.open() as f:
        data = json.load(f)

    fetchers = data["fetchers"]

    # CONTEXT: AT the moment we call fetcher-executors sequentially (due to different reasons).
    # Possibilities:
    # Sequential: slow fetcher may block other fetchers.
    # Asyncio: every fetcher must be asyncio-aware. This is ok, but even estimation requires time
    # Threading: some fetcher may be not thread safe(snmp, for example). May be dangerous.
    # Multiprocessing: CPU and memory(at least in terms of kernel) hungry. Also duplicates
    # functionality of the Microcore.

    messages: List[FetcherMessage] = []
    with timeout_control(timeout):
        try:
            # fill as many messages as possible before timeout exception raised
            for entry in fetchers:
                messages.append(run_fetcher(entry, mode))
        except MKTimeout as exc:
            # fill missing entries with timeout errors
            messages.extend([
                _make_fetcher_timeout_message(FetcherType[entry["fetcher_type"]], exc)
                for entry in fetchers[len(messages):]
            ])

    log.logger.debug("Produced %d messages:", len(messages))
    for message in messages:
        log.logger.debug("  message: %s", message.header)

    write_bytes(make_payload_answer(*messages))
    for msg in filter(
            lambda msg: msg.header.payload_type is PayloadType.ERROR,
            messages,
    ):
        log.logger.log(msg.header.status, "Error in %s fetcher: %s", msg.header.fetcher_type.name,
                       msg.raw_data.error)


def read_json_file(serial: ConfigSerial, host_name: HostName) -> str:
    json_file = build_json_file_path(serial=serial, host_name=host_name)
    return json_file.read_text(encoding="utf-8")


def build_json_file_path(serial: ConfigSerial, host_name: HostName) -> Path:
    return Path(core_helper_config_dir, serial, "fetchers", "hosts", f"{host_name}.json")


def build_json_global_config_file_path(serial: ConfigSerial) -> Path:
    return Path(core_helper_config_dir, serial, "fetchers", "global_config.json")


# Idea is based on the cmk method:
# We are writing to non-blocking socket, because simple sys.stdout.write requires flushing
# and flushing is not always appropriate. fd is fixed by design: stdout is always 1 and microcore
# receives data from stdout
def write_bytes(data: bytes) -> None:
    while data:
        bytes_written = os.write(1, data)
        data = data[bytes_written:]
        # TODO (ml): We need improve performance - 100% CPU load if Microcore is busy
