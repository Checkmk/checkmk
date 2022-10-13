#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import json
import logging
import os
import sys
import traceback
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Mapping, NamedTuple, Optional, Tuple

import cmk.utils.cleanup
from cmk.utils.config_path import ConfigPath, VersionedConfigPath
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.observer import ABCResourceObserver
from cmk.utils.timeout import MKTimeout, Timeout
from cmk.utils.type_defs import HostName, SourceType
from cmk.utils.type_defs.protocol import Serializer

from . import Fetcher, FetcherFactory, get_raw_data, protocol
from .agent import AgentFileCache, PushAgentFileCache
from .cache import FileCache, MaxAge
from .crash_reporting import create_fetcher_crash_dump
from .snmp import SNMPFetcher, SNMPFileCache, SNMPPluginStore
from .type_defs import FetcherType, Mode

logger = logging.getLogger("cmk.helper")


def make_global_config_path(config_path: ConfigPath) -> Path:
    return Path(config_path) / "fetchers" / "global_config.json"


def make_local_config_path(config_path: ConfigPath, host_name: HostName) -> Path:
    return make_local_config_dir(config_path) / f"{host_name}.json"


@lru_cache
def make_local_config_dir(config_path: ConfigPath) -> Path:
    return Path(config_path) / "fetchers" / "hosts"


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
            3: logging.ERROR,  # error
            4: logging.WARNING,  # warning
            5: logging.WARNING,  # notice
            6: logging.INFO,  # informational
            7: logging.DEBUG,  # debug
        }[self.cmc_log_level]

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "GlobalConfig":
        fetcher_config = serialized["fetcher_config"]
        return cls(
            cmc_log_level=fetcher_config["cmc_log_level"],
            cluster_max_cachefile_age=fetcher_config["cluster_max_cachefile_age"],
            snmp_plugin_store=SNMPPluginStore.deserialize(fetcher_config["snmp_plugin_store"]),
        )

    def serialize(self) -> Mapping[str, Any]:
        return {
            "fetcher_config": {
                "cmc_log_level": self.cmc_log_level,
                "cluster_max_cachefile_age": self.cluster_max_cachefile_age,
                "snmp_plugin_store": self.snmp_plugin_store.serialize(),
            },
        }


class Command(NamedTuple):
    config_path: VersionedConfigPath
    host_name: HostName
    mode: Mode
    timeout: int

    @staticmethod
    def from_str(command: str) -> "Command":
        serial, host_name, mode_name, timeout = command.split(sep=";", maxsplit=3)
        return Command(
            config_path=VersionedConfigPath(int(serial)),
            host_name=HostName(host_name),
            mode=Mode.CHECKING if mode_name == "checking" else Mode.DISCOVERY,
            timeout=int(timeout),
        )


def process_command(raw_command: str, observer: ABCResourceObserver) -> None:
    with _confirm_command_processed():
        config_path: Optional[ConfigPath] = None
        host_name: Optional[HostName] = None
        try:
            command = Command.from_str(raw_command)
            config_path = command.config_path
            host_name = command.host_name
            global_config = load_global_config(make_global_config_path(command.config_path))
            logging.getLogger().setLevel(global_config.log_level)
            SNMPFetcher.plugin_store = global_config.snmp_plugin_store
            run_fetchers(**command._asdict())
            observer.check_resources(raw_command)
        except Exception as e:
            crash_info = create_fetcher_crash_dump(
                str(config_path) if config_path is not None else None, host_name
            )
            logger.critical("Exception is '%s' (%s)", e, crash_info)
            sys.exit(15)


@contextlib.contextmanager
def _confirm_command_processed() -> Iterator[None]:
    try:
        yield
    finally:
        logger.info("Command done")
        write(protocol.CMCMessage.end_of_reply())


def run_fetchers(
    config_path: VersionedConfigPath,
    host_name: HostName,
    timeout: int,
    mode: Mode,
) -> None:
    """Entry point from bin/fetcher"""
    try:
        # Usually OMD_SITE/var/check_mk/core/fetcher-config/[config-serial]/[host].json
        _run_fetchers_from_file(config_path, host_name, timeout, mode=mode)
    except FileNotFoundError:
        # Not an error.
        logger.warning("fetcher file for host %r and %s is absent", host_name, config_path)

    # Cleanup different things (like object specific caches)
    cmk.utils.cleanup.cleanup_globals()


def load_global_config(path: Path) -> GlobalConfig:
    try:
        with path.open() as f:
            return GlobalConfig.deserialize(json.load(f))
    except FileNotFoundError:
        logger.warning("fetcher global config %s is absent", path)
        return GlobalConfig(
            cmc_log_level=5,
            cluster_max_cachefile_age=90,
            snmp_plugin_store=SNMPPluginStore(),
        )


def _run_fetcher(
    fetcher_type: FetcherType,
    source_type: SourceType,
    host_name: HostName,
    fetcher: Fetcher,
    file_cache: FileCache,
    mode: Mode,
) -> protocol.FetcherMessage:
    """Entrypoint to obtain data from fetcher objects."""
    logger.debug("Fetch from %s", fetcher)
    with CPUTracker() as tracker:
        raw_data = get_raw_data(file_cache, fetcher, mode)

    return protocol.FetcherMessage.from_raw_data(
        host_name,
        fetcher.ident,
        raw_data,
        tracker.duration,
        fetcher_type,
        source_type,
    )


