#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import json
import logging
import os
import signal
from pathlib import Path
from types import FrameType
from typing import Any, Dict, Iterator, List, NamedTuple, Optional

import cmk.utils.cleanup
import cmk.utils.paths as paths
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import MKTimeout
from cmk.utils.type_defs import ConfigSerial, HostName, result

from . import FetcherType, protocol
from .type_defs import Mode

logger = logging.getLogger("cmk.helper")


class GlobalConfig(NamedTuple):
    cmc_log_level: int

    @property
    def log_level(self) -> int:
        """A Python log level such as logging.DEBUG, Logging.INFO, etc.

        See Also:
            Comments in `cmk.utils.log._level`.

        """
        return {
            0: logging.CRITICAL,  # emergency
            1: logging.CRITICAL,  # alert
            2: logging.CRITICAL,  # critical
            3: logging.ERROR,  #  error
            4: logging.WARNING,  # warning
            5: logging.WARNING,  # notice
            6: logging.INFO,  # informational
            7: logging.DEBUG,  # debug
        }[self.cmc_log_level]

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "GlobalConfig":
        try:
            return cls(serialized["fetcher_config"]["cmc_log_level"])
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Dict[str, Any]:
        return {"fetcher_config": {"cmc_log_level": self.cmc_log_level}}


def _disable_timeout() -> None:
    """ Disable alarming and remove any running alarms"""

    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    signal.alarm(0)


def _enable_timeout(timeout: int) -> None:
    """ Raises MKTimeout exception after timeout seconds"""
    def _handler(signum: int, frame: Optional[FrameType]) -> None:
        raise MKTimeout(f"Fetcher timed out after {timeout} seconds")

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
        global_config = load_global_config(command.serial)
        logger.setLevel(global_config.log_level)
        run_fetchers(**command._asdict())


@contextlib.contextmanager
def _confirm_command_processed() -> Iterator[None]:
    try:
        yield
    finally:
        logger.info("Command done")
        write_bytes(protocol.make_end_of_reply_answer())


def run_fetchers(serial: ConfigSerial, host_name: HostName, mode: Mode, timeout: int) -> None:
    """Entry point from bin/fetcher"""
    # check that file is present, because lack of the file is not an error at the moment
    local_config_path = make_local_config_path(serial=serial, host_name=host_name)

    if not local_config_path.exists():
        logger.warning("fetcher file for host %r and %s is absent", host_name, serial)
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(file_name=local_config_path, mode=mode, timeout=timeout)

    # Cleanup different things (like object specific caches)
    cmk.utils.cleanup.cleanup_globals()


def load_global_config(serial: ConfigSerial) -> GlobalConfig:
    try:
        with make_global_config_path(serial).open() as f:
            return GlobalConfig.deserialize(json.load(f))
    except FileNotFoundError:
        logger.warning("fetcher global config %s is absent", serial)
        return GlobalConfig(cmc_log_level=5)


def run_fetcher(entry: Dict[str, Any], mode: Mode) -> protocol.FetcherMessage:
    """ Entrypoint to obtain data from fetcher objects.    """

    try:
        fetcher_type = FetcherType[entry["fetcher_type"]]
    except KeyError as exc:
        raise RuntimeError from exc

    logger.debug("Executing fetcher: %s", entry["fetcher_type"])

    try:
        fetcher_params = entry["fetcher_params"]
    except KeyError as exc:
        return protocol.make_error_message(fetcher_type, exc)

    try:
        with CPUTracker() as tracker, fetcher_type.from_json(fetcher_params) as fetcher:
            raw_data = fetcher.fetch(mode)
    except Exception as exc:
        raw_data = result.Error(exc)

    return protocol.FetcherMessage.from_raw_data(
        raw_data,
        tracker.duration,
        fetcher_type,
    )


def _run_fetchers_from_file(file_name: Path, mode: Mode, timeout: int) -> None:
    """ Writes to the stdio next data:
    Count Answer        Content               Action
    ----- ------        -------               ------
    1     Result        Fetcher Blob          Send to the checker
    0..n  Log           Message to be logged  Log
    1     End of reply  empty                 End IO
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

    messages: List[protocol.FetcherMessage] = []
    with timeout_control(timeout):
        try:
            # fill as many messages as possible before timeout exception raised
            for entry in fetchers:
                messages.append(run_fetcher(entry, mode))
        except MKTimeout as exc:
            # fill missing entries with timeout errors
            messages.extend([
                protocol.make_fetcher_timeout_message(
                    FetcherType[entry["fetcher_type"]],
                    exc,
                    Snapshot.null(),
                ) for entry in fetchers[len(messages):]
            ])

    logger.debug("Produced %d messages", len(messages))
    write_bytes(protocol.make_result_answer(*messages))
    for msg in filter(
            lambda msg: msg.header.payload_type is protocol.PayloadType.ERROR,
            messages,
    ):
        logger.log(msg.header.status, "Error in %s fetcher: %s", msg.header.fetcher_type.name,
                   msg.raw_data.error)


def make_local_config_path(serial: ConfigSerial, host_name: HostName) -> Path:
    return paths.make_fetchers_config_path(serial) / "hosts" / f"{host_name}.json"


def make_global_config_path(serial: ConfigSerial) -> Path:
    return paths.make_fetchers_config_path(serial) / "global_config.json"


# Idea is based on the cmk method:
# We are writing to non-blocking socket, because simple sys.stdout.write requires flushing
# and flushing is not always appropriate. fd is fixed by design: stdout is always 1 and microcore
# receives data from stdout
def write_bytes(data: bytes) -> None:
    while data:
        bytes_written = os.write(1, data)
        data = data[bytes_written:]
        # TODO (ml): We need improve performance - 100% CPU load if Microcore is busy
