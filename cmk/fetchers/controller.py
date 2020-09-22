#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Protocol fetcher -> core: <header><payload>

import enum
import json
import os
import struct
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Final, Union

from cmk.utils.paths import core_helper_config_dir
from cmk.utils.type_defs import HostName, Result, SectionName, ConfigSerial
import cmk.utils.log as log

from cmk.snmplib.type_defs import AbstractRawData

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


class PayloadType(enum.Enum):
    ERROR = enum.auto()
    AGENT = enum.auto()
    SNMP = enum.auto()


class FetcherHeader:
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

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, (FetcherHeader, bytes)):
            return NotImplemented
        return bytes(self) == bytes(other)

    def __hash__(self) -> int:
        return hash(bytes(self))

    def __add__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(self) + bytes(other)
        return NotImplemented

    def __radd__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(other) + bytes(self)
        return NotImplemented

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


class FetcherMessage:
    def __init__(
        self,
        header: FetcherHeader,
        payload: bytes,
    ) -> None:
        self.header: Final[FetcherHeader] = header
        self.payload: Final[bytes] = payload

    def __repr__(self) -> str:
        return "%s(%r, %r)" % (type(self).__name__, self.header, self.payload)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, (FetcherMessage, bytes)):
            return NotImplemented
        return bytes(self) == bytes(other)

    def __hash__(self) -> int:
        return hash((self.header, self.payload))

    def __add__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(self) + bytes(other)
        return NotImplemented

    def __radd__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(other) + bytes(self)
        return NotImplemented

    def __len__(self) -> int:
        return len(bytes(self))

    def __bytes__(self) -> bytes:
        return self.header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "FetcherMessage":
        header = FetcherHeader.from_bytes(data)
        payload = data[len(header):len(header) + header.payload_length]
        return cls(header, payload)

    @classmethod
    def from_raw_data(
        cls,
        raw_data: Result[AbstractRawData, Exception],
        fetcher_type: FetcherType,
    ) -> "FetcherMessage":
        if raw_data.is_error():
            payload = repr(raw_data.error).encode("utf-8")
            return cls(
                FetcherHeader(
                    fetcher_type,
                    payload_type=PayloadType.ERROR,
                    status=50,
                    payload_length=len(payload),
                ),
                payload,
            )

        if fetcher_type is FetcherType.SNMP:
            assert isinstance(raw_data.ok, dict)
            payload = json.dumps({str(k): v for k, v in raw_data.ok.items()}).encode("utf8")
            return cls(
                FetcherHeader(
                    fetcher_type,
                    payload_type=PayloadType.SNMP,
                    status=0,
                    payload_length=len(payload),
                ),
                payload,
            )

        assert isinstance(raw_data.ok, bytes)
        return cls(
            FetcherHeader(
                fetcher_type,
                payload_type=PayloadType.AGENT,
                status=0,
                payload_length=len(raw_data.ok),
            ),
            raw_data.ok,
        )

    @property
    def raw_data(self) -> Result[AbstractRawData, Exception]:
        if self.header.payload_type is PayloadType.ERROR:
            try:
                # TODO(ml): This is brittle.
                return Result.Error(eval(self.payload.decode("utf8")))
            except Exception:
                return Result.Error(Exception(self.payload.decode("utf8")))
        if self.header.payload_type is PayloadType.SNMP:
            return Result.OK({SectionName(k): v for k, v in json.loads(self.payload).items()})
        return Result.OK(self.payload)


