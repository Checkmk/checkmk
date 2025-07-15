#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Refactor/document locking. It is not clear when and how to apply
# locks or when they are held by which component.

# TODO: Refactor events to be handled as objects, e.g. in case when
# creating objects. Or at least update the documentation. It is not clear
# which fields are mandatory for the events.

from __future__ import annotations

import abc
import ast
import contextlib
import errno
import ipaddress
import itertools
import json
import os
import pprint
import select
import signal
import socket
import sys
import threading
import time
import traceback
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from logging import DEBUG, getLogger, Logger
from pathlib import Path
from types import FrameType
from typing import Any, assert_never, IO, Literal, TypedDict

from setproctitle import setthreadtitle

import cmk.ccc.daemon
import cmk.ccc.profile
import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import omd_site

import cmk.utils.paths
from cmk.utils import log
from cmk.utils.iterables import partition
from cmk.utils.log import VERBOSE
from cmk.utils.translations import translate_hostname

from .actions import do_event_action, do_event_actions, do_notify, event_has_opened
from .config import (
    Config,
    ConfigFromWATO,
    Count,
    ECRulePack,
    Expect,
    ExpectInterval,
    MatchGroups,
    Rule,
)
from .core_queries import HostInfo, query_hosts_scheduled_downtime_depth
from .crash_reporting import CrashReportStore, ECCrashReport
from .event import create_events_from_syslog_messages, Event, scrub_string
from .helpers import ECLock, parse_bytes_into_syslog_messages
from .history import ActiveHistoryPeriod, get_logfile, History, HistoryWhat, quote_tab, TimedHistory
from .history_file import FileHistory
from .history_mongo import MongoDBHistory
from .history_sqlite import SQLiteHistory, SQLiteSettings
from .host_config import HostConfig
from .perfcounters import Perfcounters
from .query import (
    Columns,
    filter_operator_in,
    MKClientError,
    Query,
    QueryCOMMAND,
    QueryGET,
    QueryREPLICATE,
    StatusTable,
)
from .rule_matcher import compile_rule, match, MatchFailure, MatchResult, MatchSuccess, RuleMatcher
from .rule_packs import load_active_config
from .settings import create_settings, FileDescriptor, PortNumber, Settings
from .snmp import SNMPTrapParser
from .syslog import SyslogFacility, SyslogPriority
from .timeperiod import TimePeriods


def open_log(log_file_path: Path) -> None:
    try:
        logfile: IO[str] = log_file_path.open("a", encoding="utf-8")
    except Exception as e:
        getLogger("cmk.mkeventd").exception("Cannot open log file '%s': %s", log_file_path, e)
        logfile = sys.stderr
    log.setup_logging_handler(logfile)


class PackedEventStatus(TypedDict):
    next_event_id: int
    events: list[Event]
    rule_stats: dict[str, int]
    interval_starts: dict[str, int]


class SlaveStatus(TypedDict):
    last_master_down: float | None
    last_sync: float
    mode: Literal["master", "sync", "takeover"]
    success: bool


FileDescr = int  # mypy calls this FileDescriptor, but this clashes with our definition

Response = Iterable[Sequence[object]] | Mapping[str, object] | None

LimitKind = Literal["overall", "by_rule", "by_host"]


# .
#   .--Helper functions----------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'


class ECServerThread(threading.Thread):
    @abc.abstractmethod
    def serve(self) -> None:
        raise NotImplementedError

    def __init__(
        self,
        name: str,
        logger: Logger,
        settings: Settings,
        config: Config,
        slave_status: SlaveStatus,
        profiling_enabled: bool,
        profile_file: Path,
    ) -> None:
        super().__init__(name=name)
        self.settings = settings
        self._config = config
        self._slave_status = slave_status
        self._profiling_enabled = profiling_enabled
        self._profile_file = profile_file
        self._terminate_event = threading.Event()
        self._logger = logger

    def run(self) -> None:
        self._logger.info("Starting up")
        setthreadtitle(self.name)
        while not self._terminate_event.is_set():
            try:
                with cmk.ccc.profile.Profile(
                    enabled=self._profiling_enabled, profile_file=str(self._profile_file)
                ):
                    self.serve()
            except Exception:
                self._logger.exception("Exception in %s server", self.name)
                if self.settings.options.debug:
                    raise
                time.sleep(1)
        self._logger.info("Terminated")

    def terminate(self) -> None:
        self._terminate_event.set()


def create_history_raw(
    settings: Settings,
    config: Config,
    logger: Logger,
    event_columns: Columns,
    history_columns: Columns,
) -> History:
    """Factory for History objects based on the current configuration."""
    match config["archive_mode"]:
        case "file":
            return FileHistory(settings, config, logger, event_columns, history_columns)
        case "mongodb":
            return MongoDBHistory(settings, config, logger, event_columns, history_columns)
        case "sqlite":
            return SQLiteHistory(
                SQLiteSettings.from_settings(
                    settings=settings,
                    database=Path(settings.paths.history_dir.value / "history.sqlite"),
                ),
                config,
                logger,
                event_columns,
                history_columns,
            )
        case _ as default:
            assert_never(default)


def create_history(
    settings: Settings,
    config: Config,
    logger: Logger,
    event_columns: Columns,
    history_columns: Columns,
) -> History:
    """Factory for History objects based on the current configuration, optionally augmented with timing information."""
    history = create_history_raw(settings, config, logger, event_columns, history_columns)
    return TimedHistory(history) if logger.isEnabledFor(DEBUG) else history


def allowed_ip(
    ip: ipaddress.IPv6Address | ipaddress.IPv4Address,
    access_list: Iterable[ipaddress.IPv6Network | ipaddress.IPv4Network],
) -> bool:
    """
    Checks if ip is in the access_list.
    Takes care of mapped ipv6->ipv4 and ipv4->mapped_ipv6.
    This is needed because the access_list could contain ipv4/ipv6/ipv6mapped.
    """
    if any(ip in entry for entry in access_list):
        return True

    if not str(ip).startswith("::ffff:"):
        if any(ipaddress.ip_address(f"::ffff:{str(ip)}") in entry for entry in access_list):
            return True

    if isinstance(ip, ipaddress.IPv6Address):
        return any(ip.ipv4_mapped in entry for entry in access_list)

    return False


def unmap_ipv4_address(ip_address: str) -> str:
    """
    Accepts addresses with ipv4_mapped hosts and
    returns unmapped ipv4.

    >>> unmap_ipv4_address('::FFFF:192.0.2.128')
    '192.0.2.128'
    """
    try:
        host = ipaddress.ip_address(ip_address)
    except ValueError:
        # in case address[0] is a hostname
        return ip_address

    if host.version == 4:
        return ip_address

    # If IPv6 is mapped to IPv4
    if host.version == 6 and host.ipv4_mapped:
        return str(host.ipv4_mapped)

    return ip_address


def parse_address(what: str, address: object) -> tuple[str, int]:
    # We always have an AF_INET or AF_INET6 socket, so the remote address we're dealing with is a
    # pair (host: str, port: int), where host can be the domain name or an IPv4/IPv6 address.
    if not (
        isinstance(address, tuple) and isinstance(address[0], str) and isinstance(address[1], int)
    ):
        raise ValueError(f"Invalid remote address '{address!r}' for {what}")
    return unmap_ipv4_address(address[0]), address[1]


def terminate(
    terminate_main_event: threading.Event,
    event_server: EventServer,
    status_server: StatusServer,
) -> None:
    terminate_main_event.set()
    status_server.terminate()
    event_server.terminate()


def bail_out(logger: Logger, reason: str) -> None:
    logger.error("FATAL ERROR: %s", reason)
    sys.exit(1)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def drain_pipe(pipe: FileDescr) -> None:
    while True:
        try:
            readable: list[FileDescr] = select.select([pipe], [], [], 0.1)[0]
        except OSError as e:
            if e.args[0] != errno.EINTR:
                raise
            continue

        if pipe in readable:
            try:
                if not os.read(pipe, 4096):  # EOF
                    break
            except Exception:
                break  # Error while reading
        else:
            break  # No data available


def replace_groups(text: str, origtext: str, match_groups: MatchGroups) -> str:
    # replace \0 with text itself. This allows to add information
    # in front or and the end of a message
    text = text.replace("\\0", origtext)

    # Generic replacement with \1, \2, ...
    match_groups_message = match_groups.get("match_groups_message", False)
    if match_groups_message is not False:
        for nr, g in enumerate(match_groups_message):
            text = text.replace(f"\\{nr + 1}", g)

    # Replacement with keyword
    # Right now we have
    # $MATCH_GROUPS_MESSAGE_x$
    # $MATCH_GROUPS_SYSLOG_APPLICATION_x$
    for key_prefix, values in match_groups.items():
        if not isinstance(values, tuple):
            continue

        for idx, match_value in enumerate(values):
            text = text.replace(f"${key_prefix.upper()}_{idx + 1}$", match_value)

    return text


class MKSignalException(MKException):
    def __init__(self, signum: int) -> None:
        MKException.__init__(self, f"Got signal {signum}")
        self.signum = signum


# .
#   .--EventServer---------------------------------------------------------.
#   |      _____                 _   ____                                  |
#   |     | ____|_   _____ _ __ | |_/ ___|  ___ _ ____   _____ _ __        |
#   |     |  _| \ \ / / _ \ '_ \| __\___ \ / _ \ '__\ \ / / _ \ '__|       |
#   |     | |___ \ V /  __/ | | | |_ ___) |  __/ |   \ V /  __/ |          |
#   |     |_____| \_/ \___|_| |_|\__|____/ \___|_|    \_/ \___|_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Verarbeitung und Klassifizierung von eingehenden Events.            |
#   '----------------------------------------------------------------------'


