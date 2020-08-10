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
from typing import Any, Dict, Union

from cmk.utils.paths import core_fetcher_config_dir
from cmk.utils.type_defs import HostName

from . import FetcherType
from ._base import AbstractDataFetcher


class FetcherFactory:
    @staticmethod
    def make(fetcher_type: str, fetcher_params: Dict[str, Any]) -> AbstractDataFetcher:
        return FetcherType[fetcher_type].value.from_json(fetcher_params)


#
# At the moment Protocol and API are opened to critic.
# Base structure and API are fixed
#


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

    def __init__(self, name: str, state: Union['Header.State', str], severity: str,
                 payload_length: int) -> None:
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
        return Header.fmt.format(self.name[:5], self.state[:7], self.severity[:8],
                                 self.payload_length)

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def __len__(self) -> int:
        return Header.length

    @classmethod
    def from_network(cls, data: str) -> 'Header':
        try:
            # to simplify parsing we are using ':' as a splitter
            name, state, hint, payload_length = data[:Header.length].split(":")[:4]
            return cls(name, state, hint, int(payload_length, base=10))
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self) -> 'Header':
        return Header(self.name, self.state, self.severity, self.payload_length)

    @staticmethod
    def default_protocol_name() -> str:
        return "fetch"


def make_success_answer(data: str) -> str:
    return str(
        Header(name=Header.default_protocol_name(),
               state=Header.State.SUCCESS,
               severity=" ",
               payload_length=len(data))) + data


def make_failure_answer(data: str, *, severity: str) -> str:
    return str(
        Header(name=Header.default_protocol_name(),
               state=Header.State.FAILURE,
               severity=severity,
               payload_length=len(data))) + data


def make_waiting_answer() -> str:
    return str(
        Header(name=Header.default_protocol_name(),
               state=Header.State.WAITING,
               severity=" ",
               payload_length=0))


# NOTE: This function is not stub, but simplified
def run_fetchers(serial: str, host_name: HostName, timeout: int) -> None:
    # check that file is present, because lack of the file is not an error at the moment
    json_file = build_json_file_path(serial=serial, host_name=host_name)

    if not json_file.exists():
        write_data(make_failure_answer("fetcher file is absent", severity="warning"))
        #  we do not send waiting answer - the fetcher should be dead
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(file_name=json_file, timeout=timeout)


def _run_fetcher(entry: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """ timeout to be used by concrete fetcher implementation
    Examples of correct dictionaries to return:
    {  "fetcher_type": "snmp", "status": 0,   "payload": ""whatever}
    {  "fetcher_type": "tcp",  "status": 50,  "payload": "exception text"}
    """

    try:
        ff = FetcherFactory()
        fetcher_type = entry["fetcher_type"]
        fetcher_params = entry["fetcher_params"]
        fetcher = ff.make(fetcher_type=fetcher_type, fetcher_params=fetcher_params)
        fetcher_data = fetcher.data()

        # If data returns bytes -> decode. This is current state of development.
        # SNMP returns not a str, but raw structure. We must serialize this structure and send it.
        if isinstance(fetcher_data, bytes):
            payload = fetcher_data.decode("utf-8")
        else:
            payload = json.dumps(fetcher_data)

        return {
            "fetcher_type": fetcher_type,
            "status": 0,
            "payload": payload,
        }

    except Exception as e:
        # NOTE. The exception is too broad by design:
        # we need specs for Exception coming from fetchers(and how to process)
        return {
            "fetcher_type": fetcher_type,
            "status": 50,  # CRITICAL, see _level.py
            "payload": str(e),
        }


def _run_fetchers_from_file(file_name: Path, timeout: int) -> None:
    """ Writes to the stdio next data:
    Count Type            Content                     Action
    ----- -----           -------                     ------
    1     Success Answer  Fetcher Blob                Send to the checker
    0..n  Failure Answer  Exception of failed fetcher Log
    1     Waiting Answer  empty                       End IO
    *) Fetcher blob contains all answers from all fetcher objects including failed
    **) file_name is serial/host_name.json
    ***) timeout is niot used at the moment"""
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

    resulting_blob = [_run_fetcher(entry, timeout) for entry in fetchers]
    write_data(make_success_answer(json.dumps(resulting_blob)))

    for entry in resulting_blob:
        if entry["status"] == 0:
            continue

        # Errors generated by fetchers will be logged by Microcore
        write_data(
            make_failure_answer(data=entry["fetcher_type"] + ": " + entry["payload"],
                                severity="critical"))

    write_data(make_waiting_answer())


def read_json_file(serial: str, host_name: HostName) -> str:
    json_file = build_json_file_path(serial=serial, host_name=host_name)
    return json_file.read_text(encoding="utf-8")


def build_json_file_path(serial: str, host_name: HostName) -> Path:
    return Path("{}/{}/{}.json".format(core_fetcher_config_dir, serial, host_name))


# Idea is based on the cmk method:
# We are writing to non-blocking socket, because simple sys.stdout.write requires flushing
# and flushing is not always appropriate. fd is fixed by design: stdout is always 1 and microcore
# receives data from stdout
def write_data(data: str) -> None:
    output = data.encode("utf-8")
    while output:
        bytes_written = os.write(1, output)
        output = output[bytes_written:]
        # TODO (ml): We need improve performance - 100% CPU load if Microcore is busy
