#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, NamedTuple

import cmk.utils.cleanup
import cmk.utils.paths as paths
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.fetcher_crash_reporting import create_fetcher_crash_dump
from cmk.utils.observer import ABCResourceObserver
from cmk.utils.timeout import MKTimeout, Timeout
from cmk.utils.type_defs import ConfigSerial, HostName, result

from . import ABCFetcher, FetcherType, MaxAge, protocol
from .snmp import SNMPFetcher, SNMPPluginStore
from .type_defs import Mode

logger = logging.getLogger("cmk.helper")


class GlobalConfig(NamedTuple):
    cmc_log_level: int
    cluster_max_cachefile_age: int
    snmp_plugin_store: SNMPPluginStore

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
        fetcher_config = serialized["fetcher_config"]
        try:
            return cls(
                cmc_log_level=fetcher_config["cmc_log_level"],
                cluster_max_cachefile_age=fetcher_config["cluster_max_cachefile_age"],
                snmp_plugin_store=SNMPPluginStore.deserialize(fetcher_config["snmp_plugin_store"]),
            )
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Dict[str, Any]:
        return {
            "fetcher_config": {
                "cmc_log_level": self.cmc_log_level,
                "cluster_max_cachefile_age": self.cluster_max_cachefile_age,
                "snmp_plugin_store": self.snmp_plugin_store.serialize(),
            },
        }


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


def process_command(raw_command: str, observer: ABCResourceObserver) -> None:
    with _confirm_command_processed():
        serial: ConfigSerial = ConfigSerial("")
        host_name: HostName = ""
        try:
            command = Command.from_str(raw_command)
            serial = command.serial
            host_name = command.host_name
            global_config = load_global_config(command.serial)
            logging.getLogger().setLevel(global_config.log_level)
            SNMPFetcher.plugin_store = global_config.snmp_plugin_store
            run_fetchers(**command._asdict())
            observer.check_resources(raw_command)
        except Exception as e:
            crash_info = create_fetcher_crash_dump(serial=serial, host=host_name)
            logger.critical("Exception is '%s' (%s)", e, crash_info)
            sys.exit(15)


@contextlib.contextmanager
def _confirm_command_processed() -> Iterator[None]:
    try:
        yield
    finally:
        logger.info("Command done")
        write_bytes(bytes(protocol.CMCMessage.end_of_reply()))


def run_fetchers(serial: ConfigSerial, host_name: HostName, mode: Mode, timeout: int) -> None:
    """Entry point from bin/fetcher"""
    # check that file is present, because lack of the file is not an error at the moment
    local_config_path = make_local_config_path(serial=serial, host_name=host_name)

    if not local_config_path.exists():
        logger.warning("fetcher file for host %r and %s is absent", host_name, serial)
        return

    # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
    _run_fetchers_from_file(serial, host_name, mode=mode, timeout=timeout)

    # Cleanup different things (like object specific caches)
    cmk.utils.cleanup.cleanup_globals()


def load_global_config(serial: ConfigSerial) -> GlobalConfig:
    try:
        with make_global_config_path(serial).open() as f:
            return GlobalConfig.deserialize(json.load(f))
    except FileNotFoundError:
        logger.warning("fetcher global config %s is absent", serial)
        return GlobalConfig(
            cmc_log_level=5,
            cluster_max_cachefile_age=90,
            snmp_plugin_store=SNMPPluginStore(),
        )


def run_fetcher(fetcher: ABCFetcher, mode: Mode) -> protocol.FetcherMessage:
    """ Entrypoint to obtain data from fetcher objects.    """
    logger.debug("Executing fetcher: %s", fetcher)
    with CPUTracker() as tracker:
        try:
            with fetcher:
                raw_data = fetcher.fetch(mode)
        except Exception as exc:
            raw_data = result.Error(exc)

    return protocol.FetcherMessage.from_raw_data(
        raw_data,
        tracker.duration,
        FetcherType.from_fetcher(fetcher),
    )


def _parse_config(serial: ConfigSerial, host_name: HostName) -> Iterator[ABCFetcher]:
    with make_local_config_path(serial=serial, host_name=host_name).open() as f:
        data = json.load(f)

    if "fetchers" in data:
        yield from _parse_fetcher_config(data)
    elif "clusters" in data:
        yield from _parse_cluster_config(data, serial)
    else:
        raise LookupError("invalid config")