class EventServer(ECServerThread):
    """Processing and classification of incoming events."""

    def __init__(
        self,
        logger: Logger,
        settings: Settings,
        config: Config,
        slave_status: SlaveStatus,
        perfcounters: Perfcounters,
        lock_configuration: ECLock,
        history: History,
        event_status: EventStatus,
        event_columns: Columns,
        create_pipes_and_sockets: bool = True,
    ) -> None:
        super().__init__(
            name="EventServer",
            logger=logger,
            settings=settings,
            config=config,
            slave_status=slave_status,
            profiling_enabled=settings.options.profile_event,
            profile_file=settings.paths.event_server_profile.value,
        )
        self._syslog_udp: socket.socket | None = None
        self._syslog_tcp: socket.socket | None = None
        self._snmp_trap_socket: socket.socket | None = None

        self._rules: list[Rule] = []
        self._rule_by_id: dict[str | None, Rule] = {}
        self._rule_hash: dict[int, dict[int, Any]] = {}
        self._hash_stats: list[list[int]] = []  # facility/priority
        for _unused_facility in range(32):
            self._hash_stats.append([0] * 8)

        self.host_config = HostConfig(self._logger)
        self._perfcounters = perfcounters
        self._lock_configuration = lock_configuration
        self._history = history
        self._event_status = event_status
        self._event_columns = event_columns
        self._message_period = ActiveHistoryPeriod()
        self._time_period = TimePeriods(logger)
        self._rule_matcher = RuleMatcher(
            logger=self._logger if config["debug_rules"] else None,
            omd_site_id=omd_site(),
            is_active_time_period=self._time_period.active,
        )

        # HACK for testing: The real fix would involve breaking up these huge
        # class monsters.
        if not create_pipes_and_sockets:
            return

        self.create_pipe()
        self.open_eventsocket()
        self.open_syslog_udp()
        self.open_syslog_tcp()
        self.open_snmptrap()
        self._snmp_trap_parser = SNMPTrapParser(
            self.settings, self._config, self._logger.getChild("snmp")
        ).parse

    @classmethod
    def status_columns(cls) -> Columns:
        return list(
            itertools.chain(
                cls._general_columns(),
                Perfcounters.status_columns(),
                cls._replication_columns(),
                cls._event_limit_columns(),
            )
        )

    @classmethod
    def _general_columns(cls) -> Columns:
        return [
            ("status_config_load_time", 0),
            ("status_num_open_events", 0),
            ("status_virtual_memory_size", 0),
        ]

    @classmethod
    def _replication_columns(cls) -> Columns:
        return [
            ("status_replication_slavemode", ""),
            ("status_replication_last_sync", 0.0),
            ("status_replication_success", False),
        ]

    @classmethod
    def _event_limit_columns(cls) -> Columns:
        return [
            ("status_event_limit_host", 0),
            ("status_event_limit_rule", 0),
            ("status_event_limit_overall", 0),
            ("status_event_limit_active_hosts", []),
            ("status_event_limit_active_rules", []),
            ("status_event_limit_active_overall", False),
        ]

    def get_status(self) -> Iterable[Sequence[object]]:
        return [
            [
                *self._add_general_status(),
                *self._perfcounters.get_status(),
                *self._add_replication_status(),
                *self._add_event_limit_status(),
            ]
        ]

    def _add_general_status(self) -> Sequence[object]:
        return [
            self._config["last_reload"],
            self._event_status.num_existing_events,
            self._virtual_memory_size(),
        ]

    def _virtual_memory_size(self) -> int:
        parts = Path("/proc/self/stat").read_text().split()
        return int(parts[22])  # in Bytes

    def _add_replication_status(self) -> list[object]:
        if is_replication_slave(self._config):
            return [
                self._slave_status["mode"],
                self._slave_status["last_sync"],
                self._slave_status["success"],
            ]
        return ["master", 0.0, False]

    def _add_event_limit_status(self) -> list[object]:
        return [
            self._config["event_limit"]["by_host"]["limit"],
            self._config["event_limit"]["by_rule"]["limit"],
            self._config["event_limit"]["overall"]["limit"],
            self.get_hosts_with_active_event_limit(),
            self.get_rules_with_active_event_limit(),
            self.is_overall_event_limit_active(),
        ]

    def create_pipe(self) -> None:
        path = self.settings.paths.event_pipe.value
        with contextlib.suppress(Exception):
            if not path.is_fifo():
                path.unlink()
        if not path.exists():
            os.mkfifo(str(path))
        # We want to be able to receive events from all users on the local system
        path.chmod(0o662)

        self._logger.info("Created FIFO '%s' for receiving events", path)

    def open_syslog_udp(self) -> None:
        endpoint = self.settings.options.syslog_udp
        try:
            if isinstance(endpoint, FileDescriptor):
                try:
                    self._logger.info("Trying to use ipv6 for syslog-udp from file descriptor")
                    self._syslog_udp = socket.fromfd(
                        endpoint.value, socket.AF_INET6, socket.SOCK_DGRAM
                    )
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for syslog-udp")
                    self._syslog_udp = socket.fromfd(
                        endpoint.value, socket.AF_INET, socket.SOCK_DGRAM
                    )
                os.close(endpoint.value)
                self._logger.info(
                    "Opened builtin syslog server on inherited filedescriptor %d", endpoint.value
                )
            if isinstance(endpoint, PortNumber):
                try:
                    self._logger.info("Trying to use ipv6 for syslog-udp")
                    self._syslog_udp = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                    self._syslog_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for syslog-udp...")
                        self._syslog_udp.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except (AttributeError, OSError):
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for syslog-udp"
                        )
                    self._syslog_udp.bind(("::", endpoint.value))
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for syslog-udp")
                    self._syslog_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._syslog_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._syslog_udp.bind(("0.0.0.0", endpoint.value))
                self._logger.info("Opened builtin syslog server on UDP port %d", endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin syslog server") from e

    def open_syslog_tcp(self) -> None:
        endpoint = self.settings.options.syslog_tcp
        try:
            if isinstance(endpoint, FileDescriptor):
                try:
                    self._logger.info("Trying to use ipv6 for syslog-tcp from file descriptor")
                    self._syslog_tcp = socket.fromfd(
                        endpoint.value, socket.AF_INET6, socket.SOCK_STREAM
                    )
                except OSError:
                    self._logger.exception("Binding ipv6 failed. Falling back to ipv4")
                    self._syslog_tcp = socket.fromfd(
                        endpoint.value, socket.AF_INET, socket.SOCK_STREAM
                    )
                self._syslog_tcp.listen(20)
                os.close(endpoint.value)
                self._logger.info(
                    "Opened builtin syslog-tcp server on inherited filedescriptor %d",
                    endpoint.value,
                )
            if isinstance(endpoint, PortNumber):
                try:
                    self._logger.info("Trying to use ipv6 for syslog-tcp")
                    self._syslog_tcp = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    self._syslog_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for syslog-tcp...")
                        self._syslog_tcp.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except (AttributeError, OSError):
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for syslog-tcp"
                        )
                    self._syslog_tcp.bind(("::", endpoint.value))
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for syslog-tcp")
                    self._syslog_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._syslog_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._syslog_tcp.bind(("0.0.0.0", endpoint.value))
                self._syslog_tcp.listen(20)
                self._logger.info("Opened builtin syslog-tcp server on TCP port %d", endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin syslog-tcp server") from e

    def open_snmptrap(self) -> None:
        endpoint = self.settings.options.snmptrap_udp
        try:
            if isinstance(endpoint, FileDescriptor):
                try:
                    self._logger.info("Trying to use ipv6 for snmptrap from file descriptor")
                    self._snmp_trap_socket = socket.fromfd(
                        endpoint.value, socket.AF_INET6, socket.SOCK_DGRAM
                    )
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for snmptrap")
                    self._snmp_trap_socket = socket.fromfd(
                        endpoint.value, socket.AF_INET, socket.SOCK_DGRAM
                    )
                os.close(endpoint.value)
                self._logger.info(
                    "Opened builtin snmptrap server on inherited filedescriptor %d", endpoint.value
                )
            if isinstance(endpoint, PortNumber):
                try:
                    self._logger.info("Trying to use ipv6 for snmptrap")
                    self._snmp_trap_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                    self._snmp_trap_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for snmptrap...")
                        self._snmp_trap_socket.setsockopt(
                            socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0
                        )
                    except (AttributeError, OSError):
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for snmptrap"
                        )
                    self._snmp_trap_socket.bind(("::", endpoint.value))
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for snmptrap")
                    self._snmp_trap_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._snmp_trap_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._snmp_trap_socket.bind(("0.0.0.0", endpoint.value))
                self._logger.info("Opened builtin snmptrap server on UDP port %d", endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin snmptrap server") from e

    def open_eventsocket(self) -> None:
        path = self.settings.paths.event_socket.value
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._eventsocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._eventsocket.bind(str(path))
        path.chmod(0o660)
        self._eventsocket.listen(self._config["eventsocket_queue_len"])
        self._logger.info("Opened UNIX socket '%s' for receiving events", path)

    def open_pipe(self) -> FileDescr:
        # Beware: we must open the pipe also for writing. Otherwise
        # we will see EOF forever after one writer has finished and
        # select() will trigger even if there is no data. A good article
        # about this is here:
        # http://www.outflux.net/blog/archives/2008/03/09/using-select-on-a-fifo/
        return os.open(str(self.settings.paths.event_pipe.value), os.O_RDWR | os.O_NONBLOCK)

    def serve(self) -> None:
        pipe = self.open_pipe()
        # We just read()/recvfrom() these, so we create no new FDs via them.
        pipe_and_datagram_sockets = [
            f for f in (pipe, self._syslog_udp, self._snmp_trap_socket) if f is not None
        ]
        # We use accept() on these FDs, so we must be careful to avoid creating too many additional
        # FDs. We use an arbitrary limit below (less than the usual 1024 FD_SETSIZE limit), so we
        # don't accept() any more connections when there are already many of them. Connections get
        # queued in the OS queue then, and when that is full, a client will get an error, which is
        # the right thing here.
        stream_sockets = [f for f in (self._syslog_tcp, self._eventsocket) if f is not None]
        client_sockets: dict[FileDescr, tuple[socket.socket, tuple[str, int] | None, bytes]] = {}
        select_timeout = 1
        unprocessed_pipe_data = b""
        while not self._terminate_event.is_set():
            try:
                readable: list[FileDescr | socket.socket] = select.select(
                    pipe_and_datagram_sockets
                    + (stream_sockets if len(client_sockets) < 900 else [])
                    + list(client_sockets.keys()),
                    [],
                    [],
                    select_timeout,
                )[0]
            except OSError as e:
                if e.args[0] != errno.EINTR:
                    raise
                continue
            address: tuple[str, int] | None  # host/port

            # Accept new connection on event unix socket
            if self._eventsocket in readable:
                client_socket, remote_address = self._eventsocket.accept()
                # We have a AF_UNIX socket, so the remote address is a str, which is always ''.
                if not (isinstance(remote_address, str) and remote_address == ""):
                    raise ValueError(
                        f"Invalid remote address '{remote_address!r}' for event socket"
                    )
                client_sockets[client_socket.fileno()] = (client_socket, None, b"")

            # Same for the TCP syslog socket
            if self._syslog_tcp is not None and self._syslog_tcp in readable:
                client_socket, address = self._syslog_tcp.accept()
                client_sockets[client_socket.fileno()] = (
                    client_socket,
                    parse_address("syslog socket (TCP)", address),
                    b"",
                )

            # Read data from existing event unix socket connections
            # NOTE: We modify client_socket in the loop, so we need to copy below!
            for fd, (cs, address, previous_data) in list(client_sockets.items()):
                if fd in readable:
                    try:
                        new_data = cs.recv(4096)
                    except Exception:
                        new_data = b""
                        self._logger.exception("Exception during syslog socket_tcp recv")

                    if new_data:
                        messages, unprocessed = parse_bytes_into_syslog_messages(
                            previous_data + new_data
                        )
                        self.process_syslog_messages(messages, address)
                        client_sockets[fd] = (cs, address, unprocessed)
                    else:  # the other side is gone, no more data will ever come
                        del client_sockets[fd]  # discarding previous_data is OK, it's incomplete
                        cs.close()  # do this *after* the bookkeeping above, close() can throw

            # Read data from pipe
            if pipe in readable:
                try:
                    unprocessed_pipe_data += os.read(pipe, 4096)
                except Exception:
                    self._logger.exception("General exception during pipe os.read")

                messages, unprocessed_pipe_data = parse_bytes_into_syslog_messages(
                    unprocessed_pipe_data
                )
                self.process_syslog_messages(messages, None)

            # Read events from builtin syslog server
            if self._syslog_udp is not None and self._syslog_udp in readable:
                message, address = self._syslog_udp.recvfrom(4096)
                self.process_syslog_messages(
                    [message], parse_address("syslog socket (UDP)", address)
                )

            # Read events from builtin snmptrap server
            if self._snmp_trap_socket is not None and self._snmp_trap_socket in readable:
                message, address = self._snmp_trap_socket.recvfrom(65535)
                self.process_potential_event_instrumented(
                    self.create_events_from_trap(message, parse_address("SNMP trap", address))
                )

            if spool_files := sorted(
                self.settings.paths.spool_dir.value.glob("[!.]*"), key=lambda x: x.stat().st_mtime
            ):
                self.process_syslog_messages(spool_files[0].read_bytes().splitlines(), None)
                spool_files[0].unlink()
                select_timeout = 0  # enable fast processing to process further files
            else:
                select_timeout = 1  # restore default select timeout

    def create_events_from_trap(self, data: bytes, address: tuple[str, int]) -> Iterator[Event]:
        try:
            if varbinds_and_ipaddress := self._snmp_trap_parser(data, address):
                yield create_event_from_trap(varbinds_and_ipaddress[0], varbinds_and_ipaddress[1])
        except Exception as e:
            # NOTE: SNMPTrapParser._handle_unauthenticated_snmptrap() logs more details about what
            # went wrong on "verbose" logging level, anyway. We do not log on "info" here to avoid
            # possible log spam from a misconfigured/buggy device.
            self._logger.debug("skipping unparsable SNMP trap, reason: %s", e)

    def process_potential_event_instrumented(self, events: Iterable[Event]) -> None:
        """
        Processes incoming data, just a wrapper between the real data and the
        handler function to record some statistics etc.
        """
        for event in events:
            self._perfcounters.count("messages")
            before = time.time()
            # In replication slave mode (when not took over), ignore all events
            if not is_replication_slave(self._config) or self._slave_status["mode"] != "sync":
                self.process_potential_event(event)
            elif self.settings.options.debug:
                self._logger.info("Replication: we are in slave mode, ignoring event")
            elapsed = time.time() - before
            self._perfcounters.count_time("processing", elapsed)

    def process_syslog_messages(
        self, messages: Iterable[bytes], address: tuple[str, int] | None
    ) -> None:
        self.process_potential_event_instrumented(
            create_events_from_syslog_messages(
                messages, address, self._logger if self._config["debug_rules"] else None
            )
        )

    def do_housekeeping(self) -> None:
        with self._event_status.lock, self._lock_configuration:
            self.hk_handle_event_timeouts()
            self.hk_check_expected_messages()
            self.hk_cleanup_downtime_events()
        self._history.housekeeping()

    def hk_cleanup_downtime_events(self) -> None:
        """
        For all events that have been created in a host downtime check the host
        whether or not it is still in downtime. In case the downtime has ended
        archive the events that have been created in a downtime.
        """
        host_downtimes: dict[str, bool] = {}
        for event in self._event_status.events():
            if not event["host_in_downtime"]:
                continue  # only care about events created in downtime
            host_name = HostName("") if event["core_host"] is None else event["core_host"]
            try:
                in_downtime = host_downtimes[host_name]
            except KeyError:
                in_downtime = self._is_host_in_downtime(host_name)
                host_downtimes[host_name] = in_downtime
            if in_downtime:
                continue  # (still) in downtime, don't delete any event
            self._logger.log(
                VERBOSE, "Remove event %d (created in downtime, host left downtime)", event["id"]
            )
            self._event_status.remove_event(event, "AUTODELETE")

    def hk_handle_event_timeouts(self) -> None:
        """
        1. Automatically delete all events that are in state "counting"
           and have not reached the required number of hits and whose
           time is elapsed.
        2. Automatically delete all events that are in state "open"
           and whose lifetime is elapsed.
        """
        events_to_delete: list[tuple[Event, HistoryWhat]] = []
        events = self._event_status.events()
        now = time.time()
        for event in events:
            rule = self._rule_by_id.get(event["rule_id"])

            if event["phase"] == "counting":
                # Event belongs to a rule that does not longer exist? It
                # will never reach its count. Better delete it.
                if not rule:
                    self._logger.info(
                        "Deleting orphaned event %d created by obsolete rule %s",
                        event["id"],
                        event["rule_id"],
                    )
                    event["phase"] = "closed"
                    events_to_delete.append((event, "ORPHANED"))

                elif "count" not in rule and not rule.get("expect"):
                    self._logger.info(
                        "Count-based event %d belonging to rule %s: rule does not "
                        "count/expect anymore. Deleting event.",
                        event["id"],
                        event["rule_id"],
                    )
                    event["phase"] = "closed"
                    events_to_delete.append((event, "NOCOUNT"))

                # handle counting
                elif "count" in rule:
                    count = rule["count"]
                    if count.get("algorithm") in {"tokenbucket", "dynabucket"}:
                        last_token = event.get("last_token", event["first"])
                        secs_per_token = count["period"] / float(count["count"])
                        if count["algorithm"] == "dynabucket":  # get fewer tokens if count is lower
                            if event["count"] <= 1:
                                secs_per_token = count["period"]
                            else:
                                secs_per_token *= float(count["count"]) / float(event["count"])
                        elapsed_secs = now - last_token
                        new_tokens = int(elapsed_secs / secs_per_token)
                        if new_tokens:
                            if self.settings.options.debug:
                                self._logger.info(
                                    "Rule %s/%s, event %d: got %d new tokens",
                                    rule["pack"],
                                    rule["id"],
                                    event["id"],
                                    new_tokens,
                                )
                            event["count"] = max(0, event["count"] - new_tokens)
                            event["last_token"] = (
                                last_token + new_tokens * secs_per_token
                            )  # not now! would be unfair
                            if event["count"] == 0:
                                self._logger.info(
                                    "Rule %s/%s, event %d: again without allowed rate, dropping event",
                                    rule["pack"],
                                    rule["id"],
                                    event["id"],
                                )
                                event["phase"] = "closed"
                                events_to_delete.append((event, "COUNTFAILED"))

                    elif event["first"] + count["period"] <= now:  # End of period reached
                        self._logger.info(
                            "Rule %s/%s: reached only %d out of %d events within %d seconds. "
                            "Resetting to zero.",
                            rule["pack"],
                            rule["id"],
                            event["count"],
                            count["count"],
                            count["period"],
                        )
                        event["phase"] = "closed"
                        events_to_delete.append((event, "COUNTFAILED"))

            # Handle delayed actions
            elif event["phase"] == "delayed":
                delay_until = event.get("delay_until", 0)  # should always be present
                if now >= delay_until:
                    self._logger.info(
                        "Delayed event %d of rule %s is now activated.",
                        event["id"],
                        event["rule_id"],
                    )
                    event["phase"] = "open"
                    self._history.add(event, "DELAYOVER")
                    if rule:
                        event_has_opened(
                            self._history,
                            self.settings,
                            self._config,
                            self._logger,
                            self.host_config,
                            self._event_columns,
                            rule,
                            event,
                        )
                        if rule.get("autodelete"):
                            event["phase"] = "closed"
                            events_to_delete.append((event, "AUTODELETE"))

                    else:
                        self._logger.info(
                            "Cannot do rule action: rule %s not present anymore.", event["rule_id"]
                        )

            # Handle events with a limited lifetime
            elif "live_until" in event and now >= event["live_until"]:
                allowed_phases = event.get("live_until_phases", ["open"])
                if event["phase"] in allowed_phases:
                    event["phase"] = "closed"
                    events_to_delete.append((event, "EXPIRED"))
                    self._logger.info(
                        "Lifetime of event %d (rule %s) exceeded. Deleting event.",
                        event["id"],
                        event["rule_id"],
                    )

        for event, reason in events_to_delete:
            self._event_status.remove_event(event, reason)

    def hk_check_expected_messages(self) -> None:
        """
        "Expecting"-rules are rules that require one or several
        occurrences of a message within a defined time period.
        Whenever one period of time has elapsed, we need to check
        how many messages have been seen for that rule. If these
        are too few, we open an event.
        We need to handle to cases:
        1. An event for such a rule already exists and is
           in the state "counting" -> this can only be the case if
           more than one occurrence is required.
        2. No event at all exists.
           in that case.
        """
        now = time.time()
        for rule in self._rules:
            if expect := rule.get("expect"):
                if isinstance(
                    self._rule_matcher.event_rule_matches_site(rule, event=Event()), MatchFailure
                ):
                    continue

                interval = expect["interval"]
                interval_start = self._event_status.interval_start(rule["id"], interval)
                if interval_start >= now:
                    continue

                next_interval_start = self._event_status.next_interval_start(
                    interval, interval_start
                )
                if next_interval_start > now:
                    continue

                # Interval has been elapsed. Now comes the truth: do we have enough
                # rule matches?

                # First do not forget to switch to next interval
                self._event_status.start_next_interval(rule["id"], interval)

                # First look for case 1: rule that already have at least one hit
                # and this events in the state "counting" exist.
                events_to_delete: list[tuple[Event, HistoryWhat]] = []
                events = self._event_status.events()
                for event in events:
                    if event["rule_id"] == rule["id"] and event["phase"] == "counting":
                        # time has elapsed. Now lets see if we have reached
                        # the necessary count:
                        if event["count"] < expect["count"]:  # no -> trigger alarm
                            events_to_delete.append((event, "AUTODELETE"))
                            self._handle_absent_event(rule, expect, event["count"], event["last"])
                        else:  # yes -> everything is fine. Just log.
                            self._logger.info(
                                "Rule %s/%s has reached %d occurrences (%d required). "
                                "Starting next period.",
                                rule["pack"],
                                rule["id"],
                                event["count"],
                                expect["count"],
                            )
                        # Counting event is no longer needed.
                        events_to_delete.append((event, "COUNTREACHED"))
                        break

                # Ou ou, no event found at all.
                else:
                    self._handle_absent_event(rule, expect, 0, interval_start)

                for event, reason in events_to_delete:
                    self._event_status.remove_event(event, reason)

    def _handle_absent_event(
        self, rule: Rule, expect: Expect, event_count: int, interval_start: float
    ) -> None:
        now = time.time()
        if event_count:
            text = (
                f"Expected message arrived only {event_count} out of {expect['count']}"
                f" times since {time.strftime('%F %T', time.localtime(interval_start))}"
            )

        else:
            text = f"Expected message did not arrive since {time.strftime('%F %T', time.localtime(interval_start))}"

        # If there is already an incidence about this absent message, we can merge and
        # not create a new event. There is a setting for this.
        merge_event = None

        reset_ack = True
        merge = expect.get("merge", "open")

        # Changed "acked" to ("acked", bool) with 1.6.0p20
        if isinstance(merge, tuple):  # TODO: Move this to upgrade time
            merge, reset_ack = merge  # type: ignore[unreachable]

        if merge != "never":
            for event in self._event_status.events():
                if event["rule_id"] == rule["id"] and (
                    event["phase"] == "open" or (event["phase"] == "ack" and merge == "acked")
                ):
                    merge_event = event
                    break

        if merge_event:
            merge_event["last"] = now
            merge_event["count"] += 1

            # This was resetting the state back to "open", even in case an
            # "ack" event is being merged. This was made configurable in
            # 1.6.0p20 because of SUP-4803.
            if reset_ack:
                merge_event["phase"] = "open"

            merge_event["time"] = now
            merge_event["text"] = text
            # Better rewrite (again). Rule might have changed. Also we have changed
            # the text and the user might have his own text added via set_text.
            self.rewrite_event(rule, merge_event, MatchGroups(), set_first=False)
            self._history.add(merge_event, "COUNTFAILED")
        else:
            # Create artificial event from scratch. Make sure that all important
            # fields are defined.
            event = Event(
                rule_id=rule["id"],
                text=text,
                phase="open",
                count=1,
                time=now,
                first=now,
                last=now,
                comment="",
                host=HostName(""),
                ipaddress="",
                application="",
                pid=0,
                priority=3,
                facility=1,  # user
                match_groups=(),
                match_groups_syslog_application=(),
                core_host=HostName(""),
                host_in_downtime=False,
            )
            self._add_rule_contact_groups_to_event(rule, event)
            self.rewrite_event(rule, event, MatchGroups())
            self._event_status.new_event(event)
            self._history.add(event, "COUNTFAILED")
            event_has_opened(
                self._history,
                self.settings,
                self._config,
                self._logger,
                self.host_config,
                self._event_columns,
                rule,
                event,
            )
            if rule.get("autodelete"):
                event["phase"] = "closed"
                self._event_status.remove_event(event, "AUTODELETE")

    def reload_configuration(self, config: Config, history: History) -> None:
        self._config = config
        self._history = history
        self._snmp_trap_parser = SNMPTrapParser(
            self.settings, self._config, self._logger.getChild("snmp")
        ).parse
        self.compile_rules(self._config["rule_packs"])
        self.host_config = HostConfig(self._logger)
        self._rule_matcher = RuleMatcher(
            logger=self._logger if config["debug_rules"] else None,
            omd_site_id=omd_site(),
            is_active_time_period=self._time_period.active,
        )

    def compile_rules(self, rule_packs: Sequence[ECRulePack]) -> None:
        """Precompile regular expressions and similar stuff."""
        self._rules = []
        self._rule_by_id = {}
        # Speedup-Hash for rule execution
        self._rule_hash = {}
        count_disabled = 0
        count_rules = 0
        count_unspecific = 0

        # Loop through all rule packs and with through their rules
        for rule_pack in rule_packs:
            if rule_pack["disabled"]:
                count_disabled += len(rule_pack["rules"])
                continue

            for rule in rule_pack["rules"]:
                if rule.get("disabled"):
                    count_disabled += 1
                else:
                    count_rules += 1
                    rule = rule.copy()  # keep original intact because of slave replication

                    # Store information about rule pack right within the rule. This is needed
                    # for debug output and also for skipping rule packs
                    rule["pack"] = rule_pack["id"]
                    self._rules.append(rule)
                    self._rule_by_id[rule["id"]] = rule
                    try:
                        compile_rule(rule)
                    except Exception:
                        if self.settings.options.debug:
                            raise
                        rule["disabled"] = True
                        count_disabled += 1
                        self._logger.exception(
                            "Ignoring rule '%s/%s' because of an invalid regex.",
                            rule["pack"],
                            rule["id"],
                        )

                    if self._config["rule_optimizer"]:
                        self.hash_rule(rule)
                        if (
                            "match_facility" not in rule
                            and "match_priority" not in rule
                            and "cancel_priority" not in rule
                            and "cancel_application" not in rule
                        ):
                            count_unspecific += 1

        self._logger.info(
            "Compiled %d active rules (ignoring %d disabled rules)", count_rules, count_disabled
        )
        if self._config["rule_optimizer"]:
            self._logger.info(
                "Rule hash: %d rules - %d hashed, %d unspecific",
                len(self._rules),
                len(self._rules) - count_unspecific,
                count_unspecific,
            )
            for facility in list(range(23)) + [31]:
                if facility in self._rule_hash:
                    stats = [
                        f"{SyslogPriority(prio)}({len(entries)})"
                        for prio, entries in self._rule_hash[facility].items()
                    ]
                    self._logger.info(" %-12s: %s", SyslogFacility(facility), " ".join(stats))

    def hash_rule(self, rule: Rule) -> None:
        """Construct rule hash for faster execution."""
        facility = rule.get("match_facility")
        if facility and not rule.get("invert_matching"):
            self.hash_rule_facility(rule, facility)
        else:
            for facility in range(32):  # all syslog facilities
                self.hash_rule_facility(rule, facility)

    def hash_rule_facility(self, rule: Rule, facility: int) -> None:
        needed_prios = [False] * 8

        if "match_priority" in rule:
            prio_from, prio_to = rule["match_priority"]
            for p in range(prio_to, prio_from + 1):  # Beware: from > to!
                needed_prios[p] = True
        else:  # all priorities match
            needed_prios = [True] * 8  # needed to check this rule for all event priorities

        if "cancel_priority" in rule:
            prio_from, prio_to = rule["cancel_priority"]
            for p in range(prio_to, prio_from + 1):  # Beware: from > to!
                needed_prios[p] = True
        elif "match_ok" in rule:  # a cancelling rule where all priorities cancel
            needed_prios = [True] * 8  # needed to check this rule for all event priorities

        if rule.get("invert_matching"):
            needed_prios = [True] * 8

        prio_hash = self._rule_hash.setdefault(facility, {})
        for prio, need in enumerate(needed_prios):
            if need:
                prio_hash.setdefault(prio, []).append(rule)

    def output_hash_stats(self) -> None:
        self._logger.info("Top 20 of facility/priority:")
        entries = []
        total_count = 0
        for facility in range(32):
            for priority in range(8):
                count = self._hash_stats[facility][priority]
                if count:
                    total_count += count
                    entries.append((count, (facility, priority)))
        entries.sort()
        entries.reverse()
        for count, (facility, priority) in entries[:20]:
            self._logger.info(
                "  %s/%s - %d (%.2f%%)",
                SyslogFacility(facility),
                SyslogPriority(priority),
                count,
                (100.0 * count / float(total_count)),
            )

    def process_potential_event(self, event: Event) -> None:
        self.do_translate_hostname(event)

        # Log all incoming messages into a syslog-like text file if that is enabled
        if self._config["log_messages"]:
            self.log_message(event)

        # Rule optimizer
        if self._config["rule_optimizer"]:
            self._hash_stats[event["facility"]][event["priority"]] += 1
            rule_candidates = self._rule_hash.get(event["facility"], {}).get(event["priority"], [])
        else:
            rule_candidates = self._rules

        skip_pack = None
        for rule in rule_candidates:
            if skip_pack and rule["pack"] == skip_pack:
                continue  # still in the rule pack that we want to skip
            skip_pack = None  # new pack, reset skipping

            try:
                result = self.event_rule_matches(rule, event)
            except Exception as e:
                result = MatchFailure(
                    reason=f"Rule would match, but due to inverted matching does not. {e}"
                )
                self._logger.exception(result.reason)

            if isinstance(result, MatchSuccess):
                self._perfcounters.count("rule_hits")
                if self._config["debug_rules"]:
                    self._logger.info("  matching groups:\n%s", pprint.pformat(result.match_groups))

                self._event_status.count_rule_match(rule["id"])
                if self._config["log_rulehits"]:
                    self._logger.info(
                        "Rule '%s/%s' hit by message %s/%s - '%s'.",
                        rule["pack"],
                        rule["id"],
                        SyslogFacility(event["facility"]),
                        SyslogPriority(event["priority"]),
                        event["text"],
                    )

                if rule.get("drop"):
                    if rule["drop"] == "skip_pack":
                        skip_pack = rule["pack"]
                        if self._config["debug_rules"]:
                            self._logger.info("  skipping this rule pack (%s)", skip_pack)
                        continue
                    self._perfcounters.count("drops")
                    return

                if result.cancelling:
                    self._event_status.cancel_events(
                        self, self._event_columns, event, result.match_groups, rule
                    )
                    return

                # Remember the rule id that this event originated from
                event["rule_id"] = rule["id"]

                # Attach optional contact group information for visibility
                # and eventually for notifications
                self._add_rule_contact_groups_to_event(rule, event)

                # Store groups from matching this event. In order to make
                # persistence easier, we do not save them as list but join
                # them on ASCII-1.
                match_groups_message = result.match_groups.get("match_groups_message", ())
                assert match_groups_message is not False
                event["match_groups"] = match_groups_message

                match_groups_syslog_application = result.match_groups.get(
                    "match_groups_syslog_application", ()
                )
                assert match_groups_syslog_application is not False
                event["match_groups_syslog_application"] = match_groups_syslog_application

                self.rewrite_event(rule, event, result.match_groups)

                # Lookup the monitoring core hosts and add the core host
                # name to the event when one can be matched.
                #
                # Needs to be done AFTER event rewriting, because the rewriting
                # may change the "host" field.
                #
                # For the moment we have no rule/condition matching on this
                # field. So we only add the core host info for matched events.
                self._add_core_host_to_new_event(event)

                if "count" in rule:
                    count = rule["count"]
                    # Check if a matching event already exists that we need to
                    # count up. If the count reaches the limit, the event will
                    # be opened and its rule actions performed.
                    existing_event = self._event_status.count_event(self, event, count)
                    if existing_event:
                        if "delay" in rule:
                            if self._config["debug_rules"]:
                                self._logger.info(
                                    "Event opening will be delayed for %d seconds", rule["delay"]
                                )
                            existing_event["delay_until"] = time.time() + rule["delay"]
                            existing_event["phase"] = "delayed"
                        else:
                            event_has_opened(
                                self._history,
                                self.settings,
                                self._config,
                                self._logger,
                                self.host_config,
                                self._event_columns,
                                rule,
                                existing_event,
                            )

                        self._history.add(existing_event, "COUNTREACHED")

                        if "delay" not in rule and rule.get("autodelete"):
                            existing_event["phase"] = "closed"
                            with self._event_status.lock:
                                self._event_status.remove_event(existing_event, "AUTODELETE")
                elif rule.get("expect"):
                    self._event_status.count_expected_event(self, event)
                else:
                    if "delay" in rule:
                        if self._config["debug_rules"]:
                            self._logger.info(
                                "Event opening will be delayed for %d seconds", rule["delay"]
                            )
                        event["delay_until"] = time.time() + rule["delay"]
                        event["phase"] = "delayed"
                    else:
                        event["phase"] = "open"

                    if self.new_event_respecting_limits(event) and event["phase"] == "open":
                        event_has_opened(
                            self._history,
                            self.settings,
                            self._config,
                            self._logger,
                            self.host_config,
                            self._event_columns,
                            rule,
                            event,
                        )
                        if rule.get("autodelete"):
                            event["phase"] = "closed"
                            with self._event_status.lock:
                                self._event_status.remove_event(event, "AUTODELETE")
                return

        # End of loop over rules.
        if self._config["archive_orphans"]:
            self._event_status.archive_event(event)

    def _add_rule_contact_groups_to_event(self, rule: Rule, event: Event) -> None:
        if rule.get("contact_groups") is None:
            event.update(
                {
                    "contact_groups": None,
                    "contact_groups_notify": False,
                    "contact_groups_precedence": "host",
                }
            )
        else:
            event.update(
                {
                    "contact_groups": rule["contact_groups"]["groups"],
                    "contact_groups_notify": rule["contact_groups"]["notify"],
                    "contact_groups_precedence": rule["contact_groups"]["precedence"],
                }
            )

    def add_core_host_to_event(self, event: Event) -> None:
        event["core_host"] = self.host_config.get_canonical_name(event["host"])

    def _add_core_host_to_new_event(self, event: Event) -> None:
        self.add_core_host_to_event(event)

        # Add some state dependent information (like host is in downtime etc.)
        event["host_in_downtime"] = self._is_host_in_downtime(event["core_host"])

    def _is_host_in_downtime(self, host_name: HostName | None) -> bool:
        if not host_name:
            return False  # Found no host in core: Not in downtime!
        try:
            return query_hosts_scheduled_downtime_depth(host_name) >= 1
        except Exception:
            self._logger.exception(
                "Cannot get downtime info for host '%s', assuming no downtime.", host_name
            )
            return False

    def event_rule_matches(self, rule: Rule, event: Event) -> MatchResult:
        """
        Checks if an event matches a rule. Returns either MatchFailure (no match)
        or a MatchSuccess with a pair of matchtype, groups, where matchtype is False for a
        normal match and True for a cancelling match and the groups is a tuple
        if matched regex groups in either text (normal) or match_ok (cancelling)
        match.
        """
        self._perfcounters.count("rule_tries")
        with self._lock_configuration:
            return self._rule_matcher.event_rule_matches(rule, event)

    def rewrite_event(
        self, rule: Rule, event: Event, match_groups: MatchGroups, set_first: bool = True
    ) -> None:
        """Rewrite texts and compute other fields in the event."""
        if rule["state"] == -1:
            prio = event["priority"]
            if prio <= 3:
                event["state"] = 2
            elif prio == 4:
                event["state"] = 1
            else:
                event["state"] = 0
        elif isinstance(rule["state"], tuple) and rule["state"][0] == "text_pattern":
            state_patterns = rule["state"][1]
            text = event["text"]
            if match(state_patterns.get("2", None), text, complete=False) is not False:
                event["state"] = 2
            elif match(state_patterns.get("1", None), text, complete=False) is not False:
                event["state"] = 1
            elif match(state_patterns.get("0", None), text, complete=False) is not False:
                event["state"] = 0
            else:
                event["state"] = 3
        else:
            event["state"] = rule["state"]

        if ("sl" not in event) or (rule["sl"]["precedence"] == "rule"):
            event["sl"] = rule["sl"]["value"]
        if set_first:
            event["first"] = event["time"]
        event["last"] = event["time"]
        if "set_comment" in rule:
            event["comment"] = replace_groups(rule["set_comment"], event["text"], match_groups)
        if "set_text" in rule:
            event["text"] = replace_groups(rule["set_text"], event["text"], match_groups)
        if "set_host" in rule:
            event["orig_host"] = event["host"]
            event["host"] = HostName(replace_groups(rule["set_host"], event["host"], match_groups))
        if "set_application" in rule:
            event["application"] = replace_groups(
                rule["set_application"], event["application"], match_groups
            )
        if "set_contact" in rule and "contact" not in event:
            event["contact"] = replace_groups(
                rule["set_contact"], event.get("contact", ""), match_groups
            )

    def do_translate_hostname(self, event: Event) -> None:
        try:
            event["host"] = translate_hostname(self._config["hostname_translation"], event["host"])
        except Exception:
            if self._config["debug_rules"]:
                self._logger.exception('Unable to parse host "%s"', event.get("host"))
            event["host"] = HostName("")

    def log_message(self, event: Event) -> None:
        try:
            with get_logfile(
                self._config, self.settings.paths.messages_dir.value, self._message_period
            ).open(mode="ab") as f:
                f.write(
                    (
                        "%s %s %s%s: %s\n"
                        % (
                            time.strftime("%b %d %H:%M:%S", time.localtime(event["time"])),
                            event["host"],
                            event["application"],
                            f"[{event['pid']}]" if event["pid"] else "",
                            event["text"],
                        )
                    ).encode()
                )
        except Exception:
            if self.settings.options.debug:
                raise
            # Better silently ignore errors. We could have run out of
            # diskspace and make things worse by logging that we could
            # not log.

    def get_hosts_with_active_event_limit(self) -> list[str]:
        hosts = []
        for (hostname, core_host), count in self._event_status.num_existing_events_by_host.items():
            host_config = self.host_config.get_config_for_host(core_host) if core_host else None
            if count >= self._get_host_event_limit(host_config)[0]:
                hosts.append(hostname)
        return hosts

    def get_rules_with_active_event_limit(self) -> list[str]:
        rule_ids = []
        for rule_id, num_events in self._event_status.num_existing_events_by_rule.items():
            if rule_id is None:
                continue  # Ignore rule unrelated overflow events. They have no rule id associated.
            if num_events >= self._get_rule_event_limit(rule_id)[0]:
                rule_ids.append(rule_id)
        return rule_ids

    def is_overall_event_limit_active(self) -> bool:
        return (
            self._event_status.num_existing_events
            >= self._config["event_limit"]["overall"]["limit"]
        )

    # protected by self._event_status.lock
    def new_event_respecting_limits(self, event: Event) -> bool:
        self._logger.log(
            VERBOSE,
            "Checking limit for message from %s (rule '%s')",
            event["host"],
            event["rule_id"],
        )

        core_host = event["core_host"]
        host_config = self.host_config.get_config_for_host(core_host) if core_host else None
        with self._event_status.lock:
            if self._handle_event_limit("overall", event, host_config):
                return False

            if self._handle_event_limit("by_host", event, host_config):
                return False

            if self._handle_event_limit("by_rule", event, host_config):
                return False

            self._event_status.new_event(event)
            return True

    # The following actions can be configured:
    # stop                 Stop creating new events
    # stop_overflow        Stop creating new events, create overflow event
    # stop_overflow_notify Stop creating new events, create overflow event, notify
    # delete_oldest        Delete oldest event, create new event
    # protected by self._event_status.lock

    def _handle_event_limit(
        self, ty: LimitKind, event: Event, host_config: HostInfo | None
    ) -> bool:
        """Returns False if the event has been created and actions should be performed on that event."""
        num_already_open = self._event_status.get_num_existing_events_by(ty, event)

        limit, action = self._get_event_limit(ty, event, host_config)
        self._logger.log(
            VERBOSE, "  Type: %s, already open events: %d, Limit: %d", ty, num_already_open, limit
        )

        # Limit not reached: add new event
        if num_already_open < limit:
            num_already_open += 1  # after adding this event

        # Limit even then still not reached: we are fine
        if num_already_open < limit:
            return False

        # Delete oldest messages if that is the configure method of keeping the limit
        if action == "delete_oldest":
            while num_already_open > limit:
                self._perfcounters.count("overflows")
                self._event_status.remove_oldest_event(ty, event)
                num_already_open -= 1
            return False

        # Limit reached already in the past: Simply drop silently
        if num_already_open > limit:
            # Just log in verbose mode! Otherwise log file will be flooded
            self._logger.log(VERBOSE, "  Skip processing because limit is already in effect")
            self._perfcounters.count("overflows")
            return True  # Prevent creation and prevent one time actions (below)

        self._logger.info("  The %s limit has been reached", ty)

        # This is the event which reached the limit, allow creation of it. Further
        # events will be stopped.

        # Perform one time actions
        overflow_event = self._create_overflow_event(ty, event, limit)

        if "overflow" in action:
            self._logger.info("  Creating overflow event")
            self._event_status.new_event(overflow_event)

        if "notify" in action:
            self._logger.info("  Creating overflow notification")
            do_notify(self.host_config, self._logger, overflow_event)

        return False

    # protected by self._event_status.lock
    def _get_event_limit(
        self, ty: LimitKind, event: Event, host_config: HostInfo | None
    ) -> tuple[int, str]:
        match ty:
            case "overall":
                return self._get_overall_event_limit()
            case "by_rule":
                return self._get_rule_event_limit(event["rule_id"])
            case "by_host":
                return self._get_host_event_limit(host_config)
            case _ as unreachable:
                assert_never(unreachable)

    def _get_overall_event_limit(self) -> tuple[int, str]:
        return (
            self._config["event_limit"]["overall"]["limit"],
            self._config["event_limit"]["overall"]["action"],
        )

    def _get_rule_event_limit(self, rule_id: str | None) -> tuple[int, str]:
        """Prefer the rule individual limit for by_rule limit (in case there is some)."""
        if rule_limit := self._rule_by_id.get(rule_id, Rule()).get("event_limit"):
            return rule_limit["limit"], rule_limit["action"]

        return (
            self._config["event_limit"]["by_rule"]["limit"],
            self._config["event_limit"]["by_rule"]["action"],
        )

    def _get_host_event_limit(self, host_config: HostInfo | None) -> tuple[int, str]:
        """Prefer the host individual limit for by_host limit (in case there is some)."""
        host_limit = (
            None if host_config is None else host_config.custom_variables.get("EC_EVENT_LIMIT")
        )
        if host_limit:
            limit, action = host_limit.split(":", 1)
            return int(limit), action

        return (
            self._config["event_limit"]["by_host"]["limit"],
            self._config["event_limit"]["by_host"]["action"],
        )

    def _create_overflow_event(self, ty: LimitKind, event: Event, limit: int) -> Event:
        now = time.time()
        new_event = Event(
            rule_id=None,
            phase="open",
            count=1,
            time=now,
            first=now,
            last=now,
            comment="",
            host=HostName(""),
            ipaddress="",
            application="Event Console",
            pid=0,
            priority=2,  # crit
            facility=1,  # user
            match_groups=(),
            match_groups_syslog_application=(),
            state=2,  # crit
            sl=event["sl"],
            core_host=None,
            host_in_downtime=False,
        )
        self._add_rule_contact_groups_to_event(Rule(), new_event)

        match ty:
            case "overall":
                new_event["text"] = (
                    f"The overall event limit of {limit} open events has been reached. Not "
                    "opening any additional event until open events have been "
                    "archived."
                )

            case "by_host":
                new_event.update(
                    {
                        "host": event["host"],
                        "ipaddress": event["ipaddress"],
                        "text": (
                            f'The host event limit of {limit} open events has been reached for host "{event["host"]}". '
                            "Not opening any additional event for this host until open events have "
                            "been archived."
                        ),
                    }
                )

                # Lookup the monitoring core hosts and add the core host
                # name to the event when one can be matched
                self._add_core_host_to_new_event(new_event)

            case "by_rule":
                new_event.update(
                    {
                        "rule_id": event["rule_id"],
                        "contact_groups": event["contact_groups"],
                        "contact_groups_notify": event.get("contact_groups_notify", False),
                        "contact_groups_precedence": event.get("contact_groups_precedence", "host"),
                        "text": (
                            f'The rule event limit of {limit} open events has been reached for rule "{event["rule_id"]}". '
                            "Not opening any additional event for this rule until open events have "
                            "been archived."
                        ),
                    }
                )

            case _ as unreachable:
                assert_never(unreachable)

        return new_event


def create_event_from_trap(trap: Iterable[tuple[str, str]], ipaddress_: str) -> Event:
    """New event with the trap OID as the application."""
    trapOIDs, other = partition(
        lambda binding: binding[0] in {"1.3.6.1.6.3.1.1.4.1.0", "SNMPv2-MIB::snmpTrapOID.0"}, trap
    )
    return Event(
        time=time.time(),
        host=HostAddress(scrub_string(ipaddress_)),
        ipaddress=scrub_string(ipaddress_),
        priority=5,  # notice
        facility=31,  # not used by syslog -> we use this for all traps
        application=scrub_string(trapOIDs[0][1] if trapOIDs else ""),
        text=scrub_string(", ".join(f"{oid}: {value}" for oid, value in other)),
        core_host=None,
        host_in_downtime=False,
    )


# .
#   .--Status Queries------------------------------------------------------.
#   |  ____  _        _                ___                  _              |
#   | / ___|| |_ __ _| |_ _   _ ___   / _ \ _   _  ___ _ __(_) ___  ___    |
#   | \___ \| __/ _` | __| | | / __| | | | | | | |/ _ \ '__| |/ _ \/ __|   |
#   |  ___) | || (_| | |_| |_| \__ \ | |_| | |_| |  __/ |  | |  __/\__ \   |
#   | |____/ \__\__,_|\__|\__,_|___/  \__\_\\__,_|\___|_|  |_|\___||___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Parsing and processing of status queries                             |
#   '----------------------------------------------------------------------'


class Queries:
    """Parsing and processing of status queries."""

    def __init__(
        self,
        get_table: Callable[[str], StatusTable],
        sock: socket.socket,
        logger: Logger,
    ) -> None:
        self._get_table = get_table
        self._socket = sock
        self._logger = logger
        self._buffer = b""

    def _query(self, request: bytes) -> Query:
        return Query.make(self._get_table, request.decode("utf-8").splitlines(), self._logger)

    def __iter__(self) -> Iterator[Query]:
        while True:
            parts = self._buffer.split(b"\n\n", 1)
            if len(parts) > 1:
                request, self._buffer = parts
                yield self._query(request)
            else:
                data = self._socket.recv(4096)
                if data:
                    self._buffer += data
                elif self._buffer:
                    request, self._buffer = [self._buffer, b""]
                    yield self._query(request)
                else:
                    break


# .
#   .--Status Tables-------------------------------------------------------.
#   |     ____  _        _               _____     _     _                 |
#   |    / ___|| |_ __ _| |_ _   _ ___  |_   _|_ _| |__ | | ___  ___       |
#   |    \___ \| __/ _` | __| | | / __|   | |/ _` | '_ \| |/ _ \/ __|      |
#   |     ___) | || (_| | |_| |_| \__ \   | | (_| | |_) | |  __/\__ \      |
#   |    |____/ \__\__,_|\__|\__,_|___/   |_|\__,_|_.__/|_|\___||___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class StatusTableEvents(StatusTable):
    name = "events"
    prefix = "event"
    columns: Columns = [
        ("event_id", 1),
        ("event_count", 1),
        ("event_text", ""),
        ("event_first", 0.0),
        ("event_last", 0.0),
        ("event_comment", ""),
        ("event_sl", 0),  # filter fehlt
        ("event_host", ""),
        ("event_contact", ""),
        ("event_application", ""),
        ("event_pid", 0),
        ("event_priority", 5),
        ("event_facility", 1),
        ("event_rule_id", ""),
        ("event_state", 0),
        ("event_phase", ""),
        ("event_owner", ""),
        ("event_match_groups", ""),  # last column up to 1.2.4
        ("event_contact_groups", ""),  # introduced in 1.2.5i2
        ("event_ipaddress", ""),  # introduced in 1.2.7i1
        ("event_orig_host", ""),  # introduced in 1.4.0b1
        ("event_contact_groups_precedence", "host"),  # introduced in 1.4.0b1
        ("event_core_host", ""),  # introduced in 1.5.0i1
        ("event_host_in_downtime", False),  # introduced in 1.5.0i1
        ("event_match_groups_syslog_application", ""),  # introduced in 1.5.0i2
    ]

    def __init__(self, logger: Logger, event_status: EventStatus) -> None:
        super().__init__(logger)
        self._event_status = event_status
        # NOTE: We depend on the dict insertion order below, but this is guaranteed for Python >= 3.7.
        self._columns_dict = dict(self.columns)

    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        for event in self._event_status.get_events():
            # Optimize filters that are set by the check_mkevents active check. Since users
            # may have a lot of those checks running, it is a good idea to optimize this.
            if not query.only_host or filter_operator_in(event["host"], query.only_host):
                yield [
                    event.get(column_name[6:], default)
                    for column_name, default in self._columns_dict.items()
                ]


class StatusTableHistory(StatusTable):
    name = "history"
    prefix = "history"
    columns: Columns = list(
        itertools.chain(
            [
                ("history_line", 0),  # Line number in event history file
                ("history_time", 0.0),
                ("history_what", ""),
                ("history_who", ""),
                ("history_addinfo", ""),
            ],
            StatusTableEvents.columns,
        )
    )

    def __init__(self, logger: Logger, history: History) -> None:
        super().__init__(logger)
        self._history = history

    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return self._history.get(query)


class StatusTableRules(StatusTable):
    name = "rules"
    prefix = "rule"
    columns: Columns = [
        ("rule_id", ""),
        ("rule_hits", 0),
    ]

    def __init__(self, logger: Logger, event_status: EventStatus) -> None:
        super().__init__(logger)
        self._event_status = event_status

    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return self._event_status.get_rule_stats()


class StatusTableStatus(StatusTable):
    name = "status"
    prefix = "status"
    columns: Columns = EventServer.status_columns()

    def __init__(self, logger: Logger, event_server: EventServer) -> None:
        super().__init__(logger)
        self._event_server = event_server

    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return self._event_server.get_status()


# .
#   .--StatusServer--------------------------------------------------------.
#   |     ____  _        _             ____                                |
#   |    / ___|| |_ __ _| |_ _   _ ___/ ___|  ___ _ ____   _____ _ __      |
#   |    \___ \| __/ _` | __| | | / __\___ \ / _ \ '__\ \ / / _ \ '__|     |
#   |     ___) | || (_| | |_| |_| \__ \___) |  __/ |   \ V /  __/ |        |
#   |    |____/ \__\__,_|\__|\__,_|___/____/ \___|_|    \_/ \___|_|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Beantworten von Status- und Kommandoanfragen über das UNIX-Socket   |
#   '----------------------------------------------------------------------'


class StatusServer(ECServerThread):
    """Responding to status and command requests via the UNIX/TCP sockets."""

    def __init__(
        self,
        logger: Logger,
        settings: Settings,
        config: Config,
        slave_status: SlaveStatus,
        perfcounters: Perfcounters,
        lock_configuration: ECLock,
        history: History,
        event_status: EventStatus,
        event_server: EventServer,
        terminate_main_event: threading.Event,
        reload_config_event: threading.Event,
    ) -> None:
        super().__init__(
            name="StatusServer",
            logger=logger,
            settings=settings,
            config=config,
            slave_status=slave_status,
            profiling_enabled=settings.options.profile_status,
            profile_file=settings.paths.status_server_profile.value,
        )
        self._socket: socket.socket | None = None
        self._tcp_socket: socket.socket | None = None
        self._reopen_sockets = False

        self._table_events = StatusTableEvents(logger, event_status)
        self._table_history = StatusTableHistory(logger, history)
        self._table_rules = StatusTableRules(logger, event_status)
        self._table_status = StatusTableStatus(logger, event_server)
        self._perfcounters = perfcounters
        self._lock_configuration = lock_configuration
        self._history = history
        self._event_status = event_status
        self._event_server = event_server
        self._event_columns = StatusTableEvents.columns
        self._terminate_main_event = terminate_main_event
        self._reload_config_event = reload_config_event

        self.open_unix_socket()
        self.open_tcp_socket()

    def table(self, name: str) -> StatusTable:
        if name == "events":
            return self._table_events
        if name == "history":
            return self._table_history
        if name == "rules":
            return self._table_rules
        if name == "status":
            return self._table_status
        raise MKClientError(f"Invalid table: {name} (allowed are: events, history, rules, status)")

    def open_unix_socket(self) -> None:
        path = self.settings.paths.unix_socket.value
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(path))
        # Make sure that socket is group writable
        path.chmod(0o660)
        self._socket.listen(self._config["socket_queue_len"])
        self._unix_socket_queue_len = self._config["socket_queue_len"]  # detect changes in config

    def open_tcp_socket(self) -> None:
        if self._config["remote_status"] is not None:
            try:
                self._tcp_port, self._tcp_allow_commands, networks = self._config["remote_status"]
                try:
                    self._tcp_access_list = (
                        None if networks is None else [ipaddress.ip_network(n) for n in networks]
                    )
                except ValueError as e:
                    self._logger.warning(f"{e}, disabling all TCP access")
                    self._tcp_access_list = []
                try:
                    self._logger.info("Trying to use ipv6 for TCP socket port")
                    self._tcp_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for tcp socket...")
                        self._tcp_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except (AttributeError, OSError):
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for tcp socket"
                        )
                    self._tcp_socket.bind(("::", self._tcp_port))
                except OSError:
                    self._logger.info(
                        "Binding ipv6 failed. Falling back to ipv4 for TCP socket port"
                    )
                    self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._tcp_socket.bind(("0.0.0.0", self._tcp_port))
                self._tcp_socket.listen(self._config["socket_queue_len"])
                self._logger.info(
                    "Going to listen for status queries on TCP port %d", self._tcp_port
                )
            except Exception:
                if self.settings.options.debug:
                    raise
                self._logger.exception("Cannot listen on TCP socket port %d", self._tcp_port)
        else:
            self._tcp_socket = None
            self._tcp_port = 0
            self._tcp_allow_commands = False
            self._tcp_access_list = []

    def close_unix_socket(self) -> None:
        if self._socket:
            self._socket.close()
            self._socket = None

    def close_tcp_socket(self) -> None:
        if self._tcp_socket:
            self._tcp_socket.close()
            self._tcp_socket = None

    def reopen_sockets(self) -> None:
        if self._unix_socket_queue_len != self._config["socket_queue_len"]:
            self._logger.info("socket_queue_len has changed. Reopening UNIX socket.")
            self.close_unix_socket()
            self.open_unix_socket()

        self.close_tcp_socket()
        self.open_tcp_socket()

    def reload_configuration(self, config: Config, history: History) -> None:
        """Reload StatusServer configuration.

        Also the table history is reloaded, because it depends on the history object.
        """
        self._config = config
        self._history = history
        self._table_history = StatusTableHistory(self._logger, self._history)
        self._reopen_sockets = True

    def serve(self) -> None:
        while not self._terminate_event.is_set():
            try:
                client_socket = None
                addr_info = None

                if self._reopen_sockets:
                    self.reopen_sockets()
                    self._reopen_sockets = False

                listen_list = [s for s in (self._socket, self._tcp_socket) if s is not None]
                try:
                    readable: list[socket.socket] = select.select(listen_list, [], [], 0.2)[0]
                except OSError as e:
                    if e.args[0] != errno.EINTR:
                        raise
                    continue

                for s in readable:
                    client_socket, addr_info = s.accept()
                    client_socket.settimeout(3)
                    before = time.time()
                    self._perfcounters.count("connects")
                    if addr_info:
                        allow_commands = self._tcp_allow_commands
                        if self.settings.options.debug:
                            self._logger.info(
                                "Handle status connection from %s:%d", addr_info[0], addr_info[1]
                            )
                        if self._tcp_access_list is not None and not allowed_ip(
                            ipaddress.ip_address(addr_info[0]), self._tcp_access_list
                        ):
                            client_socket.close()
                            client_socket = None
                            self._logger.info(
                                "Denying access to status socket from %s (allowed is only %s)",
                                addr_info[0],
                                ", ".join(str(x) for x in self._tcp_access_list),
                            )
                            continue
                    else:
                        allow_commands = True

                    self.handle_client(
                        client_socket, allow_commands, addr_info and addr_info[0] or ""
                    )

                    duration = time.time() - before
                    self._logger.log(VERBOSE, "Answered request in %0.2f ms", duration * 1000)
                    self._perfcounters.count_time("request", duration)

            except Exception as e:
                msg = f"Error handling client {addr_info}: {e}"
                # Do not log a stack trace for client errors, they are not *our* fault.
                if isinstance(e, MKClientError):
                    self._logger.error(msg)
                else:
                    self._logger.exception(msg)
                if client_socket:
                    client_socket.close()
                    client_socket = None
                time.sleep(0.2)
            client_socket = None  # close without danger of exception

    def handle_client(
        self, client_socket: socket.socket, allow_commands: bool, client_ip: str
    ) -> None:
        for query in Queries(self.table, client_socket, self._logger):
            self._logger.log(VERBOSE, "Client livestatus query: %r", query)

            with self._event_status.lock:
                # TODO: What we really want is a method in Query returning a response instead of this dispatching horror.
                if isinstance(query, QueryGET):
                    response: Response = query.table.query(query)
                elif isinstance(query, QueryREPLICATE):
                    response = self.handle_replicate(query.method_arg, client_ip)
                elif isinstance(query, QueryCOMMAND):
                    self.handle_command_request(query.method_arg, allow_commands)
                    response = None  # pylint and mypy are braindead and don't understand that None is a value
                else:
                    raise NotImplementedError  # can never happen

                try:
                    self._answer_query(client_socket, query, response)
                except OSError as e:
                    if e.errno != errno.EPIPE:
                        raise

        client_socket.close()  # TODO: This should be in a finally somehow.

    def _answer_query(self, client_socket: socket.socket, query: Query, response: Response) -> None:
        """
        Only GET queries have customizable output formats. COMMAND is always
        a dictionary and COMMAND is always None and always output as "python"
        TODO: We should probably nuke these silly cases. Currently the allowed type
        of the response depends on the value of query. :-/.
        """
        if not isinstance(query, QueryGET):
            self._answer_query_python(client_socket, response)
            return
        if response is None:
            raise NotImplementedError  # Make mypy happy

        if query.output_format == "plain":
            for row in response:
                client_socket.sendall(b"\t".join(quote_tab(c) for c in row) + b"\n")

        elif query.output_format == "json":
            client_socket.sendall((json.dumps(list(response)) + "\n").encode("utf-8"))

        elif query.output_format == "python":
            self._answer_query_python(client_socket, list(response))

        else:
            raise NotImplementedError

    def _answer_query_python(self, client_socket: socket.socket, response: Response) -> None:
        client_socket.sendall((repr(response) + "\n").encode("utf-8"))

    # All commands are already locked with self._event_status.lock
    def handle_command_request(self, commandline: str, allow_commands: bool) -> None:
        if not allow_commands:
            raise MKClientError("Sorry. Commands are disallowed via TCP")
        self._logger.info("Executing command: %s", commandline)
        parts = commandline.split(";")
        command = parts[0]
        replication_allow_command(self._config, command, self._slave_status)
        arguments = parts[1:]
        if command == "DELETE":
            self.handle_command_delete(arguments)
        elif command == "DELETE_EVENTS_OF_HOST":
            self.handle_command_delete_events_of_host(arguments)
        elif command == "RELOAD":
            self.handle_command_reload()
        elif command == "SHUTDOWN":
            self._logger.info("Going to shut down")
            terminate(self._terminate_main_event, self._event_server, self)
        elif command == "REOPENLOG":
            self.handle_command_reopenlog()
        elif command == "FLUSH":
            self.handle_command_flush()
        elif command == "SYNC":
            self.handle_command_sync()
        elif command == "RESETCOUNTERS":
            self.handle_command_resetcounters(arguments)
        elif command == "UPDATE":
            self.handle_command_update(arguments)
        elif command == "CREATE":
            self.handle_command_create(arguments)
        elif command == "CHANGESTATE":
            self.handle_command_changestate(arguments)
        elif command == "ACTION":
            self.handle_command_action(arguments)
        elif command == "SWITCHMODE":
            self.handle_command_switchmode(arguments)
        else:
            raise MKClientError(f"Unknown command {command}")

    def handle_command_delete(self, arguments: list[str]) -> None:
        if len(arguments) != 2:
            raise MKClientError("Wrong number of arguments for DELETE")
        event_ids, user = arguments
        ids = {int(event_id) for event_id in event_ids.split(",")}
        self._event_status.delete_events_by(lambda event: event["id"] in ids, user)

    def handle_command_delete_events_of_host(self, arguments: list[str]) -> None:
        if len(arguments) != 2:
            raise MKClientError("Wrong number of arguments for DELETE_EVENTS_OF_HOST")
        hostname, user = arguments
        self._event_status.delete_events_by(lambda event: event["host"] == hostname, user)

    def handle_command_update(self, arguments: list[str]) -> None:
        event_ids, user, acknowledged, comment, contact = arguments
        failures = list[str]()
        for event_id in event_ids.split(","):
            event = self._event_status.event(int(event_id))
            if not event:
                failures.append(f"No event with id {event_id}.")
                continue
            if acknowledged:
                if not int(acknowledged):
                    event["phase"] = "open"
                elif event["phase"] in {"open", "ack"}:
                    event["phase"] = "ack"
                else:
                    failures.append(
                        f"You cannot acknowledge event {event_id}, it is {event['phase']}."
                    )
                    continue
            if comment:
                event["comment"] = comment
            if contact:
                event["contact"] = contact
            if user:
                event["owner"] = user
            self._history.add(event, "UPDATE", user)
        if failures:
            raise MKClientError(" ".join(failures))

    def handle_command_create(self, arguments: list[str]) -> None:
        # Would rather use process_syslog_messages(), but we are already
        # holding self._event_status.lock and it's sub functions are setting
        # self._event_status.lock too. The lock can not be allocated twice.
        with open(str(self.settings.paths.event_pipe.value), "wb") as pipe:
            pipe.write(f"{';'.join(arguments)}\n".encode())

    def handle_command_changestate(self, arguments: list[str]) -> None:
        event_ids, user, newstate = arguments
        failures = list[str]()
        for event_id in event_ids.split(","):
            event = self._event_status.event(int(event_id))
            if not event:
                failures.append(f"No event with id {event_id}.")
                continue
            event["state"] = int(newstate)
            if user:
                event["owner"] = user
            self._history.add(event, "CHANGESTATE", user)
        if failures:
            raise MKClientError(" ".join(failures))

    def handle_command_reload(self) -> None:
        self._reload_config_event.set()

    def handle_command_reopenlog(self) -> None:
        self._logger.info("Closing this logfile")
        open_log(self.settings.paths.log_file.value)
        self._logger.info("Opened new logfile")

    def handle_command_flush(self) -> None:
        """Erase our current state and history!."""
        self._history.flush()
        self._event_status.flush()
        self._event_status.save_status()
        if is_replication_slave(self._config):
            with contextlib.suppress(Exception):
                self.settings.paths.master_config_file.value.unlink()
                self.settings.paths.slave_status_file.value.unlink()
                update_slave_status(self._slave_status, self.settings, self._config)
        self._logger.info("Flushed current status and historic events.")

    def handle_command_sync(self) -> None:
        self._event_status.save_status()

    def handle_command_resetcounters(self, arguments: list[str]) -> None:
        if arguments:
            self._logger.info("Resetting counters of rule %s", arguments[0])
            self._event_status.reset_counters(arguments[0])
        else:
            self._logger.info("Resetting all rule counters")
            self._event_status.reset_counters(None)

    def handle_command_action(self, arguments: list[str]) -> None:
        event_ids, user, action_id = arguments
        for event_id in event_ids.split(","):
            event: Event | None = self._event_status.event(int(event_id))
            if user and event is not None:
                event["owner"] = user

            # TODO: De-duplicate code from do_event_actions()
            if action_id == "@NOTIFY" and event is not None:
                do_notify(
                    self._event_server.host_config, self._logger, event, user, is_cancelling=False
                )
            else:
                # TODO: This locking doesn't make sense: We use the config outside of the lock below, too.
                with self._lock_configuration:
                    actions = self._config["action"]
                    if action_id not in actions:
                        raise MKClientError(
                            f"The action '{action_id}' is not defined. After adding new commands please "
                            "make sure that you activate the changes in the Event Console."
                        )
                    action = actions[action_id]
                if event:
                    do_event_action(
                        self._history,
                        self.settings,
                        self._config,
                        self._logger,
                        self._event_columns,
                        action,
                        event,
                        user,
                    )

    def handle_command_switchmode(self, arguments: list[str]) -> None:
        new_mode = arguments[0]
        if not is_replication_slave(self._config):
            raise MKClientError("Cannot switch replication mode: this is not a replication slave.")
        if new_mode == "sync":
            self._slave_status["mode"] = "sync"
        elif new_mode == "takeover":
            self._slave_status["mode"] = "takeover"
        else:
            raise MKClientError(
                f"Invalid target mode {new_mode}: allowed are only 'sync' and 'takeover'"
            )
        save_slave_status(self.settings, self._slave_status)
        self._logger.info("Switched replication mode to '%s' by external command.", new_mode)

    def handle_replicate(self, argument: str, client_ip: str) -> Response:
        # Last time our slave got a config update
        try:
            last_update = int(argument)
            if self.settings.options.debug:
                self._logger.info(
                    "Replication: sync request from %s, last update %d seconds ago",
                    client_ip,
                    time.time() - last_update,
                )

        except (ValueError, OverflowError) as e:
            raise MKClientError("Invalid arguments to command REPLICATE") from e
        return replication_send(
            self._config, self._lock_configuration, self._event_status, last_update
        )


