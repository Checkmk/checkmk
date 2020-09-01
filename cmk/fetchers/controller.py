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
from pathlib import Path
from typing import Any, Dict, Final, NamedTuple, Union

from cmk.utils.paths import core_fetcher_config_dir
from cmk.utils.type_defs import HostName, SectionName
import cmk.utils.log

from cmk.snmplib.type_defs import AbstractRawData

from . import FetcherType

__all__ = [
    "FetcherHeader",
    "FetcherMessage",
    "Header",
    "make_success_answer",
    "make_failure_answer",
    "make_waiting_answer",
]

#
# Protocols
#


class FetcherHeader:
    """Header is fixed size(16+8+8 = 32 bytes) bytes in format

      header: <TYPE>:<STATUS>:<SIZE>:
      TYPE   - fetcher type, see FetcherType
      STATUS - error code. ) or 50 or ...
      SIZE   - 8 bytes string 0..9

    Example:
        "TCP        :0       :12345678:"

    used to transmit results of the fetcher to checker
    """
    fmt = "{:<15}:{:<7}:{:<7}:"
    length = 32

    def __init__(
        self,
        type_: FetcherType,
        *,
        status: int,
        payload_length: int,
    ) -> None:
        self.type: Final[FetcherType] = type_
        self.status: Final[int] = status
        self.payload_length: Final[int] = payload_length

    def __repr__(self) -> str:
        return "%s(%r, %r, %r)" % (
            type(self).__name__,
            self.type,
            self.status,
            self.payload_length,
        )

    def __str__(self) -> str:
        return FetcherHeader.fmt.format(self.type.name[:15], self.status, self.payload_length)

    def __bytes__(self) -> bytes:  # pylint: disable=E0308
        # E0308: false positive, see https://github.com/PyCQA/pylint/issues/3599
        return str(self).encode("ascii")

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def __len__(self) -> int:
        return FetcherHeader.length

    @classmethod
    def from_network(cls, data: bytes) -> 'FetcherHeader':
        try:
            # to simplify parsing we are using ':' as a splitter
            type_, status, payload_length = data[:FetcherHeader.length].split(b":")[:3]
            return cls(
                FetcherType[type_.decode("ascii").strip()],
                status=int(status, base=10),
                payload_length=int(payload_length, base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def dump(self, payload: bytes) -> bytes:
        return bytes(self) + payload

    def clone(self) -> 'FetcherHeader':
        return FetcherHeader(self.type, status=self.status, payload_length=self.payload_length)


# TODO(ml): Is this type really necessary?
class FetcherMessage(NamedTuple("FetcherMessage", [
    ("header", FetcherHeader),
    ("payload", bytes),
])):
    def raw_data(self) -> AbstractRawData:
        if self.header.type is FetcherType.SNMP:
            return {SectionName(k): v for k, v in json.loads(self.payload)}
        return self.payload


class Header:
    """Header is fixed size(6+8+9+9 = 32 bytes) string in format

      header: <ID>:<'SUCCESS'|'FAILURE'>:<HINT>:<SIZE>:
      ID   - 5 bytes protocol id, "base0" at the start
      HINT - 8 bytes string. Arbitrary data, usually some error info
      SIZE - 8 bytes string 0..9

    Example:
        "base0:SUCCESS:        :12345678:"

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
        state: Union['Header.State', str],
        severity: str,
        payload_length: int,
    ) -> None:
        self.name = name
        self.state = Header.State(state) if isinstance(state, str) else state
        self.severity = severity
        self.payload_length = payload_length

    def __repr__(self) -> str:
        return "%s(%r, %r, %r, %r)" % (
            type(self).__name__,
            self.name,
            self.state,
            self.severity,
            self.payload_length,
        )

    def __str__(self) -> str:
        return Header.fmt.format(
            self.name[:5],
            self.state[:7],
            self.severity[:8],
            self.payload_length,
        )

    def __bytes__(self) -> bytes:  # pylint: disable=E0308
        # E0308: false positive, see https://github.com/PyCQA/pylint/issues/3599
        return str(self).encode("ascii")

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def __len__(self) -> int:
        return Header.length

    @classmethod
    def from_network(cls, data: bytes) -> 'Header':
        try:
            # to simplify parsing we are using ':' as a splitter
            name, state, severity, payload_length = data[:Header.length].split(b":")[:4]
            return cls(
                name.decode("ascii"),
                state.decode("ascii"),
                severity.decode("ascii"),
                int(payload_length, base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self) -> 'Header':
        return Header(self.name, self.state, self.severity, self.payload_length)

    def dump(self, payload: bytes) -> bytes:
        return bytes(self) + payload

    @staticmethod
    def default_protocol_name() -> str:
        return "fetch"


def make_success_answer(data: bytes) -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.SUCCESS,
               severity=" ",
               payload_length=len(data))) + data


def make_failure_answer(data: bytes, *, severity: str) -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.FAILURE,
               severity=severity,
               payload_length=len(data))) + data


def make_waiting_answer() -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.WAITING,
               severity=" ",
               payload_length=0))


# NOTE: This function is not stub, but simplified
def run_fetchers(serial: str, host_name: HostName, timeout: int) -> None:
    # check that file is present, because lack of the file is not an error at the moment
    json_file = build_json_file_path(serial=serial, host_name=host_name)

    if not json_file.exists():
        # this happens during development(or filesystem is broken)
        data = f"fetcher file for host '{host_name}' and {serial} is absent".encode("utf8")
        write_data(make_success_answer(data))
        write_data(make_failure_answer(data, severity="warning"))
        write_data(make_waiting_answer())
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(file_name=json_file, timeout=timeout)


def load_global_config(serial: int) -> None:
    global_json_file = build_json_global_config_file_path(serial=str(serial))
    if not global_json_file.exists():
        # this happens during development(or filesystem is broken)
        data = f"fetcher global config {serial} is absent".encode("utf8")
        write_data(make_success_answer(data))
        write_data(make_failure_answer(data, severity="warning"))
        write_data(make_waiting_answer())
        return

    with global_json_file.open() as f:
        result = json.load(f)["fetcher_config"]
        cmk.utils.log.logger.setLevel(result["log_level"])


def _run_fetcher(entry: Dict[str, Any], timeout: int) -> FetcherMessage:
    """Fetch and serialize the raw data."""
    try:
        fetcher_type = FetcherType[entry["fetcher_type"]]
        fetcher_params = entry["fetcher_params"]

        with fetcher_type.from_json(fetcher_params) as fetcher:
            fetcher_data = fetcher.fetch()

        payload: bytes
        if fetcher_type is FetcherType.SNMP:
            payload = json.dumps({str(k): v for k, v in fetcher_data.items()}).encode("utf-8")
        else:
            assert isinstance(fetcher_data, bytes)
            payload = fetcher_data

        return FetcherMessage(
            FetcherHeader(
                fetcher_type,
                status=0,
                payload_length=len(payload),
            ),
            payload,
        )

    except Exception as exc:
        # NOTE. The exception is too broad by design:
        # we need specs for Exception coming from fetchers(and how to process)
        payload = repr(exc).encode("utf-8")
        return FetcherMessage(
            FetcherHeader(
                fetcher_type,
                status=50,  # CRITICAL, see _level.py
                payload_length=len(payload),
            ),
            payload,
        )


def status_to_microcore_severity(status: int) -> str:
    # TODO(ml): That could/should be an enum called Severity.
    try:
        return {
            50: "critical",
            40: "error",
            30: "warning",
            20: "info",
            15: "info",
            10: "debug",
        }[status]
    except KeyError:
        return "warning"


def _run_fetchers_from_file(file_name: Path, timeout: int) -> None:
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

    for header, payload in (_run_fetcher(entry, timeout) for entry in fetchers):
        write_data(header.dump(payload))
        if header.status != 0:
            # Let Microcore log errors.
            write_data(
                make_failure_answer(
                    data=header.dump(payload),
                    severity=status_to_microcore_severity(header.status),
                ))

    write_data(make_waiting_answer())


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
def write_data(data: bytes) -> None:
    while data:
        bytes_written = os.write(1, data)
        data = data[bytes_written:]
        # TODO (ml): We need improve performance - 100% CPU load if Microcore is busy