def _parse_config(
    config_path: ConfigPath, host_name: HostName
) -> Iterator[Tuple[FetcherType, SourceType, Fetcher, FileCache]]:
    with make_local_config_path(config_path, host_name).open() as f:
        data = json.load(f)

    if "fetchers" in data:
        yield from _parse_fetcher_config(data)
    elif "clusters" in data:
        yield from _parse_cluster_config(data, config_path)
    else:
        raise LookupError("invalid config")


def _parse_fetcher_config(
    data: Mapping[str, Any]
) -> Iterator[Tuple[FetcherType, SourceType, Fetcher, FileCache]]:
    # Hard crash on parser errors: The interface is versioned and internal.
    # Crashing on error really *is* the best way to catch bonehead mistakes.
    for entry in data["fetchers"]:
        fetcher_type = FetcherType[entry["fetcher_type"]]
        source_type = SourceType[entry["source_type"]]
        fetcher = FetcherFactory.from_json(fetcher_type, entry["fetcher_params"])
        match fetcher_type:
            case FetcherType.SNMP:
                file_cache: FileCache = SNMPFileCache.from_json(entry["file_cache_params"])
                file_cache.max_age = MaxAge(
                    checking=file_cache.max_age.checking,
                    discovery=0,
                    inventory=file_cache.max_age.inventory,
                )
            case FetcherType.PUSH_AGENT:
                file_cache = PushAgentFileCache.from_json(entry["file_cache_params"])
            case _:
                file_cache = AgentFileCache.from_json(entry["file_cache_params"])

        yield fetcher_type, source_type, fetcher, file_cache


def _parse_cluster_config(
    data: Mapping[str, Any], config_path: ConfigPath
) -> Iterator[Tuple[FetcherType, SourceType, Fetcher, FileCache]]:
    global_config = load_global_config(make_global_config_path(config_path))
    for host_name in data["clusters"]["nodes"]:
        for fetcher_type, source_type, fetcher, file_cache in _parse_config(config_path, host_name):
            file_cache.max_age = MaxAge(
                checking=global_config.cluster_max_cachefile_age,
                discovery=global_config.cluster_max_cachefile_age,
                inventory=2 * global_config.cluster_max_cachefile_age,
            )
            yield fetcher_type, source_type, fetcher, file_cache


def _run_fetchers_from_file(
    config_path: VersionedConfigPath,
    host_name: HostName,
    timeout: int,
    mode: Mode,
) -> None:
    """Writes to the stdio next data:
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
        fetchers = tuple(_parse_config(config_path, host_name))
        try:
            # fill as many messages as possible before timeout exception raised
            for fetcher_type, source_type, fetcher, file_cache in fetchers:
                messages.append(
                    _run_fetcher(fetcher_type, source_type, host_name, fetcher, file_cache, mode)
                )
        except MKTimeout as exc:
            # fill missing entries with timeout errors
            messages.extend(
                protocol.FetcherMessage.timeout(
                    fetcher_type,
                    source_type,
                    host_name,
                    fetcher.ident,
                    exc,
                    Snapshot.null(),
                )
                for fetcher_type, source_type, fetcher, _ in fetchers[len(messages) :]
            )

    if timeout_manager.signaled:
        messages = _replace_netsnmp_obfuscated_timeout(messages, timeout_manager.message)

    logger.debug("Produced %d messages", len(messages))
    write(
        protocol.CMCMessage.result_answer(
            messages,
            serial=config_path.serial,
            host_name=host_name,
            timeout=timeout,
            duration=cpu_tracker.duration,
        )
    )
    for msg in filter(
        lambda msg: msg.header.payload_type is protocol.PayloadType.ERROR,
        messages,
    ):
        logger.log(
            msg.header.status,
            "Error in %s fetcher: %r",
            msg.header.fetcher_type.name,
            msg.raw_data.error,
        )
        logger.debug(
            "".join(
                traceback.format_exception(
                    msg.raw_data.error.__class__,
                    msg.raw_data.error,
                    msg.raw_data.error.__traceback__,
                )
            )
        )


def _replace_netsnmp_obfuscated_timeout(
    messages: Iterable[protocol.FetcherMessage], timeout_msg: str
) -> List[protocol.FetcherMessage]:
    return [
        protocol.FetcherMessage.timeout(
            FetcherType.SNMP,
            msg.source_type,
            msg.host_name,
            msg.ident,
            MKTimeout(timeout_msg),
            Snapshot.null(),
        )
        if (
            msg.header.fetcher_type is FetcherType.SNMP
            and msg.header.payload_type is protocol.PayloadType.ERROR
            and isinstance(msg.raw_data.error, SystemError)
        )
        else msg
        for msg in messages
    ]


def write(serializable: Serializer) -> None:
    """Idea is based on the cmk method.
    Data will be received  by Microcore from a non-blocking socket, thus simple sys.stdout.write
    makes flushing mandatory, which is not always appropriate.

    1 is a file descriptor, which  is fixed by design: stdout is always 1 and microcore will
    receive data from stdout.

    The socket, we are writing in, is blocking, thus loop will not overload CPU in any case.
    """
    data = bytes(serializable)
    view = memoryview(data)
    while view:
        bytes_written = os.write(1, view)
        view = view[bytes_written:]