# .
#   .--Dispatching---------------------------------------------------------.
#   |         ____  _                 _       _     _                      |
#   |        |  _ \(_)___ _ __   __ _| |_ ___| |__ (_)_ __   __ _          |
#   |        | | | | / __| '_ \ / _` | __/ __| '_ \| | '_ \ / _` |         |
#   |        | |_| | \__ \ |_) | (_| | || (__| | | | | | | | (_| |         |
#   |        |____/|_|___/ .__/ \__,_|\__\___|_| |_|_|_| |_|\__, |         |
#   |                    |_|                                |___/          |
#   +----------------------------------------------------------------------+
#   |  Starten und Verwalten der beiden Threads.                           |
#   '----------------------------------------------------------------------'


def run_eventd(
    terminate_main_event: threading.Event,
    settings: Settings,
    config: Config,
    lock_configuration: ECLock,
    history: History,
    perfcounters: Perfcounters,
    event_status: EventStatus,
    event_server: EventServer,
    status_server: StatusServer,
    slave_status: SlaveStatus,
    logger: Logger,
    reload_config_event: threading.Event,
) -> None:
    """Dispatching: starting and managing the two threads."""
    status_server.start()
    event_server.start()
    now = time.time()
    next_housekeeping = now + config["housekeeping_interval"]
    next_retention = now + config["retention_interval"]
    next_statistics = now + config["statistics_interval"]
    next_replication = 0.0  # force immediate replication after restart

    while not terminate_main_event.is_set():
        try:
            try:
                # Wait until either housekeeping or retention is due, but at
                # maximum 60 seconds. That way changes of the interval from a very
                # high to a low value will never require more than 60 seconds

                event_list = [next_housekeeping, next_retention, next_statistics]
                if is_replication_slave(config):
                    event_list.append(next_replication)

                time_left = max(0, min(event_list) - time.time())
                reload_config_event.wait(min(time_left, 60))
                now = time.time()

                if reload_config_event.is_set():
                    reload_config_event.clear()
                    history = reload_configuration(
                        settings,
                        getLogger("cmk.mkeventd"),
                        lock_configuration,
                        history,
                        event_status,
                        event_server,
                        status_server,
                        slave_status,
                    )

                if now > next_housekeeping:
                    event_server.do_housekeeping()
                    next_housekeeping = now + config["housekeeping_interval"]

                if now > next_retention:
                    with event_status.lock:
                        event_status.save_status()
                    next_retention = now + config["retention_interval"]

                if now > next_statistics:
                    perfcounters.do_statistics()
                    next_statistics = now + config["statistics_interval"]

                # Beware: replication might be turned on during this loop!
                if is_replication_slave(config) and now > next_replication:
                    replication_pull(
                        settings,
                        config,
                        lock_configuration,
                        perfcounters,
                        event_status,
                        event_server,
                        slave_status,
                        logger,
                    )
                    replication_settings = config["replication"]
                    if replication_settings is None:  # help mypy a bit
                        raise ValueError("no replication settings")
                    next_replication = now + replication_settings["interval"]
            except MKSignalException as e:
                raise e
            except Exception:
                logger.exception("Exception in main thread")
                if settings.options.debug:
                    raise
                time.sleep(1)
        except MKSignalException as e:
            if e.signum == 1:
                logger.info("Received SIGHUP - going to reload configuration")
                history = reload_configuration(
                    settings,
                    logger,
                    lock_configuration,
                    history,
                    event_status,
                    event_server,
                    status_server,
                    slave_status,
                )
            else:
                logger.info("Signalled to death by signal %d", e.signum)
                terminate(terminate_main_event, event_server, status_server)

    # Now wait for termination of the server threads
    event_server.join()
    status_server.join()


