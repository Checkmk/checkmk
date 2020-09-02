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
from typing import Any, Dict, Final, NamedTuple

from cmk.utils.paths import core_fetcher_config_dir
from cmk.utils.type_defs import HostName, SectionName
import cmk.utils.log

from cmk.snmplib.type_defs import AbstractRawData

from . import FetcherType

__all__ = [
    "FetcherMessage",
    "Header",
    "make_success_answer",
    "make_failure_answer",
    "make_waiting_answer",
]

#
# Protocols
#


class Header:
    """Header is fixed size 40 bytes string in format

      header: <NAME>:<STATUS>:<HINT>:<SIZE>:

      NAME    -  5 bytes protocol id, "fetch" at the start
      STATUS  -  8 bytes
      HINT    - 15 bytes string. Arbitrary data, usually some error info
      SIZE    -  8 bytes string 0..9

    Example:
        "fetch:SUCCESS:                :12345678:"

    """
    class State(str, enum.Enum):
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"
        WAITING = "WAITING"

    fmt = "{:<5}:{:<8}:{:<15}:{:<8}:"
    length = 40

    def __init__(
        self,
        *,
        name: str,
        state: str,
        hint: str,
        payload_length: int,
    ) -> None:
        self.name: Final[str] = name
        self.state: Final[str] = state
        self.hint: Final[str] = hint
        self.payload_length: Final[int] = payload_length

    def __repr__(self) -> str:
        return "%s(%r, %r, %r, %r)" % (
            type(self).__name__,
            self.name,
            self.state,
            self.hint,
            self.payload_length,
        )

    def __str__(self) -> str:
        return Header.fmt.format(
            self.name[:5],
            self.state[:8],
            self.hint[:15],
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
            name, state, hint, payload_length = data[:Header.length].split(b":")[:4]
            return cls(
                name=name.decode("ascii"),
                state=state.decode("ascii"),
                hint=hint.decode("ascii"),
                payload_length=int(payload_length, base=10),
            )
        except ValueError as exc:
            raise ValueError(data) from exc

    def dump(self, payload: bytes) -> bytes:
        return bytes(self) + payload

    @staticmethod
    def default_protocol_name() -> str:
        return "fetch"


# TODO(ml): Is this type really necessary?
class FetcherMessage(NamedTuple("FetcherMessage", [
    ("header", Header),
    ("payload", bytes),
])):
    def raw_data(self) -> AbstractRawData:
        if self.header.hint == "SNMP":
            return {SectionName(k): v for k, v in json.loads(self.payload)}
        return self.payload


def make_success_answer(data: bytes) -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.SUCCESS,
               hint=" ",
               payload_length=len(data))) + data


def make_failure_answer(data: bytes, *, severity: str) -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.FAILURE,
               hint=severity,
               payload_length=len(data))) + data


def make_waiting_answer() -> bytes:
    return bytes(
        Header(name=Header.default_protocol_name(),
               state=Header.State.WAITING,
               hint=" ",
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
            Header(
                name="fetch",
                state=Header.State.SUCCESS,
                hint=fetcher_type.name,
                payload_length=len(payload),
            ),
            payload,
        )

    except Exception as exc:
        # NOTE. The exception is too broad by design:
        # we need specs for Exception coming from fetchers(and how to process)
        payload = repr(exc).encode("utf-8")
        return FetcherMessage(
            Header(
                name="fetch",
                state=Header.State.FAILURE,
                hint=fetcher_type.name,
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
        if header.state != Header.State.SUCCESS:
            # Let Microcore log errors.
            write_data(make_failure_answer(
                data=header.dump(payload),
                severity="critical",
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