class Header:
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

    def __init__(self, name: str, state: Union['Header.State', str], severity: str,
                 payload_length: int) -> None:
        self.name = name
        self.state = Header.State(state) if isinstance(state, str) else state
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

    # E0308: false positive, see https://github.com/PyCQA/pylint/issues/3599
    def __bytes__(self) -> bytes:  # pylint: disable=E0308
        return Header.fmt.format(self.name[:5], self.state[:7], self.severity[:8],
                                 self.payload_length).encode("ascii")

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, (Header, bytes)):
            return NotImplemented
        return bytes(self) == bytes(other)

    def __hash__(self) -> int:
        return hash(bytes(self))

    def __add__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(self) + bytes(other)
        return NotImplemented

    def __radd__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(other) + bytes(self)
        return NotImplemented

    def __len__(self) -> int:
        return Header.length

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Header':
        try:
            # to simplify parsing we are using ':' as a splitter
            name, state, hint, payload_length = data[:Header.length].split(b":")[:4]
            return cls(
                name.decode("ascii"),
                state.decode("ascii"),
                hint.decode("ascii"),
                int(payload_length.decode("ascii"), base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self) -> 'Header':
        return Header(self.name, self.state, self.severity, self.payload_length)

    @staticmethod
    def default_protocol_name() -> str:
        return "fetch"


def make_payload_answer(*messages: FetcherMessage) -> bytes:
    """ Provides valid binary payload to be send from fetcher to checker"""
    payload = b"".join(bytes(msg) for msg in messages)
    return Header(
        name=Header.default_protocol_name(),
        state=Header.State.SUCCESS,
        severity=" ",
        payload_length=len(payload),
    ) + payload


def make_logging_answer(message: str, log_level: CmcLogLevel) -> bytes:
    """ Logs data using logging facility of the microcore """
    return Header(
        name=Header.default_protocol_name(),
        state=Header.State.FAILURE,
        severity=log_level,
        payload_length=len(message),
    ) + message.encode("utf-8")


def make_waiting_answer() -> bytes:
    return bytes(
        Header(
            name=Header.default_protocol_name(),
            state=Header.State.WAITING,
            severity=" ",
            payload_length=0,
        ))


def run_fetchers(serial: ConfigSerial, host_name: HostName, mode: Mode, timeout: int) -> None:
    """Entry point from bin/fetcher"""
    # check that file is present, because lack of the file is not an error at the moment
    json_file = build_json_file_path(serial=serial, host_name=host_name)

    if not json_file.exists():
        # this happens during development(or filesystem is broken)
        msg = f"fetcher file for host '{host_name}' and {serial} is absent"
        write_bytes(make_logging_answer(msg, log_level=CmcLogLevel.WARNING))
        write_bytes(make_waiting_answer())
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(file_name=json_file, mode=mode, timeout=timeout)


def load_global_config(serial: ConfigSerial) -> None:
    global_json_file = build_json_global_config_file_path(serial)
    if not global_json_file.exists():
        # this happens during development(or filesystem is broken)
        msg = f"fetcher global config {serial} is absent"
        write_bytes(make_logging_answer(msg, log_level=CmcLogLevel.WARNING))
        write_bytes(make_waiting_answer())
        return

    with global_json_file.open() as f:
        config = json.load(f)["fetcher_config"]
        log.logger.setLevel(config["log_level"])


def run_fetcher(entry: Dict[str, Any], mode: Mode, timeout: int) -> FetcherMessage:
    """ timeout to be used by concrete fetcher implementation.
    This is important entrypoint to obtain data from fetcher objects.
    """

    try:
        fetcher_type = FetcherType[entry["fetcher_type"]]
    except KeyError as exc:
        raise RuntimeError from exc

    try:
        fetcher_params = entry["fetcher_params"]
    except KeyError as exc:
        payload = repr(exc).encode("utf8")
        return FetcherMessage(
            FetcherHeader(
                fetcher_type,
                PayloadType.ERROR,
                status=50,
                payload_length=len(payload),
            ),
            payload,
        )

    with fetcher_type.from_json(fetcher_params) as fetcher:
        raw_data = fetcher.fetch(mode)

    return FetcherMessage.from_raw_data(raw_data, fetcher_type)


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
    messages = [run_fetcher(entry, mode, timeout) for entry in fetchers]
    write_bytes(make_payload_answer(*messages))
    for msg in filter(
            lambda msg: msg.header.payload_type is PayloadType.ERROR,
            messages,
    ):
        # Errors generated by fetchers will be logged by Microcore
        write_bytes(
            make_logging_answer(
                "{!s}: {!r}".format(msg.header, msg.raw_data.error),
                log_level=cmc_log_level_from_python(msg.header.status),
            ))

    write_bytes(make_waiting_answer())


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