# .
#   .--EventStatus---------------------------------------------------------.
#   |       _____                 _   ____  _        _                     |
#   |      | ____|_   _____ _ __ | |_/ ___|| |_ __ _| |_ _   _ ___         |
#   |      |  _| \ \ / / _ \ '_ \| __\___ \| __/ _` | __| | | / __|        |
#   |      | |___ \ V /  __/ | | | |_ ___) | || (_| | |_| |_| \__ \        |
#   |      |_____| \_/ \___|_| |_|\__|____/ \__\__,_|\__|\__,_|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Bereithalten des aktuellen Event-Status. Dieser schützt sich selbst  |
#   | durch ein Lock vor gleichzeitigen Zugriffen durch die Threads.       |
#   '----------------------------------------------------------------------'


class EventStatus:
    """
    Keeps the current Event-Status.
    This protects itself by a lock from simultaneous accesses by the threads.
    """

    def __init__(
        self,
        settings: Settings,
        config: Config,
        perfcounters: Perfcounters,
        history: History,
        logger: Logger,
    ) -> None:
        self.settings = settings
        self._config = config
        self._perfcounters = perfcounters
        self.lock = threading.Lock()
        self._history = history
        self._logger = logger
        self.flush()

    def reload_configuration(self, config: Config, history: History) -> None:
        self._config = config
        self._history = history

    def flush(self) -> None:
        # TODO: Improve types!
        self._events: list[Event] = []
        self._next_event_id = 1
        self._rule_stats: dict[str, int] = {}
        # needed for expecting rules
        self._interval_starts: dict[str, int] = {}
        self._initialize_event_limit_status()

        # TODO: might introduce some performance counters, like:
        # - number of received messages
        # - number of rule hits
        # - number of rule misses

    def events(self) -> list[Event]:
        # TODO: Improve type!
        return self._events

    def event(self, eid: int) -> Event | None:
        for event in self._events:
            if event["id"] == eid:
                return event
        return None

    def interval_start(self, rule_id: str, interval: ExpectInterval) -> int:
        """
        Return beginning of current expectation interval. For new rules
        we start with the next interval in future.
        """
        if rule_id not in self._interval_starts:
            start = self.next_interval_start(interval, time.time())
            self._interval_starts[rule_id] = start
            return start
        start = self._interval_starts[rule_id]
        # Make sure that if the user switches from day to hour and we
        # are still waiting for the first interval to begin, that we
        # do not wait for the next day.
        next_interval = self.next_interval_start(interval, time.time())
        if start > next_interval:
            start = next_interval
            self._interval_starts[rule_id] = start
        return start

    def next_interval_start(self, interval: ExpectInterval, previous_start: float) -> int:
        length, offset = interval if isinstance(interval, tuple) else (interval, 0)
        offset *= 3600

        previous_start -= offset  # take into account timezone offset
        full_parts = divmod(previous_start, length)[0]
        next_start = (full_parts + 1) * length
        next_start += offset
        return int(next_start)

    def start_next_interval(self, rule_id: str, interval: ExpectInterval) -> None:
        current_start = self.interval_start(rule_id, interval)
        next_start = self.next_interval_start(interval, current_start)
        self._interval_starts[rule_id] = next_start
        self._logger.debug(
            "Rule %s: next interval starts %s (i.e. now + %.2f sec)",
            rule_id,
            next_start,
            time.time() - next_start,
        )

    def pack_status(self) -> PackedEventStatus:
        return PackedEventStatus(
            next_event_id=self._next_event_id,
            events=self._events,
            rule_stats=self._rule_stats,
            interval_starts=self._interval_starts,
        )

    def unpack_status(self, status: PackedEventStatus) -> None:
        self._next_event_id = status["next_event_id"]
        self._events = status["events"]
        self._rule_stats = status["rule_stats"]
        self._interval_starts = status["interval_starts"]

    def save_status(self) -> None:
        now = time.time()
        status = self.pack_status()
        path = self.settings.paths.status_file.value
        path_new = path.parent / (path.name + ".new")
        # Believe it or not: cPickle is more than two times slower than repr()
        with path_new.open(mode="wb") as f:
            f.write((repr(status) + "\n").encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        path_new.rename(path)
        elapsed = time.time() - now
        self._logger.log(VERBOSE, "Saved event state to %s in %.3fms.", path, elapsed * 1000)

    def reset_counters(self, rule_id: str | None) -> None:
        if rule_id:
            if rule_id in self._rule_stats:
                del self._rule_stats[rule_id]
        else:
            self._rule_stats = {}
        self.save_status()

    def load_status(self, event_server: EventServer) -> None:
        path = self.settings.paths.status_file.value
        if path.exists():
            try:
                status = ast.literal_eval(path.read_text(encoding="utf-8"))
                self._next_event_id = status["next_event_id"]
                self._events = status["events"]
                self._rule_stats = status["rule_stats"]
                self._interval_starts = status.get("interval_starts", {})
                self._logger.info("Loaded event state from %s.", path)
            except Exception:
                self._logger.exception("Error loading event state from %s", path)
                raise

        # Add new columns and fix broken events
        for event in self._events:
            event.setdefault("ipaddress", "")
            event.setdefault("host", HostName(""))
            event.setdefault("application", "")
            event.setdefault("pid", 0)

            if "core_host" not in event:
                event_server.add_core_host_to_event(event)
                event["host_in_downtime"] = False

        # core_host is needed to initialize the status
        self._initialize_event_limit_status()

    def _initialize_event_limit_status(self) -> None:
        """
        Called on Event Console initialization from status file to initialize
        the current event limit state -> Sets internal counters which are
        updated during runtime.
        """
        self.num_existing_events = len(self._events)

        self.num_existing_events_by_host: dict[tuple[str, HostName | None], int] = {}
        self.num_existing_events_by_rule: dict[Any, int] = {}
        for event in self._events:
            self._count_event_add(event)

    def _count_event_add(self, event: Event) -> None:
        host_key = (event["host"], event["core_host"])
        if host_key not in self.num_existing_events_by_host:
            self.num_existing_events_by_host[host_key] = 1
        else:
            self.num_existing_events_by_host[host_key] += 1

        if event["rule_id"] not in self.num_existing_events_by_rule:
            self.num_existing_events_by_rule[event["rule_id"]] = 1
        else:
            self.num_existing_events_by_rule[event["rule_id"]] += 1

    def _count_event_remove(self, event: Event) -> None:
        host_key = (event["host"], event["core_host"])

        self.num_existing_events -= 1
        self.num_existing_events_by_host[host_key] -= 1
        self.num_existing_events_by_rule[event["rule_id"]] -= 1

    def new_event(self, event: Event) -> None:
        self._perfcounters.count("events")
        event["id"] = self._next_event_id
        self._next_event_id += 1
        self._events.append(event)
        self.num_existing_events += 1
        self._count_event_add(event)
        self._history.add(event, "NEW")

    def archive_event(self, event: Event) -> None:
        self._perfcounters.count("events")
        event["id"] = self._next_event_id
        self._next_event_id += 1
        event["phase"] = "closed"
        self._history.add(event, "ARCHIVED")

    def remove_event(self, event: Event, delete_reason: HistoryWhat, user: str = "") -> None:
        try:
            self._events.remove(event)
            self._history.add(event, delete_reason, user)
            self._count_event_remove(event)
        except ValueError:
            self._logger.exception("Cannot remove event %d: not present", event["id"])

    # protected by self.lock
    def remove_oldest_event(self, ty: LimitKind, event: Event) -> None:
        if ty == "overall":
            self._logger.log(VERBOSE, "  Removing oldest event")
            oldest_event = self._events[0]
            self.remove_event(oldest_event, "AUTODELETE")
        elif ty == "by_rule" and event["rule_id"] is not None:
            self._logger.log(VERBOSE, '  Removing oldest event of rule "%s"', event["rule_id"])
            self._remove_oldest_event_of_rule(event["rule_id"])
        elif ty == "by_host" and event["host"] is not None:
            self._logger.log(VERBOSE, '  Removing oldest event of host "%s"', event["host"])
            self._remove_oldest_event_of_host(event["host"])

    # protected by self.lock
    def _remove_oldest_event_of_rule(self, rule_id: str) -> None:
        for event in self._events:
            if event["rule_id"] == rule_id:
                self.remove_event(event, "AUTODELETE")
                return

    # protected by self.lock
    def _remove_oldest_event_of_host(self, hostname: str) -> None:
        for event in self._events:
            if event["host"] == hostname:
                self.remove_event(event, "AUTODELETE")
                return

    # protected by self.lock
    def get_num_existing_events_by(self, ty: LimitKind, event: Event) -> int:
        match ty:
            case "overall":
                return self.num_existing_events
            case "by_rule":
                return self.num_existing_events_by_rule.get(event["rule_id"], 0)
            case "by_host":
                return self.num_existing_events_by_host.get((event["host"], event["core_host"]), 0)
            case _ as unreachable:
                assert_never(unreachable)

    def cancel_events(
        self,
        event_server: EventServer,
        event_columns: Iterable[tuple[str, object]],
        new_event: Event,
        match_groups: MatchGroups,
        rule: Rule,
    ) -> None:
        """
        Cancel all events the belong to a certain rule id and are
        of the same "breed" as a new event.
        """
        with self.lock:
            to_delete = []
            for event in self._events:
                if event["rule_id"] == rule["id"] and self.cancelling_match(
                    match_groups, new_event, event, rule
                ):
                    # Fill a few fields of the cancelled event with data from
                    # the cancelling event so that action scripts have useful
                    # values and the logfile entry if more relevant.
                    previous_phase = event["phase"]
                    event["phase"] = "closed"
                    # TODO: Why do we use OK below and not new_event["state"]???
                    event["state"] = 0  # OK
                    event["text"] = new_event["text"]
                    # TODO: This is a hack and partial copy-n-paste from rewrite_events...
                    if "set_text" in rule:
                        event["text"] = replace_groups(
                            rule["set_text"], event["text"], match_groups
                        )
                    event["time"] = new_event["time"]
                    event["last"] = new_event["time"]
                    event["priority"] = new_event["priority"]
                    actions = rule.get("cancel_actions", [])
                    if actions:
                        if (
                            previous_phase != "open"
                            and rule.get("cancel_action_phases", "always") == "open"
                        ):
                            self._logger.info(
                                "Do not execute cancelling actions, event %s's phase "
                                "is not 'open' but '%s'",
                                event["id"],
                                previous_phase,
                            )
                        else:
                            do_event_actions(
                                self._history,
                                self.settings,
                                self._config,
                                self._logger,
                                event_server.host_config,
                                event_columns,
                                actions,
                                event,
                                is_cancelling=True,
                            )

                    to_delete.append(event)

            for e in to_delete:
                self.remove_event(e, "CANCELLED")

    def cancelling_match(
        self, match_groups: MatchGroups, new_event: Event, event: Event, rule: Rule
    ) -> bool:
        debug = self._config["debug_rules"]

        # The match_groups of the canceling match only contain the *_ok match groups
        # Since the rewrite definitions are based on the positive match, we need to
        # create some missing keys. O.o
        match_groups["match_groups_message"] = match_groups.get("match_groups_message_ok", ())
        match_groups["match_groups_syslog_application"] = match_groups.get(
            "match_groups_syslog_application_ok", ()
        )

        # Note: before we compare host and application we need to
        # apply the rewrite rules to the event. Because if in the previous
        # the hostname was rewritten, it wouldn't match anymore here.
        host = new_event["host"]
        if "set_host" in rule:
            host = HostName(replace_groups(rule["set_host"], host, match_groups))

        if event["host"] != host:
            if debug:
                self._logger.info(
                    "Do not cancel event %d: host is not the same (%s != %s)",
                    event["id"],
                    event["host"],
                    host,
                )
            return False

        # The same for the application. But in case there is cancelling based on the application
        # configured in the rule, then don't check for different applications.
        if "cancel_application" not in rule:
            application = new_event["application"]
            if "set_application" in rule:
                application = replace_groups(rule["set_application"], application, match_groups)
            if event["application"] != application:
                if debug:
                    self._logger.info(
                        "Do not cancel event %d: application is not the same (%s != %s)",
                        event["id"],
                        event["application"],
                        application,
                    )
                return False

        if event["facility"] != new_event["facility"] and debug:
            self._logger.info(
                "Do not cancel event %d: syslog facility is not the same (%d != %d)",
                event["id"],
                event["facility"],
                new_event["facility"],
            )

        # Make sure, that the matching groups are the same. If the OK match
        # has less groups, we do not care. If it has more groups, then we
        # do not care either. We just compare the common "prefix".
        groups_message_ok = match_groups.get("match_groups_message_ok", ())
        assert groups_message_ok is not False
        for nr, (prev_group, cur_group) in enumerate(
            zip(
                event["match_groups"],
                groups_message_ok,
                strict=False,
            )
        ):
            if prev_group != cur_group:
                if debug:
                    self._logger.info(
                        "Do not cancel event %d: match group number %d does not match (%s != %s)",
                        event["id"],
                        nr + 1,
                        prev_group,
                        cur_group,
                    )
                return False

        # Note: Duplicated code right above
        # Make sure, that the syslog_application matching groups are the same. If the OK match
        # has less groups, we do not care. If it has more groups, then we
        # do not care either. We just compare the common "prefix".
        groups_syslog_ok = match_groups.get("match_groups_syslog_application_ok", ())
        assert groups_syslog_ok is not False
        for nr, (prev_group, cur_group) in enumerate(
            zip(
                event.get("match_groups_syslog_application", ()),
                groups_syslog_ok,
                strict=False,
            )
        ):
            if prev_group != cur_group:
                if debug:
                    self._logger.info(
                        "Do not cancel event %d: syslog application match group number "
                        "%d does not match (%s != %s)",
                        event["id"],
                        nr + 1,
                        prev_group,
                        cur_group,
                    )
                return False

        return True

    def count_rule_match(self, rule_id: str) -> None:
        with self.lock:
            self._rule_stats.setdefault(rule_id, 0)
            self._rule_stats[rule_id] += 1

    def count_event_up(self, found: Event, event: Event) -> None:
        """
        Update event with new information from new occurrence,
        but preserve certain attributes from the original (first)
        event.
        """
        preserve = Event(count=found.get("count", 1) + 1, first=found["first"])
        # When event is already active then do not change
        # comment or contact information anymore
        if found["phase"] == "open":
            if "comment" in found:
                preserve["comment"] = found["comment"]
            if "contact" in found:
                preserve["contact"] = found["contact"]
        found.update(event)
        found.update(preserve)

    def count_expected_event(self, event_server: EventServer, event: Event) -> None:
        for ev in self._events:
            if ev["rule_id"] == event["rule_id"] and ev["phase"] == "counting":
                self.count_event_up(ev, event)
                return

        # None found, create one
        event["count"] = 1
        event["phase"] = "counting"
        event_server.new_event_respecting_limits(event)

    def count_event(self, event_server: EventServer, event: Event, count: Count) -> Event | None:
        """
        Find previous occurrence of this event and account for
        one new occurrence. In case of negated count (expecting rules)
        we do never modify events that are already in the state "open"
        since the event has been created because the count was too
        low in the specified period of time.
        """
        for ev in self._events:
            if ev["rule_id"] == event["rule_id"]:
                if ev["phase"] == "ack" and not count["count_ack"]:
                    continue  # skip acknowledged events

                if count["separate_host"] and ev["host"] != event["host"]:
                    continue  # treat events with separated hosts separately

                if count["separate_application"] and ev["application"] != event["application"]:
                    continue  # same for application

                if count["separate_match_groups"] and ev["match_groups"] != event["match_groups"]:
                    continue

                count_duration = count.get("count_duration")
                if count_duration is not None and ev["first"] + count_duration < event["time"]:
                    # Counting has been discontinued on this event after a certain time
                    continue

                if ev["host_in_downtime"] != event["host_in_downtime"]:
                    continue  # treat events with different downtime states separately

                found = ev
                self.count_event_up(found, event)
                break
        else:
            event["count"] = 1
            event["phase"] = "counting"
            event_server.new_event_respecting_limits(event)
            found = event

        # Did we just count the event that was just one too much?
        if found["phase"] == "counting" and found["count"] >= count["count"]:
            found["phase"] = "open"
            return found  # do event action, return found copy of event
        return None  # do not do event action

    def delete_events_by(self, predicate: Callable[[Event], bool], user: str) -> None:
        for event in self._events[:]:
            if predicate(event):
                event["phase"] = "closed"
                if user:
                    event["owner"] = user
                self.remove_event(event, "DELETE", user)

    def get_events(self) -> Iterable[Event]:
        return self._events

    def get_rule_stats(self) -> Iterable[tuple[str, int]]:
        return sorted(self._rule_stats.items(), key=lambda x: x[0])


# .
#   .--Replication---------------------------------------------------------.
#   |           ____            _ _           _   _                        |
#   |          |  _ \ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __             |
#   |          | |_) / _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \            |
#   |          |  _ <  __/ |_) | | | (_| (_| | |_| | (_) | | | |           |
#   |          |_| \_\___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|           |
#   |                    |_|                                               |
#   +----------------------------------------------------------------------+
#   |  Functions for doing replication, master and slave parts.            |
#   '----------------------------------------------------------------------'


def is_replication_slave(config: ConfigFromWATO) -> bool:
    repl_settings = config["replication"]
    return repl_settings is not None and not repl_settings.get("disabled")


def replication_allow_command(config: Config, command: str, slave_status: SlaveStatus) -> None:
    if (
        is_replication_slave(config)
        and slave_status["mode"] == "sync"
        and command in {"DELETE", "UPDATE", "CHANGESTATE", "ACTION"}
    ):
        raise MKClientError(
            "This command is not allowed on a replication slave while it is in sync mode."
        )


def replication_send(
    config: Config, lock_configuration: ECLock, event_status: EventStatus, last_update: int
) -> Mapping[str, object]:
    response: dict[str, object] = {}
    with lock_configuration:
        response["status"] = event_status.pack_status()
        if last_update < config["last_reload"]:
            response["rules"] = config[
                "rules"
            ]  # Remove one bright day, where legacy rules are not needed anymore
            response["rule_packs"] = config["rule_packs"]
            response["actions"] = config["actions"]
        return response


def replication_pull(
    settings: Settings,
    config: Config,
    lock_configuration: ECLock,
    perfcounters: Perfcounters,
    event_status: EventStatus,
    event_server: EventServer,
    slave_status: SlaveStatus,
    logger: Logger,
) -> None:
    """
    We distinguish two modes:
    1. slave mode: just pull the current state from the master.
       if the master is not reachable then decide whether to
       switch to takeover mode.
    2. takeover mode: if automatic fallback is enabled and the
       time frame for that has not yet elapsed, then try to
       pull the current state from the master. If that is successful
       then switch back to slave mode. If not automatic fallback
       is enabled then simply do nothing.
    """
    now = time.time()
    repl_settings = config["replication"]
    if repl_settings is None:
        raise ValueError("no replication settings")
    mode = slave_status["mode"]
    need_sync = mode == "sync" or (
        mode == "takeover"
        and "fallback" in repl_settings
        and (
            slave_status["last_master_down"] is None
            or now - repl_settings["fallback"] < slave_status["last_master_down"]
        )
    )

    if need_sync:
        with event_status.lock, lock_configuration:
            try:
                new_state = get_state_from_master(config, slave_status)
                replication_update_state(settings, config, event_status, event_server, new_state)
                if repl_settings.get("logging"):
                    logger.info("Successfully synchronized with master")
                slave_status["last_sync"] = now
                slave_status["success"] = True

                # Fall back to slave mode after successful sync
                # (time frame has already been checked)
                if mode == "takeover":
                    if slave_status["last_master_down"] is None:
                        logger.info(
                            "Replication: master reachable for the first time, "
                            "switching back to slave mode"
                        )
                        slave_status["mode"] = "sync"
                    else:
                        logger.info(
                            "Replication: master reachable again after %d seconds, "
                            "switching back to sync mode",
                            (now - slave_status["last_master_down"]),
                        )
                        slave_status["mode"] = "sync"
                slave_status["last_master_down"] = None

            except Exception:
                logger.warning("Replication: cannot sync with master", exc_info=True)
                slave_status["success"] = False
                if slave_status["last_master_down"] is None:
                    slave_status["last_master_down"] = now

                # Takeover
                if "takeover" in repl_settings and mode != "takeover":
                    if not slave_status["last_sync"]:
                        if repl_settings.get("logging"):
                            logger.error("Replication: no takeover since master was never reached.")
                    else:
                        offline = now - slave_status["last_sync"]
                        if offline < repl_settings["takeover"]:
                            if repl_settings.get("logging"):
                                logger.warning(
                                    "Replication: no takeover yet, still %d seconds to wait",
                                    repl_settings["takeover"] - offline,
                                )
                        else:
                            logger.info(
                                "Replication: master not reached for %d seconds, taking over!",
                                offline,
                            )
                            slave_status["mode"] = "takeover"

            save_slave_status(settings, slave_status)

            # Compute statistics of the average time needed for a sync
            perfcounters.count_time("sync", time.time() - now)


def replication_update_state(
    settings: Settings,
    config: Config,
    event_status: EventStatus,
    event_server: EventServer,
    new_state: dict[str, Any],
) -> None:
    # Keep a copy of the masters' rules and actions and also prepare using them
    if "rules" in new_state:
        save_master_config(settings, new_state)
        event_server.compile_rules(new_state.get("rule_packs", []))
        config["actions"] = new_state["actions"]

    # Update to the masters' event state
    event_status.unpack_status(new_state["status"])


def save_master_config(settings: Settings, new_state: Mapping[str, object]) -> None:
    path = settings.paths.master_config_file.value
    path_new = path.parent / (path.name + ".new")
    path_new.write_text(
        repr(
            {
                "rules": new_state["rules"],
                "rule_packs": new_state["rule_packs"],
                "actions": new_state["actions"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    path_new.rename(path)


def load_master_config(settings: Settings, config: ConfigFromWATO, logger: Logger) -> None:
    path = settings.paths.master_config_file.value
    try:
        master_config = ast.literal_eval(path.read_text(encoding="utf-8"))
        config["rules"] = master_config["rules"]
        config["rule_packs"] = master_config.get("rule_packs", [])
        config["actions"] = master_config["actions"]
        logger.info(
            "Replication: restored %d rule packs and %d actions from %s",
            len(config["rule_packs"]),
            len(config["actions"]),
            path,
        )
    except Exception:
        if is_replication_slave(config):
            logger.error("Replication: no previously saved master state available")


def get_state_from_master(config: Config, slave_status: SlaveStatus) -> Any:
    repl_settings = config["replication"]
    if repl_settings is None:
        raise ValueError("no replication settings")
    response_text = b""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(repl_settings["connect_timeout"])
        sock.connect(repl_settings["master"])
        sock.sendall(
            b"REPLICATE %d\n" % (slave_status["last_sync"] if slave_status["last_sync"] else 0)
        )
        sock.shutdown(socket.SHUT_WR)

        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return ast.literal_eval(response_text.decode("utf-8"))
    except SyntaxError as e:
        raise Exception(
            f"Invalid response from event daemon: <pre>{repr(response_text)}</pre>"
        ) from e

    except OSError as e:
        raise Exception("Master not responding") from e

    except Exception as e:
        raise Exception("Cannot connect to event daemon") from e


def save_slave_status(settings: Settings, slave_status: SlaveStatus) -> None:
    settings.paths.slave_status_file.value.write_text(repr(slave_status) + "\n", encoding="utf-8")


def default_slave_status_master() -> SlaveStatus:
    return SlaveStatus(
        last_sync=0,
        last_master_down=None,
        mode="master",
        success=True,
    )


def default_slave_status_sync() -> SlaveStatus:
    return SlaveStatus(
        last_sync=0,
        last_master_down=None,
        mode="sync",
        success=True,
    )


def update_slave_status(
    slave_status: SlaveStatus, settings: Settings, config: ConfigFromWATO
) -> None:
    path = settings.paths.slave_status_file.value
    if is_replication_slave(config):
        try:
            slave_status.update(ast.literal_eval(path.read_text(encoding="utf-8")))
        except Exception:
            slave_status = default_slave_status_sync()
            save_slave_status(settings, slave_status)
    else:
        if path.exists():
            path.unlink()
        slave_status = default_slave_status_master()


# .
#   .--Configuration-------------------------------------------------------.
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+
#   |  Loading of the configuration files                                  |
#   '----------------------------------------------------------------------'


def make_config(config: ConfigFromWATO) -> Config:
    return Config(
        **config,
        action={action["id"]: action for action in config["actions"]},
        last_reload=int(time.time()),
    )


def load_configuration(settings: Settings, logger: Logger, slave_status: SlaveStatus) -> Config:
    config = load_active_config(settings)
    # If not set by command line, set the log level by configuration
    if settings.options.verbosity == 0:
        levels = config["log_level"]
        logger.setLevel(levels["cmk.mkeventd"])
        logger.getChild("EventServer").setLevel(levels["cmk.mkeventd.EventServer"])
        if "cmk.mkeventd.EventServer.snmp" in levels:
            logger.getChild("EventServer.snmp").setLevel(levels["cmk.mkeventd.EventServer.snmp"])
        logger.getChild("EventStatus").setLevel(levels["cmk.mkeventd.EventStatus"])
        logger.getChild("StatusServer").setLevel(levels["cmk.mkeventd.StatusServer"])
        logger.getChild("lock").setLevel(levels["cmk.mkeventd.lock"])
    # Are we a replication slave? Parts of the configuration will be overridden by values from the master.
    update_slave_status(slave_status, settings, config)
    if is_replication_slave(config):
        logger.info("Replication: slave configuration, current mode: %s", slave_status["mode"])
    load_master_config(settings, config, logger)
    return make_config(config)


def reload_configuration(
    settings: Settings,
    logger: Logger,
    lock_configuration: ECLock,
    history: History,
    event_status: EventStatus,
    event_server: EventServer,
    status_server: StatusServer,
    slave_status: SlaveStatus,
) -> History:
    with lock_configuration:
        config = load_configuration(settings, logger, slave_status)

        history.close()
        history = create_history(
            settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
        )
        event_server.reload_configuration(config, history)

    event_status.reload_configuration(config, history)
    status_server.reload_configuration(config, history)
    logger.info("Reloaded configuration.")
    return history


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Main entry and option parsing                                       |
#   '----------------------------------------------------------------------'


def main() -> None:
    """Main entry and option parsing."""
    os.unsetenv("LANG")
    logger = getLogger("cmk.mkeventd")
    settings = create_settings(cmk_version.__version__, cmk.utils.paths.omd_root, sys.argv)

    pid_path = None
    try:
        log.setup_logging_handler(sys.stderr)
        log.logger.setLevel(log.verbosity_to_log_level(settings.options.verbosity))

        settings.paths.log_file.value.parent.mkdir(parents=True, exist_ok=True)
        if not settings.options.foreground:
            open_log(settings.paths.log_file.value)

        logger.info("-" * 65)
        logger.info("mkeventd version %s starting", cmk_version.__version__)

        slave_status = default_slave_status_master()
        config = load_configuration(settings, logger, slave_status)
        history = create_history(
            settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
        )

        pid_path = settings.paths.pid_file.value
        if pid_path.exists():
            old_pid = int(pid_path.read_text(encoding="utf-8"))
            if process_exists(old_pid):
                bail_out(
                    logger,
                    "Old PID file %s still existing and mkeventd still running with PID %d."
                    % (pid_path, old_pid),
                )
            pid_path.unlink()
            logger.info(
                "Removed orphaned PID file %s (process %d not running anymore).", pid_path, old_pid
            )

        # Make sure paths exist
        settings.paths.event_pipe.value.parent.mkdir(parents=True, exist_ok=True)
        settings.paths.event_pipe.value.parent.chmod(0o751)
        settings.paths.status_file.value.parent.mkdir(parents=True, exist_ok=True)

        # First do all things that might fail, before daemonizing
        perfcounters = Perfcounters(logger.getChild("lock.perfcounters"))
        event_status = EventStatus(
            settings, config, perfcounters, history, logger.getChild("EventStatus")
        )
        lock_configuration = ECLock(logger.getChild("lock.configuration"))
        event_server = EventServer(
            logger.getChild("EventServer"),
            settings,
            config,
            slave_status,
            perfcounters,
            lock_configuration,
            history,
            event_status,
            StatusTableEvents.columns,
        )
        terminate_main_event = threading.Event()
        reload_config_event = threading.Event()
        status_server = StatusServer(
            logger.getChild("StatusServer"),
            settings,
            config,
            slave_status,
            perfcounters,
            lock_configuration,
            history,
            event_status,
            event_server,
            terminate_main_event,
            reload_config_event,
        )

        event_status.load_status(event_server)
        event_server.compile_rules(config["rule_packs"])

        if not settings.options.foreground:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            cmk.ccc.daemon.daemonize()
            logger.info("Daemonized with PID %d.", os.getpid())

        cmk.ccc.daemon.lock_with_pid_file(pid_path)

        def signal_handler(signum: int, stack_frame: FrameType | None) -> None:
            logger.log(VERBOSE, "Got signal %d.", signum)
            raise MKSignalException(signum)

        signal.signal(signal.SIGHUP, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGQUIT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Now let's go...
        run_eventd(
            terminate_main_event,
            settings,
            config,
            lock_configuration,
            history,
            perfcounters,
            event_status,
            event_server,
            status_server,
            slave_status,
            logger,
            reload_config_event,
        )

        # We reach this point, if the server has been killed by
        # a signal or hitting Ctrl-C (in foreground mode)

        # TODO: Move this cleanup stuff to the classes that are responsible for these resources

        # Remove event pipe and drain it, so that we make sure
        # that processes (syslog, etc) will not hang when trying
        # to write into the pipe.
        logger.log(VERBOSE, "Cleaning up event pipe")
        pipe = event_server.open_pipe()  # Open it
        settings.paths.event_pipe.value.unlink()  # Remove pipe
        drain_pipe(pipe)  # Drain any data
        os.close(pipe)  # Close pipe

        logger.log(VERBOSE, "Saving final event state")
        event_status.save_status()

        logger.log(VERBOSE, "Cleaning up sockets")
        settings.paths.unix_socket.value.unlink()
        settings.paths.event_socket.value.unlink()

        logger.log(VERBOSE, "Output hash stats")
        event_server.output_hash_stats()

        logger.log(VERBOSE, "Closing fds which might be still open")
        for fd in [
            settings.options.syslog_udp,
            settings.options.syslog_tcp,
            settings.options.snmptrap_udp,
        ]:
            with contextlib.suppress(Exception):
                if isinstance(fd, FileDescriptor):
                    os.close(fd.value)

        logger.info("Successfully shut down.")
        sys.exit(0)

    except MKSignalException:
        pass

    except Exception:
        if settings.options.debug:
            raise

        CrashReportStore().save(
            ECCrashReport(
                cmk.utils.paths.crash_dir,
                ECCrashReport.make_crash_info(
                    cmk_version.get_general_version_infos(cmk.utils.paths.omd_root)
                ),
            )
        )
        bail_out(logger, traceback.format_exc())

    finally:
        if pid_path and store.have_lock(str(pid_path)):
            with contextlib.suppress(OSError):
                pid_path.unlink()


if __name__ == "__main__":
    main()