def _parse_fetcher_config(data: Dict[str, Any]) -> Iterator[ABCFetcher]:
    # Hard crash on parser errors: The interface is versioned and internal.
    # Crashing on error really *is* the best way to catch bonehead mistakes.
    for entry in data["fetchers"]:
        fetcher = FetcherType[entry["fetcher_type"]].from_json(entry["fetcher_params"])
        if isinstance(fetcher, SNMPFetcher):
            fetcher.file_cache.max_age = MaxAge(
                checking=fetcher.file_cache.max_age.checking,
                discovery=0,
                inventory=fetcher.file_cache.max_age.inventory,
            )

        yield fetcher


def _parse_cluster_config(data: Dict[str, Any], serial: ConfigSerial) -> Iterator[ABCFetcher]:
    global_config = load_global_config(serial)
    for host_name in data["clusters"]["nodes"]:
        for fetcher in _parse_config(serial, host_name):
            fetcher.file_cache.max_age = MaxAge(
                checking=global_config.cluster_max_cachefile_age,
                discovery=global_config.cluster_max_cachefile_age,
                inventory=2 * global_config.cluster_max_cachefile_age,
            )
            yield fetcher


def _run_fetchers_from_file(
    serial: ConfigSerial,
    host_name: HostName,
    mode: Mode,
    timeout: int,
) -> None:
    """ Writes to the stdio next data:
    Count Answer        Content               Action
    ----- ------        -------               ------
    1     Result        Fetcher Blob          Send to the checker
    0..n  Log           Message to be logged  Log
    1     End of reply  empty                 End IO

    """
    messages: List[protocol.FetcherMessage] = []
    with CPUTracker() as cpu_tracker, Timeout(
            timeout,
            message=f'Fetcher for host "{host_name}" timed out after {timeout} seconds',
    ) as timeout_manager:
        fetchers = tuple(_parse_config(serial, host_name))
        try:
            # fill as many messages as possible before timeout exception raised
            for entry in fetchers:
                messages.append(run_fetcher(entry, mode))
        except MKTimeout as exc:
            # fill missing entries with timeout errors
            messages.extend([
                protocol.FetcherMessage.timeout(
                    FetcherType.from_fetcher(fetcher),
                    exc,
                    Snapshot.null(),
                ) for fetcher in fetchers[len(messages):]
            ])

    if timeout_manager.signaled:
        messages = _replace_netsnmp_obfuscated_timeout(messages, timeout_manager.message)

    logger.debug("Produced %d messages", len(messages))
    write_bytes(bytes(protocol.CMCMessage.result_answer(
        messages,
        timeout,
        cpu_tracker.duration,
    )))
    for msg in filter(
            lambda msg: msg.header.payload_type is protocol.PayloadType.ERROR,
            messages,
    ):
        logger.log(msg.header.status, "Error in %s fetcher: %r", msg.header.fetcher_type.name,
                   msg.raw_data.error)
        logger.debug("".join(
            traceback.format_exception(
                msg.raw_data.error.__class__,
                msg.raw_data.error,
                msg.raw_data.error.__traceback__,
            )))


def _replace_netsnmp_obfuscated_timeout(messages: Iterable[protocol.FetcherMessage],
                                        timeout_msg: str) -> List[protocol.FetcherMessage]:
    return [
        protocol.FetcherMessage.timeout(
            FetcherType.SNMP,
            MKTimeout(timeout_msg),
            Snapshot.null(),
        ) if (msg.header.fetcher_type is FetcherType.SNMP and
              msg.header.payload_type is protocol.PayloadType.ERROR and
              isinstance(msg.raw_data.error, SystemError)) else msg for msg in messages
    ]


def make_local_config_path(serial: ConfigSerial, host_name: HostName) -> Path:
    return paths.make_fetchers_config_path(serial) / "hosts" / f"{host_name}.json"


def make_global_config_path(serial: ConfigSerial) -> Path:
    return paths.make_fetchers_config_path(serial) / "global_config.json"


def write_bytes(data: bytes) -> None:
    """Idea is based on the cmk method.
    Data will be received  by Microcore from a non-blocking socket, thus simple sys.stdout.write
    makes flushing mandatory, which is not always appropriate.

    1 is a file descriptor, which  is fixed by design: stdout is always 1 and microcore will
    receive data from stdout.

    The socket, we are writing in, is blocking, thus loop will not overload CPU in any case.
    """
    while data:
        bytes_written = os.write(1, data)
        data = data[bytes_written:]
