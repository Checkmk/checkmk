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
import logging
from pathlib import Path
from typing import Any, Dict, Union

from cmk.utils.paths import core_fetcher_config_dir
from cmk.utils.type_defs import HostName
import cmk.utils.log as log

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


class FetcherHeader:
    """Header is fixed size(16+8+8 = 32 bytes) bytes in format

      header: <NAME>:<STATUS>:<SIZE>:
      NAME   - fetcher name, for example TCP
      STATUS - error code. ) or 50 or ...
      SIZE   - 8 bytes 0..9

    Example:
        "TCP        :0       :12345678:"

    This is second(application) layer protocol and used to transmit results
    from the fetcher to the checker.
    Header.payload must be encoded with this protocol
    """
    fmt = "{:<15}:{:<7}:{:<7}:"
    length = 32

    def __init__(
        self,
        name: str,
        *,
        status: int,
        payload_length: int,
    ) -> None:
        self.name = name
        self.status = status
        self.payload_length = payload_length

    def __repr__(self) -> str:
        return "%s(%r, %r, %r)" % (
            type(self).__name__,
            self.name,
            self.status,
            self.payload_length,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, (FetcherHeader, bytes)):
            return NotImplemented
        return bytes(self) == bytes(other)

    def __hash__(self) -> int:
        return hash(bytes(self))

    def __len__(self) -> int:
        return FetcherHeader.length

    # E0308: false positive, see https://github.com/PyCQA/pylint/issues/3599
    def __bytes__(self) -> bytes:  # pylint: disable=E0308
        return FetcherHeader.fmt.format(
            self.name[:15],
            self.status,
            self.payload_length,
        ).encode("ascii")

    @classmethod
    def from_network(cls, data: bytes) -> 'FetcherHeader':
        try:
            # to simplify parsing we are using ':' as a splitter
            name, status, payload_length = data[:FetcherHeader.length].split(b":")[:3]
            return cls(
                name.decode("ascii"),
                status=int(status.decode("ascii"), base=10),
                payload_length=int(payload_length.decode("ascii"), base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self) -> 'FetcherHeader':
        return FetcherHeader(self.name, status=self.status, payload_length=self.payload_length)


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

    def __len__(self) -> int:
        return Header.length

    @classmethod
    def from_network(cls, data: bytes) -> 'Header':
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


def make_payload_answer(data: bytes) -> bytes:
    """ Provides valid binary payload to be send from fetcher to checker"""
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.SUCCESS,
               severity=" ",
               payload_length=len(data))) + data


def make_logging_answer(message: str, log_level: CmcLogLevel) -> bytes:
    """ Logs data using logging facility of the microcore """
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.FAILURE,
               severity=log_level,
               payload_length=len(message))) + message.encode("utf-8")


def make_waiting_answer() -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.WAITING,
               severity=" ",
               payload_length=0))


def run_fetchers(serial: str, host_name: HostName, mode: Mode, timeout: int) -> None:
    """Entry point from bin/fetcher"""
    # check that file is present, because lack of the file is not an error at the moment
    json_file = build_json_file_path(serial=serial, host_name=host_name)

    if not json_file.exists():
        # this happens during development(or filesystem is broken)
        text = f"fetcher file for host '{host_name}' and {serial} is absent"
        write_bytes(make_logging_answer(text, log_level=CmcLogLevel.WARNING))
        write_bytes(make_waiting_answer())
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(file_name=json_file, mode=mode, timeout=timeout)


def load_global_config(serial: int) -> None:
    global_json_file = build_json_global_config_file_path(serial=str(serial))
    if not global_json_file.exists():
        # this happens during development(or filesystem is broken)
        text = f"fetcher global config {serial} is absent"
        write_bytes(make_logging_answer(text, log_level=CmcLogLevel.WARNING))
        write_bytes(make_waiting_answer())
        return

    with global_json_file.open() as f:
        result = json.load(f)["fetcher_config"]
        log.logger.setLevel(result["log_level"])


def run_fetcher(entry: Dict[str, Any], mode: Mode, timeout: int) -> bytes:
    """ timeout to be used by concrete fetcher implementation.
    This is important entrypoint to obtain data from fetcher objects.
    """

    try:
        fetcher_type = entry["fetcher_type"]
    except LookupError as exc:
        raise RuntimeError from exc  # proposition from ml/sk to avoid stupid exception

    try:
        fetcher_params = entry["fetcher_params"]

        with FetcherType[fetcher_type].from_json(fetcher_params) as fetcher:
            fetcher_data = fetcher.fetch(mode)

        # TODO (sk): Change encoding approach:
        # Below is weak code, which breaks isolation. It has been left just to keep things running.
        # In fact, to correctly encode data we must estimate not the fetcher name but the data type.
        # We do not know anything about relation between fetcher and data, but we certainly know
        # how to encode different data types.
        if fetcher_type == "SNMP":
            # Keys of SNMP payload is of type SectionName which can not be encoded using JSON.
            snmp_fetcher_data = {"%s" % k: v for k, v in fetcher_data.items()}
            payload = json.dumps(snmp_fetcher_data).encode("utf-8")
        else:
            payload = fetcher_data

        fh = FetcherHeader(fetcher_type, status=0, payload_length=len(payload))
        return bytes(fh) + payload

    except Exception as e:
        # NOTE. The exception is too broad by design:
        # we need specs for Exception coming from fetchers(and how to process)
        payload = repr(e).encode("utf-8")
        fh = FetcherHeader(fetcher_type, status=50, payload_length=len(payload))
        return bytes(fh) + payload


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

    resulting_blob = [run_fetcher(entry, mode, timeout) for entry in fetchers]

    write_bytes(make_payload_answer(b''.join(resulting_blob)))

    for entry in resulting_blob:
        fh = FetcherHeader.from_network(entry)
        status = fh.status
        if status == 0:
            continue

        # Errors generated by fetchers will be logged by Microcore
        write_bytes(
            make_logging_answer(fh.name + ": " + entry[FetcherHeader.length:].decode("utf-8"),
                                log_level=cmc_log_level_from_python(status)))

    write_bytes(make_waiting_answer())


def read_json_file(serial: str, host_name: HostName) -> str:
    json_file = build_json_file_path(serial=serial, host_name=host_name)
    return json_file.read_text(encoding="utf-8")


def build_json_file_path(serial: str, host_name: HostName) -> Path:
    return Path("{}/{}/{}.json".format(core_fetcher_config_dir, serial, host_name))


def build_json_global_config_file_path(serial: str) -> Path:
    return Path("{}/{}/global_config.json".format(core_fetcher_config_dir, serial))


# Idea is based on the cmk method:
# We are writing to non-blocking socket, because simple sys.stdout.write requires flushing
# and flushing is not always appropriate. fd is fixed by design: stdout is always 1 and microcore
# receives data from stdout
def write_bytes(data: bytes) -> None:
    while data:
        bytes_written = os.write(1, data)
        data = data[bytes_written:]
        # TODO (ml): We need improve performance - 100% CPU load if Microcore is busy
