#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# TODO: Refactor/document locking. It is not clear when and how to apply
# locks or when they are held by which component.

# TODO: Refactor events to be handled as objects, e.g. in case when
# creating objects. Or at least update the documentation. It is not clear
# which fields are mandatory for the events.


import abc
import array
import ast
import collections
import contextlib
import errno
import fcntl
import functools
import hashlib
import ipaddress
import itertools
import json
import logging
import os
import pprint
import re
import select
import signal
import socket
import stat
import sys
import termios
import threading
import time
import traceback
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from logging import DEBUG, getLogger, Logger
from pathlib import Path
from types import FrameType
from typing import Any, assert_never, ClassVar, IO, Literal, NamedTuple, override, TypedDict

from setproctitle import setthreadtitle

import cmk.ccc.daemon
import cmk.ccc.profile
import cmk.ccc.store
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.log import CMKFormatter, VERBOSE, verbosity_to_log_level
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version_info import get_general_version_infos
from cmk.crash import ABCCrashReport, CrashReportStore, make_crash_report_base_path
from cmk.livestatus_client import LocalConnection

from .actions import (
    ActionRunner,
    do_event_action,
    do_event_actions,
    do_notify,
    event_has_opened,
)
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
from .core_queries import Connection, HostInfo, query_hosts_scheduled_downtime_depth
from .event import (
    create_events_from_syslog_messages,
    Event,
    LimitKind,
    scrub_string,
    translate_event_host,
)
from .helpers import (
    ECLock,
    EVENT_PIPE,
    EVENT_SOCKET,
    Framing,
    Incomplete,
    next_messages,
    parse_spool_file,
    SYSLOG_VIA_TCP,
    Truncated,
    Unprocessed,
    unprocessed_size,
)
from .history import (
    ActiveHistoryPeriod,
    ErrorLoggingHistory,
    get_logfile,
    History,
    HistoryWhat,
    quote_tab,
    TimedHistory,
)
from .host_config import HostConfig
from .perfcounters import Perfcounters
from .query import (
    Columns,
    MKClientError,
    Query,
    QueryCOMMAND,
    QueryGET,
    QueryREPLICATE,
    request_lines,
    StatusTable,
)
from .rule_matcher import (
    compile_active_rule,
    match,
    match_outcome,
    MatchFailure,
    MatchOutcome,
    MatchResult,
    MatchSuccess,
    RuleMatcher,
)
from .rule_packs import load_active_config
from .settings import create_settings, FileDescriptor, PortNumber, Settings
from .snmp import SNMPTrapParser
from .syslog import SyslogFacility, SyslogPriority
from .timeperiod import TimePeriods


def open_log(log_file_path: Path) -> None:
    try:
        logfile: IO[str] = log_file_path.open("a", encoding="utf-8")
    except Exception as e:
        getLogger("cmk.mkeventd").exception(
            "Cannot open log file '%(log_file_path)s': %(error)s",
            {"log_file_path": log_file_path, "error": e},
        )
        logfile = sys.stderr
    setup_logging_handler(logfile)


def setup_logging_handler(stream: IO[str]) -> None:
    """This method enables all log messages to be written to the given
    stream file object. The messages are formatted in Check_MK standard
    logging format.
    """
    handler = logging.StreamHandler(stream=stream)
    handler.setFormatter(CMKFormatter())
    logger = logging.getLogger("cmk")
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)


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


# Fetches the state of the master of a replication slave, see get_state_from_master()
FetchMasterState = Callable[[Config, SlaveStatus], dict[str, Any]]

FileDescr = int  # mypy calls this FileDescriptor, but this clashes with our definition

# What all events counting towards the same event limit of some kind share: nothing for the
# overall limit, the rule ID for a rule limit and both host names for a host limit
_LimitKey = str | tuple[str, HostName | None] | None

Response = Iterable[Sequence[object]] | Mapping[str, object] | None

# The order in which the event limits are checked
_LIMIT_KINDS: tuple[LimitKind, ...] = ("overall", "by_host", "by_rule")

# The text of an overflow event, which older versions didn't mark otherwise
_OVERFLOW_EVENT_TEXT = re.compile(
    r"The (overall|host|rule) event limit of \d+ open events has been reached"
)


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
        *,
        restart_delay: float = 1.0,
    ) -> None:
        super().__init__(name=name)
        self.settings = settings
        self._config = config
        self._slave_status = slave_status
        self._profiling_enabled = profiling_enabled
        self._profile_file = profile_file
        # How long run() waits before it restarts serve() after an exception. Only tests pass a
        # shorter one, to take less time.
        self._restart_delay = restart_delay
        self._terminate_event = threading.Event()
        self._logger = logger

    @override
    def run(self) -> None:
        self._logger.info("Starting up")
        setthreadtitle(self.name)
        try:
            while self._keep_serving():
                try:
                    with cmk.ccc.profile.Profile(
                        enabled=self._profiling_enabled, profile_file=str(self._profile_file)
                    ):
                        self.serve()
                except Exception:
                    self._logger.exception("Exception in %(name)s server", {"name": self.name})
                    if self.settings.options.debug:
                        raise
                    time.sleep(self._restart_delay)
        finally:
            self._clean_up()
        self._logger.info("Terminated")

    def _clean_up(self) -> None:
        """Cleans up after serving, e.g. closes what serve() keeps open across restarts"""

    def terminate(self) -> None:
        self._terminate_event.set()

    def _keep_serving(self) -> bool:
        """Tells whether to go on serving, i.e. until told to terminate"""
        return not self._terminate_event.is_set()


def create_history_raw(
    settings: Settings,
    config: Config,
    logger: Logger,
    event_columns: Columns,
    history_columns: Columns,
) -> History:
    """Factory for History objects based on the current configuration.

    It imports only the backend configured, as e.g. importing pymongo takes long.
    """
    match config["archive_mode"]:
        case "file":
            from .history_file import FileHistory

            return FileHistory(settings, config, logger, event_columns, history_columns)
        case "mongodb":
            from .history_mongo import MongoDBHistory

            return MongoDBHistory(settings, config, logger, event_columns, history_columns)
        case "sqlite":
            from .history_sqlite import SQLiteHistory, SQLiteSettings

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
    """Factory for History objects based on the current configuration, logging the errors of adding
    entries, and optionally augmented with timing information."""
    history_logger = logger.getChild("EventStatus")
    history = ErrorLoggingHistory(
        create_history_raw(settings, config, history_logger, event_columns, history_columns),
        history_logger,
        debug=settings.options.debug,
    )
    return TimedHistory(history, history_logger) if history_logger.isEnabledFor(DEBUG) else history


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

    # An IPv4 address may also be listed IPv6-mapped, and vice versa.
    other = ip.ipv6_mapped if isinstance(ip, ipaddress.IPv4Address) else ip.ipv4_mapped
    return other is not None and any(other in entry for entry in access_list)


def unmap_ipv4_address(ip_address: str) -> str:
    """
    Accepts addresses with ipv4_mapped hosts and
    returns unmapped ipv4.

    >>> unmap_ipv4_address('::FFFF:192.0.2.128')
    '192.0.2.128'
    """
    with contextlib.suppress(ValueError):  # in case address[0] is a hostname
        host = ipaddress.ip_address(ip_address)
        if isinstance(host, ipaddress.IPv6Address) and host.ipv4_mapped:
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


def receive_datagram(sock: socket.socket) -> tuple[bytes, Any]:
    """Receives a datagram and its sender's address

    The buffer holds the largest UDP payload, as recvfrom() discards the part of a
    datagram which doesn't fit into it, i.e. the end of a long syslog message.
    """
    return sock.recvfrom(65535)


def _mtime_of_regular_file(path: Path) -> float | None:
    """
    The modification time of a regular file, possibly behind a symbolic link, with a single stat(),
    as the event server does this for each entry of the spool directory when it lists it
    """
    try:
        status = path.stat()
    except OSError:  # e.g. a broken symbolic link, or removed in the meantime
        return None
    return status.st_mtime if stat.S_ISREG(status.st_mode) else None


# Errors reading or removing a spool file which are no fault of the file and go away again, e.g.
# when another thread took the last free file descriptor right after we listed the spool directory
_LACK_OF_FILE_DESCRIPTORS = frozenset({errno.EMFILE, errno.ENFILE})

# How often in a row the event server tries to read a spool file it lacks the memory for: Unlike
# file descriptors, memory may never suffice for a big file, e.g. under a limit of the address
# space, and then the file mustn't hold back the newer ones forever.
MAX_TRIES_LACKING_MEMORY = 5

# Far more than its writers spool at once, e.g. about 1 MiB per file when forwarding log messages,
# but little enough to read a spool file at once: With an object for each line, reading one takes
# about 2.5 times its size for syslog messages, and up to 15 times for the shortest lines.
MAX_SPOOL_FILE_SIZE = 16 * 1024 * 1024


def _open_without_blocking(path: str | os.PathLike[str], flags: int) -> int:
    """Like open() opens a file, but a FIFO without waiting for a writer to open it, too"""
    return os.open(path, flags | os.O_NONBLOCK)


def _rename_without_replacing(path: Path, target: Path) -> None:
    """
    Like rename(), but failing with EEXIST instead of replacing the target, as Python offers no
    RENAME_NOREPLACE. Only the event server puts spool files aside, so no target appears meanwhile.
    """
    if target.exists(follow_symlinks=False):
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(target))
    path.rename(target)


def _error_text(error: OSError | MemoryError) -> str:
    """For log messages, as Python raises a MemoryError without any text"""
    return "out of memory" if isinstance(error, MemoryError) else str(error)


def read_spool_file(path: Path) -> Iterator[bytes] | None:
    """
    Its messages, see parse_spool_file(), but None if it is no regular file anymore, e.g. replaced
    by a FIFO or a directory since the spool directory was listed, and EFBIG for a file too big to
    read at once, also if it has grown since
    """
    try:
        with open(path, "rb", opener=_open_without_blocking) as file:
            # What we opened, as the path may lead to something else by now
            status = os.fstat(file.fileno())
            if not stat.S_ISREG(status.st_mode):
                return None
            if status.st_size > MAX_SPOOL_FILE_SIZE:
                raise OSError(errno.EFBIG, f"{os.strerror(errno.EFBIG)}, {status.st_size} bytes")
            # Only opening a FIFO mustn't block: On some file systems, e.g. FUSE ones, reading a
            # regular file without blocking may return only a part of it.
            os.set_blocking(file.fileno(), True)
            # A byte more than its size shows whether it has grown since, and only then we read on,
            # up to a byte more than the limit: Reading that much right away would allocate it.
            data = file.read(status.st_size + 1)
            if len(data) > status.st_size:
                data += file.read(MAX_SPOOL_FILE_SIZE - status.st_size)
                if len(data) > MAX_SPOOL_FILE_SIZE:
                    raise OSError(
                        errno.EFBIG,
                        f"{os.strerror(errno.EFBIG)}, more than {MAX_SPOOL_FILE_SIZE} bytes",
                    )
            return parse_spool_file(data)
    except IsADirectoryError:  # Unlike for a FIFO, Python's open() refuses a directory itself.
        return None


def terminate(
    terminate_main_event: threading.Event,
    event_server: EventServer,
    status_server: StatusServer,
) -> None:
    terminate_main_event.set()
    status_server.terminate()
    event_server.terminate()


def bail_out(logger: Logger, reason: str) -> None:
    logger.error("FATAL ERROR: %(reason)s", {"reason": reason})
    sys.exit(1)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _bytes_in_pipe(pipe: FileDescr) -> int:
    count = array.array("i", [0])
    fcntl.ioctl(pipe, termios.FIONREAD, count)
    return count[0]


# A reference to the matched message in a text which a rule rewrites: \0 for the whole message,
# \1, \2, ... for its match groups, or e.g. $MATCH_GROUPS_MESSAGE_1$ for a match group by name
_GROUP_REFERENCE = re.compile(r"\\(\d+)|\$([A-Z_]+)_(\d+)\$")


def replace_groups(text: str, origtext: str, match_groups: MatchGroups) -> str:
    r"""Replaces the references to the matched message in the text all at once

    So a replacement is never replaced again, e.g. a reference within the message inserted by \0.
    For \10 and up, the longest number referring to a match group wins, so with fewer groups,
    \10 is still the first group followed by a 0. A reference to a missing group stays as it is.
    """
    message_groups = match_groups.get("match_groups_message", False)
    groups = () if message_groups is False else message_groups
    named_groups = {
        name.upper(): values for name, values in match_groups.items() if isinstance(values, tuple)
    }

    def replacement(reference: re.Match[str]) -> str:
        if (digits := reference.group(1)) is not None:
            for end in range(len(digits), 0, -1):
                number, rest = digits[:end], digits[end:]
                if number == "0":
                    return origtext + rest
                if not number.startswith("0") and int(number) <= len(groups):
                    return groups[int(number) - 1] + rest
            return reference.group(0)
        values = named_groups.get(reference.group(2), ())
        index = int(reference.group(3))
        return values[index - 1] if 1 <= index <= len(values) else reference.group(0)

    return _GROUP_REFERENCE.sub(replacement, text)


def _rewritten(text: str, origtext: str, match_groups: MatchGroups) -> str:
    """A text rewritten by a rule, see replace_groups(), with spaces instead of tabs

    Like for the text of a message, see scrub_string(): Livestatus gets a tab as a space, see
    quote_tab(), so a filter it forwards to us would compare with another value than it does.
    A host name can't contain whitespace anyway."""
    return scrub_string(replace_groups(text, origtext, match_groups))


class SignalHandler:
    """Records the signals it handles, so that the main loop acts on them between its tasks

    Raising an exception instead could leave a lock held or keep the EC from saving its status.
    """

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        # Appending and popping are atomic, so no signal gets lost while take() runs.
        self._received: collections.deque[int] = collections.deque()

    def __call__(self, signum: int, stack_frame: FrameType | None) -> None:  # noqa: ARG002
        # Not logged: The handler can interrupt the main thread while that logs.
        self._received.append(signum)

    def take(self) -> int | None:
        """Returns the signal to act on and forgets the others, terminating before reloading"""
        signum: int | None = None
        while self._received:
            received = self._received.popleft()
            self._logger.log(VERBOSE, "Got signal %(signum)d.", {"signum": received})
            if signum is None or signum == signal.SIGHUP:
                signum = received
        return signum

    def terminating(self) -> bool:
        """Tells whether a signal to terminate arrived, without forgetting it like take() does"""
        # Of an atomic copy, as a signal could change the deque meanwhile
        return any(signum != signal.SIGHUP for signum in list(self._received))


@dataclass(frozen=True, kw_only=True)
class ClientConnection:
    """A connection to the event socket or to the syslog socket (TCP)"""

    sock: socket.socket
    endpoint: str  # for log messages, e.g. "event socket"
    address: tuple[str, int] | None  # None for the event socket
    framing: Framing
    unprocessed: Unprocessed = Incomplete()

    @property
    def source(self) -> str:
        """Where its messages come from, for log messages"""
        if self.address is None:
            return self.endpoint
        return f"{self.endpoint}, host {self.address[0]}, port {self.address[1]}"


class _EventPipe(NamedTuple):
    """The event pipe, opened for reading and, by ourselves, for writing"""

    reader: FileDescr
    writer: FileDescr


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
        connection: Connection,
        omd_site: SiteId,
        action_runner: ActionRunner,
        *,
        create_pipes_and_sockets: bool = True,
        idle_timeout: float = 1.0,
        read_spool_file: Callable[[Path], Iterable[bytes] | None] = read_spool_file,
        restart_delay: float = 1.0,
        actions_timeout: float = 30.0,
    ) -> None:
        super().__init__(
            name="EventServer",
            logger=logger,
            settings=settings,
            config=config,
            slave_status=slave_status,
            profiling_enabled=settings.options.profile_event,
            profile_file=settings.paths.event_server_profile.value,
            restart_delay=restart_delay,
        )
        # How long serve() waits for messages before it looks for spool files again, as nothing
        # wakes it up for these. Only tests pass a shorter one, to take less time.
        self._idle_timeout = idle_timeout
        # Waiting for unfinished actions on terminating, see _keep_serving()
        self._actions_timeout = actions_timeout
        self._terminating_since: float | None = None
        self._gave_up_waiting_for_actions = False
        self._pipe: _EventPipe | None = None
        # Kept for the next data from the pipe, also when serve() restarts, like the pipe itself
        self._unprocessed_pipe: Unprocessed = Incomplete()
        # The connections to the event socket and to syslog via TCP, kept with their incomplete
        # messages when serve() restarts, like the pipe
        self._client_sockets: dict[FileDescr, ClientConnection] = {}
        self._syslog_udp: socket.socket | None = None
        self._syslog_tcp: socket.socket | None = None
        self._snmp_trap_socket: socket.socket | None = None
        # Spool files we can neither process nor rename, e.g. immutable ones (chattr +i): Ignored
        # while they are there, also when serve() restarts, they hold back no other ones.
        self._ignored_spool_files: set[Path] = set()
        # Entries of the spool directory other than regular files: Warned about only once while
        # they are there, also when serve() restarts.
        self._skipped_spool_entries: set[Path] = set()
        # The spool files of the last listing of the spool directory which are still to be
        # processed, the oldest one last: Listing it again for each of them would take quadratic
        # time for a backlog of spool files.
        self._spool_files: list[Path] = []
        # The spool file we last lacked the resources to read, which we warn about only once while
        # we try it again and again, and how many of these tries in a row lacked memory
        self._lacking_resources_for: tuple[Path | None, int] = (None, 0)
        # Until when, by time.monotonic(), we take no spool file after lacking the resources for
        # one: The select() timeout alone gives them no time to be freed while messages arrive.
        self._no_spool_files_until = 0.0
        # Only tests pass another one, to make something happen right between listing the spool
        # directory and reading a file from it, which can't be timed.
        self._read_spool_file = read_spool_file

        self._rules: list[Rule] = []
        self._rule_by_id: dict[str | None, Rule] = {}
        self._rule_hash: dict[int, dict[int, Any]] | None = None  # None without rule optimizer
        self._hash_stats: list[list[int]] = []  # facility/priority
        for _unused_facility in range(32):
            self._hash_stats.append([0] * 8)

        self._connection = connection
        self._omd_site = omd_site
        # Shared with the status server and the main thread
        self._action_runner = action_runner
        self.host_config = HostConfig(self._logger, self._connection)
        self._perfcounters = perfcounters
        self._lock_configuration = lock_configuration
        self._history = history
        self._event_status = event_status
        self._event_columns = event_columns
        self._message_period = ActiveHistoryPeriod()
        self._time_period = TimePeriods(self._logger, self._connection)
        self._rule_matcher = RuleMatcher(
            logger=self._logger if config["debug_rules"] else None,
            omd_site_id=self._omd_site,
            is_active_time_period=self._time_period.active,
        )

        # HACK for testing: The real fix would involve breaking up these huge
        # class monsters.
        if not create_pipes_and_sockets:
            return

        # Like the sockets, the pipe stays open when serve() restarts after an exception.
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
        # Right away, so writers like mkevent don't wait for the rest of the startup. Our own writer
        # keeps select() from reporting EOF forever once another one is done, see
        # http://www.outflux.net/blog/archives/2008/03/09/using-select-on-a-fifo/
        reader = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            writer = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            os.close(reader)
            raise
        self._pipe = _EventPipe(reader, writer)

        self._logger.info("Created FIFO '%(path)s' for receiving events", {"path": path})

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
                    "Opened builtin syslog server on inherited filedescriptor %(fd)d",
                    {"fd": endpoint.value},
                )
            if isinstance(endpoint, PortNumber):
                try:
                    self._logger.info("Trying to use ipv6 for syslog-udp")
                    self._syslog_udp = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                    self._syslog_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for syslog-udp...")
                        self._syslog_udp.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except AttributeError, OSError:
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for syslog-udp"
                        )
                    self._syslog_udp.bind(("::", endpoint.value))
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for syslog-udp")
                    self._syslog_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._syslog_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._syslog_udp.bind(("0.0.0.0", endpoint.value))  # nosec B104 # BNS:3d8f2a
                self._logger.info(
                    "Opened builtin syslog server on UDP port %(port)d", {"port": endpoint.value}
                )
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
                    "Opened builtin syslog-tcp server on inherited filedescriptor %(fd)d",
                    {"fd": endpoint.value},
                )
            if isinstance(endpoint, PortNumber):
                try:
                    self._logger.info("Trying to use ipv6 for syslog-tcp")
                    self._syslog_tcp = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    self._syslog_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for syslog-tcp...")
                        self._syslog_tcp.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except AttributeError, OSError:
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for syslog-tcp"
                        )
                    self._syslog_tcp.bind(("::", endpoint.value))
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for syslog-tcp")
                    self._syslog_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._syslog_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._syslog_tcp.bind(("0.0.0.0", endpoint.value))  # nosec B104 # BNS:3d8f2a
                self._syslog_tcp.listen(20)
                self._logger.info(
                    "Opened builtin syslog-tcp server on TCP port %(port)d",
                    {"port": endpoint.value},
                )
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
                    "Opened builtin snmptrap server on inherited filedescriptor %(fd)d",
                    {"fd": endpoint.value},
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
                    except AttributeError, OSError:
                        self._logger.info(
                            "ipv6 dualstack failed. Continuing in ipv6-only mode for snmptrap"
                        )
                    self._snmp_trap_socket.bind(("::", endpoint.value))
                except OSError:
                    self._logger.info("Binding ipv6 failed. Falling back to ipv4 for snmptrap")
                    self._snmp_trap_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._snmp_trap_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._snmp_trap_socket.bind(("0.0.0.0", endpoint.value))  # nosec B104 # BNS:3d8f2a
                self._logger.info(
                    "Opened builtin snmptrap server on UDP port %(port)d", {"port": endpoint.value}
                )
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
        self._logger.info("Opened UNIX socket '%(path)s' for receiving events", {"path": path})

    def close_pipe(
        self,
        *,
        timeout: float = 5.0,
        idle_timeout: float = 0.5,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """
        Removes the pipe, processes what's left in it and closes it. It waits for its writers to
        close it, but at most for the timeout and only while something arrives within the idle
        timeout, as e.g. rsyslog keeps it open. Only tests change the timeouts and the clock.
        """
        if (pipe := self._pipe) is None:
            return
        self._pipe = None
        try:
            try:
                # Remove the pipe, so nobody opens it anymore.
                self.settings.paths.event_pipe.value.unlink(missing_ok=True)
            finally:
                # Without our own writer, reading hits EOF once all others have closed the pipe.
                os.close(pipe.writer)
                # Even if removing the pipe failed, as its writers took what's in it as delivered
                self._process_rest_of_pipe(
                    pipe.reader, clock() + timeout, idle_timeout=idle_timeout, clock=clock
                )
        finally:
            # Writers still blocked on it get EPIPE, so they report their message as lost.
            os.close(pipe.reader)

    def _process_rest_of_pipe(
        self,
        reader: FileDescr,
        deadline: float,
        *,
        idle_timeout: float,
        clock: Callable[[], float],
    ) -> None:
        # Writers like mkevent count a message in the pipe as delivered, so don't drop it.
        idle = closed = False
        while not idle and (timeout := deadline - clock()) > 0:
            if not select.select([reader], [], [], min(timeout, idle_timeout))[0]:
                # Nothing arrived within the idle timeout, unless the deadline cut it short
                idle = idle_timeout < timeout
                continue
            if not (data := os.read(reader, 65536)):
                closed = True  # EOF: All writers have closed the pipe.
                break
            try:
                self._process_pipe_data(data)
            except Exception:
                # Going on with the rest, like serve() does
                self._logger.exception("Exception while processing the event pipe on stopping")
        left = _bytes_in_pipe(reader) + unprocessed_size(self._unprocessed_pipe)
        if left and (idle or closed):
            self._logger.warning(
                "The rest of a message didn't arrive in the event pipe on stopping, dropping the "
                "%(bytes)d bytes left",
                {"bytes": left},
            )
        elif left:
            self._logger.warning(
                "Processing the event pipe on stopping took too long, dropping the %(bytes)d bytes left",
                {"bytes": left},
            )
        elif not closed:
            # Their writes fail once close_pipe() closes it. Only one right before gets lost.
            self._logger.info(
                "Writers still having the event pipe open on stopping get an error from now on"
            )

    def _process_pipe_data(self, data: bytes) -> None:
        messages, self._unprocessed_pipe = next_messages(EVENT_PIPE, self._unprocessed_pipe, data)
        self.process_syslog_messages(self._warning_about_truncated(messages, "event pipe"), None)

    @override
    def _clean_up(self) -> None:
        # Only now, as serve() keeps them open when it restarts
        try:
            self.close_pipe()
        except Exception:
            self._logger.exception("Cannot clean up event pipe")
        for client in self._client_sockets.values():
            client.sock.close()
        self._client_sockets.clear()

    @override
    def _keep_serving(self) -> bool:
        """
        Tells whether to go on serving: Until told to terminate, then while actions are unfinished,
        as they may write into the event pipe, but at most for the timeout of actions
        """
        if super()._keep_serving():
            return True
        if self._gave_up_waiting_for_actions or not self._action_runner.unfinished():
            return False
        now = time.monotonic()
        if self._terminating_since is None:
            self._terminating_since = now
            self._logger.info(
                "Waiting for unfinished actions before removing the event pipe, as they may write "
                "into it"
            )
        if now < self._terminating_since + self._actions_timeout:
            return True
        self._logger.warning(
            "Not waiting any longer for unfinished actions after %(timeout)s s, removing the event "
            "pipe",
            {"timeout": self._actions_timeout},
        )
        self._gave_up_waiting_for_actions = True
        return False

    @override
    def serve(self) -> None:
        # We just read()/recvfrom() these, so we create no new FDs via them.
        pipe_reader = None if self._pipe is None else self._pipe.reader
        pipe_and_datagram_sockets = [
            f for f in (pipe_reader, self._syslog_udp, self._snmp_trap_socket) if f is not None
        ]
        # We use accept() on these FDs, so we must be careful to avoid creating too many additional
        # FDs. We use an arbitrary limit below (less than the usual 1024 FD_SETSIZE limit), so we
        # don't accept() any more connections when there are already many of them. Connections get
        # queued in the OS queue then, and when that is full, a client will get an error, which is
        # the right thing here.
        stream_sockets = [f for f in (self._syslog_tcp, self._eventsocket) if f is not None]
        select_timeout = self._idle_timeout
        while self._keep_serving():
            try:
                readable: list[FileDescr | socket.socket] = select.select(
                    pipe_and_datagram_sockets
                    + (stream_sockets if len(self._client_sockets) < 900 else [])
                    + list(self._client_sockets.keys()),
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
                # We don't need the address of the client, which is "" only if it's unbound.
                client_socket, _ = self._eventsocket.accept()
                self._client_sockets[client_socket.fileno()] = ClientConnection(
                    sock=client_socket,
                    endpoint="event socket",
                    address=None,
                    framing=EVENT_SOCKET,
                )

            # Same for the TCP syslog socket
            if self._syslog_tcp is not None and self._syslog_tcp in readable:
                client_socket, address = self._syslog_tcp.accept()
                endpoint = "syslog socket (TCP)"
                self._client_sockets[client_socket.fileno()] = ClientConnection(
                    sock=client_socket,
                    endpoint=endpoint,
                    address=parse_address(endpoint, address),
                    framing=SYSLOG_VIA_TCP,
                )

            # Read data from existing connections to the event socket and syslog via TCP
            # NOTE: We modify self._client_sockets in the loop, so we need to copy below!
            for fd, client in list(self._client_sockets.items()):
                if fd in readable:
                    try:
                        # Much at once, so a long message, e.g. a log record from the OpenTelemetry
                        # collector on the event socket, takes few reads.
                        new_data = client.sock.recv(65536)
                    except Exception:
                        new_data = b""
                        self._logger.exception(
                            "Exception during recv from %(endpoint)s", {"endpoint": client.endpoint}
                        )

                    if new_data:
                        messages, unprocessed = next_messages(
                            client.framing, client.unprocessed, new_data
                        )
                        # Before processing the messages, so that a restart by an error goes on
                        # right after them
                        self._client_sockets[fd] = replace(client, unprocessed=unprocessed)
                        self.process_syslog_messages(
                            self._warning_about_truncated(messages, client.source), client.address
                        )
                    else:  # the other side is gone, no more data will ever come
                        del self._client_sockets[fd]  # dropping the incomplete rest is OK
                        client.sock.close()  # after the bookkeeping above, close() can throw

            # Read data from the pipe, without octet counting, see EVENT_PIPE for why
            if pipe_reader is not None and pipe_reader in readable:
                try:
                    data = os.read(pipe_reader, 4096)
                except Exception:
                    data = b""
                    self._logger.exception("General exception during pipe os.read")
                self._process_pipe_data(data)

            # Read events from builtin syslog server
            if self._syslog_udp is not None and self._syslog_udp in readable:
                message, address = receive_datagram(self._syslog_udp)
                self.process_syslog_messages(
                    [message], parse_address("syslog socket (UDP)", address)
                )

            # Read events from builtin snmptrap server
            if self._snmp_trap_socket is not None and self._snmp_trap_socket in readable:
                message, address = receive_datagram(self._snmp_trap_socket)
                self.process_potential_event_instrumented(
                    self.create_events_from_trap(message, parse_address("SNMP trap", address))
                )

            if (spool_file := self._next_spool_file()) is not None:
                select_timeout = 0  # enable fast processing to process further files
                try:
                    if (lines := self._read_spool_file(spool_file)) is None:
                        # No regular file anymore, so skip it like _list_spool_files(), and a new
                        # file of that name starts afresh.
                        self._lacking_resources_for = (None, 0)
                        continue
                    # Before processing it, so no error can make us process it again. Having read
                    # it, we process it even if it's gone already.
                    spool_file.unlink(missing_ok=True)
                except FileNotFoundError:
                    # Removed in the meantime, so there is nothing to process, and a new file of
                    # that name starts afresh.
                    self._lacking_resources_for = (None, 0)
                except (OSError, MemoryError) as e:
                    if self._try_again_later(spool_file, e):
                        self._spool_files.append(spool_file)  # Try it again first.
                        select_timeout = self._idle_timeout  # Give the resources time to be freed.
                    else:
                        self._put_aside_spool_file(spool_file, e)
                else:
                    self._lacking_resources_for = (None, 0)
                    self.process_syslog_messages(
                        self._warning_about_truncated(lines, f"spool file {spool_file}"), None
                    )
            else:
                select_timeout = self._idle_timeout  # restore default select timeout

    def _next_spool_file(self) -> Path | None:
        """
        The oldest spool file of the last listing of the spool directory, listing it again only
        once there is none left. A spool file may be gone or changed meanwhile, but reading it
        copes with that, and files spooled meanwhile are newer anyway.

        After lacking the resources for a spool file, it takes none until it is time to try again.
        """
        if time.monotonic() < self._no_spool_files_until:
            return None
        if not self._spool_files:
            self._spool_files = self._list_spool_files()
        return self._spool_files.pop() if self._spool_files else None

    def _list_spool_files(self) -> list[Path]:
        """
        The regular files in the spool directory which aren't ignored, the oldest one last: Reading
        a directory would fail, and reading a FIFO would block, so it skips any other entry.

        It forgets the ignored files and skipped entries which are gone, so a new file with the same
        name is neither ignored nor skipped without a warning.
        """
        paths = list(self.settings.paths.spool_dir.value.glob("[!.]*"))
        self._ignored_spool_files.intersection_update(paths)
        self._skipped_spool_entries.intersection_update(paths)
        candidates: list[tuple[float, Path]] = []
        for path in paths:
            if path in self._ignored_spool_files:
                continue
            if (mtime := _mtime_of_regular_file(path)) is None:
                self._warn_about_skipped_spool_entry(path)
            else:
                candidates.append((mtime, path))
        # By the name for the same modification time, so the order doesn't depend on the listing
        return [path for _mtime, path in sorted(candidates, reverse=True)]

    def _warn_about_skipped_spool_entry(self, path: Path) -> None:
        """Only once while it is there, as we skip it each time we list the spool directory"""
        # Not if it is gone, i.e. if it was a spool file removed right after we listed it
        if path not in self._skipped_spool_entries and path.exists(follow_symlinks=False):
            self._skipped_spool_entries.add(path)
            self._logger.warning(
                "Skipping %(path)s in the spool directory while it leads to no regular file",
                {"path": path},
            )

    def _try_again_later(self, spool_file: Path, error: OSError | MemoryError) -> bool:
        """
        Whether reading the spool file failed for lack of resources, which may be freed again, so
        we try it again after the idle timeout, even if messages wake us up before. But memory may
        never suffice for a big file, so we give up on it after MAX_TRIES_LACKING_MEMORY tries in a
        row lacking it.
        """
        last_file, tries_lacking_memory = self._lacking_resources_for
        if last_file != spool_file:
            tries_lacking_memory = 0
        # Python's own allocations fail with a MemoryError, the kernel's with ENOMEM.
        if isinstance(error, MemoryError) or error.errno == errno.ENOMEM:
            tries_lacking_memory += 1
            try_again = tries_lacking_memory < MAX_TRIES_LACKING_MEMORY
        else:
            try_again = error.errno in _LACK_OF_FILE_DESCRIPTORS
        if not try_again:
            self._lacking_resources_for = (None, 0)  # So a new file of that name starts afresh.
            return False
        if last_file != spool_file:  # Only once for each file, as we try it again and again
            self._logger.warning(
                "Cannot process spool file %(path)s now, trying again later: %(error)s",
                {"path": spool_file, "error": _error_text(error)},
            )
        self._lacking_resources_for = (spool_file, tries_lacking_memory)
        self._no_spool_files_until = time.monotonic() + self._idle_timeout
        return True

    def _put_aside_spool_file(self, spool_file: Path, error: OSError | MemoryError) -> None:
        """
        Keeps it for the admin, but hidden or ignored, so it holds back no spool file after it, and
        a file put aside earlier under the same name is kept, too
        """
        hidden = spool_file.with_name(f".{spool_file.name}.unreadable")
        try:
            _rename_without_replacing(spool_file, hidden)
        except OSError as rename_error:
            self._ignored_spool_files.add(spool_file)
            self._logger.error(  # noqa: TRY400 # not our fault, so no stack trace
                "Cannot process spool file %(path)s, ignoring it: %(error)s (%(rename_error)s)",
                {"path": spool_file, "error": _error_text(error), "rename_error": rename_error},
            )
        else:
            self._logger.error(
                "Cannot process spool file %(path)s, renamed it to %(hidden)s: %(error)s",
                {"path": spool_file, "hidden": hidden.name, "error": _error_text(error)},
            )

    def create_events_from_trap(self, data: bytes, address: tuple[str, int]) -> Iterator[Event]:
        try:
            if varbinds_and_ipaddress := self._snmp_trap_parser(data, address):
                yield create_event_from_trap(varbinds_and_ipaddress[0], varbinds_and_ipaddress[1])
        except Exception as e:
            # NOTE: SNMPTrapParser._handle_unauthenticated_snmptrap() logs more details about what
            # went wrong on "verbose" logging level, anyway. We do not log on "info" here to avoid
            # possible log spam from a misconfigured/buggy device.
            self._logger.debug("skipping unparsable SNMP trap, reason: %(reason)s", {"reason": e})

    def process_potential_event_instrumented(self, events: Iterable[Event]) -> None:
        """
        Processes incoming data, just a wrapper between the real data and the
        handler function to record some statistics etc.
        """
        for event in events:
            self._perfcounters.count("messages")
            before = time.time()
            # In replication slave mode (when not took over), ignore all events
            if not is_syncing_replication_slave(self._config, self._slave_status):
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

    def _warning_about_truncated(self, messages: Iterable[bytes], source: str) -> Iterator[bytes]:
        """
        Passes the messages on, warning about each one which its framing truncated: Each of these
        took more than MAX_MESSAGE_SIZE bytes, so there is at most one warning per 64 KiB received.
        """
        for message in messages:
            if isinstance(message, Truncated):
                self._logger.warning(
                    "Truncated a message to %(size)d bytes from %(source)s: %(start)r",
                    {
                        "size": len(message),
                        "source": source,
                        "start": message[:60].decode("utf-8", "replace"),
                    },
                )
            yield message

    def do_housekeeping(self) -> None:
        # In replication slave mode (when not took over), the master handles the events. Every sync
        # replaces them, so handling them here would only duplicate the master's actions.
        if not is_syncing_replication_slave(self._config, self._slave_status):
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
        for event in self._event_status.events()[:]:  # a copy, as removing events changes the list
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
                VERBOSE,
                "Remove event %(event_id)d (created in downtime, host left downtime)",
                {"event_id": event["id"]},
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
        now = time.time()
        # Remove each event right when closing it, so an exception while opening a later event
        # leaves no closed event behind. Hence iterate over a copy of the events.
        for event in self._event_status.events()[:]:
            rule = self._rule_by_id.get(self._event_status.creating_rule_id(event))

            if event["phase"] == "counting":
                # Event belongs to a rule that does not longer exist? It
                # will never reach its count. Better delete it.
                if not rule:
                    self._logger.info(
                        "Deleting orphaned event %(event_id)d created by obsolete rule %(rule_id)s",
                        {"event_id": event["id"], "rule_id": event["rule_id"]},
                    )
                    event["phase"] = "closed"
                    self._event_status.remove_event(event, "ORPHANED")

                elif "count" not in rule and not rule.get("expect"):
                    self._logger.info(
                        "Count-based event %(event_id)d belonging to rule %(rule_id)s: rule does not "
                        "count/expect anymore. Deleting event.",
                        {"event_id": event["id"], "rule_id": event["rule_id"]},
                    )
                    event["phase"] = "closed"
                    self._event_status.remove_event(event, "NOCOUNT")

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
                                    "Rule %(pack)s/%(rule_id)s, event %(event_id)d: got %(new_tokens)d new tokens",
                                    {
                                        "pack": rule["pack"],
                                        "rule_id": rule["id"],
                                        "event_id": event["id"],
                                        "new_tokens": new_tokens,
                                    },
                                )
                            event["count"] = max(0, event["count"] - new_tokens)
                            event["last_token"] = (
                                last_token + new_tokens * secs_per_token
                            )  # not now! would be unfair
                            if event["count"] == 0:
                                self._logger.info(
                                    "Rule %(pack)s/%(rule_id)s, event %(event_id)d: again without allowed rate, dropping event",
                                    {
                                        "pack": rule["pack"],
                                        "rule_id": rule["id"],
                                        "event_id": event["id"],
                                    },
                                )
                                event["phase"] = "closed"
                                self._event_status.remove_event(event, "COUNTFAILED")

                    elif event["first"] + count["period"] <= now:  # End of period reached
                        self._logger.info(
                            "Rule %(pack)s/%(rule_id)s: reached only %(count)d out of %(required)d events within %(period)d seconds. "
                            "Resetting to zero.",
                            {
                                "pack": rule["pack"],
                                "rule_id": rule["id"],
                                "count": event["count"],
                                "required": count["count"],
                                "period": count["period"],
                            },
                        )
                        event["phase"] = "closed"
                        self._event_status.remove_event(event, "COUNTFAILED")

            # Handle delayed actions
            elif event["phase"] == "delayed":
                delay_until = event.get("delay_until", 0)  # should always be present
                if now >= delay_until:
                    self._logger.info(
                        "Delayed event %(event_id)d of rule %(rule_id)s is now activated.",
                        {"event_id": event["id"], "rule_id": event["rule_id"]},
                    )
                    event["phase"] = "open"
                    self._history.add(event, "DELAYOVER")
                    if rule:
                        self._open_event(rule, event, holding_lock=True)
                    else:
                        self._logger.info(
                            "Cannot do rule action: rule %(rule_id)s not present anymore.",
                            {"rule_id": event["rule_id"]},
                        )

            # Handle events with a limited lifetime
            elif "live_until" in event and now >= event["live_until"]:
                allowed_phases = event.get("live_until_phases", ["open"])
                if event["phase"] in allowed_phases:
                    event["phase"] = "closed"
                    self._event_status.remove_event(event, "EXPIRED")
                    self._logger.info(
                        "Lifetime of event %(event_id)d (rule %(rule_id)s) exceeded. Deleting event.",
                        {"event_id": event["id"], "rule_id": event["rule_id"]},
                    )

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

                next_interval_start = self._event_status.clamp_timestamp_to_interval(
                    interval, interval_start, interval_count=1
                )
                if next_interval_start > now:
                    continue

                # Interval has been elapsed. Now comes the truth: do we have enough
                # rule matches?

                try:
                    # First look for case 1: rule that already have at least one hit
                    # and this events in the state "counting" exist.
                    for event in self._event_status.events():
                        if (
                            self._event_status.creating_rule_id(event) == rule["id"]
                            and event["phase"] == "counting"
                        ):
                            # time has elapsed. Now lets see if we have reached
                            # the necessary count:
                            # Either way, the counting event is no longer needed. Removing it right
                            # away is fine, as the loop ends here anyway.
                            if event["count"] < expect["count"]:  # no -> trigger alarm
                                # Remove it before opening the event about the missing messages, so
                                # the limits neither count it nor delete it to make room for that
                                # event.
                                self._event_status.remove_event(event, "AUTODELETE")
                                self._handle_absent_event(
                                    rule, expect, event["count"], interval_start
                                )
                            else:  # yes -> everything is fine.
                                self._event_status.remove_event(event, "COUNTREACHED")
                                self._event_status.clear_interval_start(rule["id"])
                                self._logger.info(
                                    "Rule %(pack)s/%(rule_id)s has reached %(count)d occurrences (%(required)d required). "
                                    "Starting next period.",
                                    {
                                        "pack": rule["pack"],
                                        "rule_id": rule["id"],
                                        "count": event["count"],
                                        "required": expect["count"],
                                    },
                                )
                            break

                    # Ou ou, no event found at all.
                    else:
                        self._handle_absent_event(rule, expect, 0, interval_start)

                finally:
                    # Do not forget to switch to next interval, even if an exception interrupts
                    # opening the event about the missing messages: Checking the same interval again
                    # would open another such event.
                    self._event_status.start_next_interval(rule["id"], interval)

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
                if self._event_status.creating_rule_id(event) == rule["id"] and (
                    event["phase"] == "open" or (event["phase"] == "ack" and merge == "acked")
                ):
                    merge_event = event
                    break

        if merge_event:
            merge_event["last"] = now
            # Like counting up an event, cope with events which have never been counted, e.g. from
            # before the rule expected messages.
            merge_event["count"] = merge_event.get("count", 1) + 1

            # This was resetting the state back to "open", even in case an
            # "ack" event is being merged. This was made configurable in
            # 1.6.0p20 because of SUP-4803.
            if reset_ack:
                merge_event["phase"] = "open"

            merge_event["time"] = now
            merge_event["text"] = text
            # Better rewrite (again). Rule might have changed. Also we have changed
            # the text and the user might have his own text added via set_text.
            # Like for a new event, rewrite from an empty host name and application, so a
            # reference to them doesn't insert what the previous rewriting produced.
            if "set_host" in rule:
                merge_event["host"] = HostName("")
            if "set_application" in rule:
                merge_event["application"] = ""
            self.rewrite_event(rule, merge_event, MatchGroups(), set_first=False)
            self._event_status.follow_hosts_of(merge_event)
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
            # Like the event counting the expected messages, no limit drops it, but the limits still
            # act on it. It has no host in the core.
            self._new_event_respecting_limits(event, None, droppable=False)
            self._history.add(event, "COUNTFAILED")
            self._open_event(rule, event, holding_lock=True)

    def reload_configuration(self, config: Config, history: History) -> None:
        # Prepare everything which can fail before changing anything, so a failed reload keeps the
        # previous configuration.
        snmp_trap_parser = SNMPTrapParser(
            self.settings, config, self._logger.getChild("snmp")
        ).parse
        compiled_rules = self._compile_rules(
            config["rule_packs"], rule_optimizer=config["rule_optimizer"]
        )
        rule_digests = _rule_digests(config["rule_packs"])
        # Messages count the hits of the rules they match, so forget the hits of the changed rules
        # together with replacing them. Like the status server, take the lock of the event status
        # before the one of the configuration.
        with self._event_status.lock, self._lock_configuration:
            self._event_status.use_rules(rule_digests)
            self._config = config
            self._history = history
            self._snmp_trap_parser = snmp_trap_parser
            self._rules, self._rule_by_id, self._rule_hash = compiled_rules
            self.host_config = HostConfig(self._logger, self._connection)
            self._rule_matcher = RuleMatcher(
                logger=self._logger if config["debug_rules"] else None,
                omd_site_id=self._omd_site,
                is_active_time_period=self._time_period.active,
            )
        # Without the locks, as it waits until an action is recorded in the previous history
        self._action_runner.use_history(history)

    def compile_rules(self, rule_packs: Sequence[ECRulePack]) -> None:
        """Precompile regular expressions and similar stuff."""
        self._rules, self._rule_by_id, self._rule_hash = self._compile_rules(
            rule_packs, rule_optimizer=self._config["rule_optimizer"]
        )

    def _compile_rules(
        self, rule_packs: Sequence[ECRulePack], *, rule_optimizer: bool
    ) -> tuple[list[Rule], dict[str | None, Rule], dict[int, dict[int, Any]] | None]:
        """Compiles the rules into new structures, so messages never see partially compiled rules

        Without the rule optimizer, there is no rule hash, so messages tell from the compiled rules
        alone whether to use it, even while a reload changes the rule optimizer setting.
        """
        rules: list[Rule] = []
        rule_by_id: dict[str | None, Rule] = {}
        # Speedup-Hash for rule execution
        rule_hash: dict[int, dict[int, Any]] = {}
        count_disabled = 0
        count_rules = 0
        count_unspecific = 0

        # Loop through all rule packs and with through their rules
        for rule_pack in rule_packs:
            for rule in rule_pack["rules"]:
                try:
                    active_rule = compile_active_rule(rule_pack, rule)
                except Exception:
                    if self.settings.options.debug:
                        raise
                    count_disabled += 1
                    self._logger.exception(
                        "Ignoring rule '%(pack)s/%(rule_id)s' because it is invalid.",
                        {"pack": rule_pack["id"], "rule_id": rule["id"]},
                    )
                    continue
                if isinstance(active_rule, str):
                    count_disabled += 1
                    continue

                count_rules += 1
                rules.append(active_rule)
                rule_by_id[active_rule["id"]] = active_rule
                if rule_optimizer:
                    self.hash_rule(rule_hash, active_rule)
                    if (
                        "match_facility" not in active_rule
                        and "match_priority" not in active_rule
                        and "cancel_priority" not in active_rule
                        and "cancel_application" not in active_rule
                    ):
                        count_unspecific += 1

        self._logger.info(
            "Compiled %(count_rules)d active rules (ignoring %(count_disabled)d disabled rules)",
            {"count_rules": count_rules, "count_disabled": count_disabled},
        )
        if rule_optimizer:
            self._logger.info(
                "Rule hash: %(total)d rules - %(hashed)d hashed, %(unspecific)d unspecific",
                {
                    "total": len(rules),
                    "hashed": len(rules) - count_unspecific,
                    "unspecific": count_unspecific,
                },
            )
            for facility in list(range(23)) + [31]:
                if facility in rule_hash:
                    stats = [
                        f"{SyslogPriority(prio)}({len(entries)})"
                        for prio, entries in rule_hash[facility].items()
                    ]
                    self._logger.info(
                        " %(facility)-12s: %(stats)s",
                        {"facility": SyslogFacility(facility), "stats": " ".join(stats)},
                    )
        return rules, rule_by_id, rule_hash if rule_optimizer else None

    @classmethod
    def hash_rule(cls, rule_hash: dict[int, dict[int, Any]], rule: Rule) -> None:
        """Construct rule hash for faster execution."""
        facility = rule.get("match_facility")
        if facility and not rule.get("invert_matching"):
            cls.hash_rule_facility(rule_hash, rule, facility)
        else:
            for facility in range(32):  # all syslog facilities
                cls.hash_rule_facility(rule_hash, rule, facility)

    @staticmethod
    def hash_rule_facility(rule_hash: dict[int, dict[int, Any]], rule: Rule, facility: int) -> None:
        needed_prios = [False] * 8

        if "match_priority" in rule:
            prio_from, prio_to = rule["match_priority"]  # sorted by compile_rule()
            for p in range(prio_from, prio_to + 1):
                needed_prios[p] = True
        else:  # all priorities match
            needed_prios = [True] * 8  # needed to check this rule for all event priorities

        if "cancel_priority" in rule:
            prio_from, prio_to = rule["cancel_priority"]  # sorted by compile_rule()
            for p in range(prio_from, prio_to + 1):
                needed_prios[p] = True
        elif "match_ok" in rule:  # a cancelling rule where all priorities cancel
            needed_prios = [True] * 8  # needed to check this rule for all event priorities

        if rule.get("invert_matching"):
            needed_prios = [True] * 8

        prio_hash = rule_hash.setdefault(facility, {})
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
                "  %(facility)s/%(priority)s - %(count)d (%(percentage).2f%%)",
                {
                    "facility": SyslogFacility(facility),
                    "priority": SyslogPriority(priority),
                    "count": count,
                    "percentage": (100.0 * count / float(total_count)),
                },
            )

    def process_potential_event(self, event: Event) -> None:
        self.do_translate_hostname(event)

        # Log all incoming messages into a syslog-like text file if that is enabled
        if self._config["log_messages"]:
            self.log_message(event)

        # Rule optimizer: Rely on the compiled rules instead of the setting, which a reload changes
        # before replacing the rules. A reload may replace them while the message runs through them,
        # so the hits count by the digests of the rules it runs through.
        with self._lock_configuration:
            rules, rule_hash = self._rules, self._rule_hash
            rule_digests = self._event_status.rule_digests
        if rule_hash is not None:
            self._hash_stats[event["facility"]][event["priority"]] += 1
            rule_candidates = rule_hash.get(event["facility"], {}).get(event["priority"], [])
        else:
            rule_candidates = rules

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
                    self._logger.info(
                        "  matching groups:\n%(match_groups)s",
                        {"match_groups": pprint.pformat(result.match_groups)},
                    )

                self._event_status.count_rule_match(rule["id"], rule_digests=rule_digests)
                if self._config["log_rulehits"]:
                    self._logger.info(
                        "Rule '%(pack)s/%(rule_id)s' hit by message %(facility)s/%(priority)s - '%(text)s'.",
                        {
                            "pack": rule["pack"],
                            "rule_id": rule["id"],
                            "facility": SyslogFacility(event["facility"]),
                            "priority": SyslogPriority(event["priority"]),
                            "text": event["text"],
                        },
                    )

                outcome = match_outcome(rule, result)
                if outcome is MatchOutcome.SKIP_PACK:
                    skip_pack = rule["pack"]
                    if self._config["debug_rules"]:
                        self._logger.info(
                            "  skipping this rule pack (%(skip_pack)s)",
                            {"skip_pack": skip_pack},
                        )
                    continue
                if outcome is MatchOutcome.DROP_MESSAGE:
                    self._perfcounters.count("drops")
                    return
                if outcome is MatchOutcome.CANCEL_EVENTS:
                    self._event_status.cancel_events(
                        self,
                        self._event_columns,
                        event,
                        result.match_groups,
                        rule,
                        action_runner=self._action_runner,
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
                                    "Event opening will be delayed for %(delay)d seconds",
                                    {"delay": rule["delay"]},
                                )
                            existing_event["delay_until"] = time.time() + rule["delay"]
                            existing_event["phase"] = "delayed"
                            self._history.add(existing_event, "COUNTREACHED")
                        else:
                            self._history.add(existing_event, "COUNTREACHED")
                            self._open_event(rule, existing_event, holding_lock=False)
                elif rule.get("expect"):
                    self._event_status.count_expected_event(self, event)
                else:
                    if "delay" in rule:
                        if self._config["debug_rules"]:
                            self._logger.info(
                                "Event opening will be delayed for %(delay)d seconds",
                                {"delay": rule["delay"]},
                            )
                        event["delay_until"] = time.time() + rule["delay"]
                        event["phase"] = "delayed"
                    else:
                        event["phase"] = "open"

                    if self.new_event_respecting_limits(event) and event["phase"] == "open":
                        self._open_event(rule, event, holding_lock=False)
                return

        # End of loop over rules.
        if self._config["archive_orphans"]:
            self._event_status.archive_event(event)

    def _open_event(self, rule: Rule, event: Event, *, holding_lock: bool) -> None:
        """Triggers the actions of the rule for the event it has just opened

        An automatically deleted event gets deleted right afterwards, even on an exception.
        """
        try:
            event_has_opened(
                self.settings,
                self._config,
                self._logger,
                self._connection,
                self.host_config,
                self._event_columns,
                rule,
                event,
                action_runner=self._action_runner,
            )
        finally:
            if rule.get("autodelete"):
                event["phase"] = "closed"
                with contextlib.nullcontext() if holding_lock else self._event_status.lock:
                    self._event_status.remove_event(event, "AUTODELETE")

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
            return query_hosts_scheduled_downtime_depth(self._connection, host_name) >= 1
        except Exception:
            self._logger.exception(
                "Cannot get downtime info for host '%(host_name)s', assuming no downtime.",
                {"host_name": host_name},
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
            pats = rule["state"][1]
            text = event["text"]
            if (p := pats.get("2")) is not None and match(p, text, complete=False) is not False:
                event["state"] = 2
            elif (p := pats.get("1")) is not None and match(p, text, complete=False) is not False:
                event["state"] = 1
            elif (p := pats.get("0")) is not None and match(p, text, complete=False) is not False:
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
            event["comment"] = _rewritten(rule["set_comment"], event["text"], match_groups)
        if "set_text" in rule:
            event["text"] = _rewritten(rule["set_text"], event["text"], match_groups)
        if "set_host" in rule:
            event["orig_host"] = event["host"]
            event["host"] = HostName(replace_groups(rule["set_host"], event["host"], match_groups))
        if "set_application" in rule:
            event["application"] = _rewritten(
                rule["set_application"], event["application"], match_groups
            )
        if "set_contact" in rule and "contact" not in event:
            event["contact"] = _rewritten(
                rule["set_contact"], event.get("contact", ""), match_groups
            )

    def do_translate_hostname(self, event: Event) -> None:
        event["host"] = translate_event_host(
            self._config["hostname_translation"],
            event["host"],
            self._logger if self._config["debug_rules"] else None,
        )

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

    def new_event_respecting_limits(self, event: Event, *, droppable: bool = True) -> bool:
        """Adds the event, unless a limit drops it, returning whether it was added

        A limit never drops an event which isn't droppable, but the event still counts towards the
        limits, they make room for it, and they act on it reaching them.
        """
        core_host = event["core_host"]
        host_config = self.host_config.get_config_for_host(core_host) if core_host else None
        with self._event_status.lock:
            return self._new_event_respecting_limits(event, host_config, droppable=droppable)

    # protected by self._event_status.lock
    def _new_event_respecting_limits(
        self, event: Event, host_config: HostInfo | None, *, droppable: bool
    ) -> bool:
        self._logger.log(
            VERBOSE,
            "Checking limit for message from %(host)s (rule '%(rule_id)s')",
            {"host": event["host"], "rule_id": event["rule_id"]},
        )
        limits: list[tuple[LimitKind, int, str]] = []
        for ty in _LIMIT_KINDS:
            limit, action = self._get_event_limit(ty, event, host_config)
            if droppable and self._drops_event(ty, event, limit, action):
                return False
            limits.append((ty, limit, action))
        # Only now that no limit drops the event, make room for it and act on the limits which
        # it reaches. Otherwise, a limit would delete events for an event which is dropped
        # anyway, and while a further limit drops the events, each of them would reach the
        # limit again. Make room for all limits first, as deleting events for one limit can
        # keep the event from reaching another one.
        for ty, limit, action in limits:
            if action == "delete_oldest":
                self._delete_oldest_events(ty, event, limit)
        reached_limits = [
            (ty, limit, action)
            for ty, limit, action in limits
            if self._reaches_limit(ty, event, limit, action)
        ]
        num_open_before = {
            ty: self._event_status.get_num_existing_events_by(ty, event) for ty in _LIMIT_KINDS
        }
        for ty, limit, action in reached_limits:
            self._act_on_reached_limit(ty, event, limit, action)
        # Overflow events created meanwhile count towards the limits, too, so the limits
        # deleting the oldest events make room once more, but only by deleting the events open
        # before: Deleting an overflow event right away would hide that its limit is reached.
        for ty, limit, action in limits:
            if action == "delete_oldest":
                self._delete_oldest_events(ty, event, limit, at_most=num_open_before[ty])
        self._event_status.new_event(event)
        return True

    # The following actions can be configured:
    # stop                 Stop creating new events
    # stop_overflow        Stop creating new events, create overflow event
    # stop_overflow_notify Stop creating new events, create overflow event, notify
    # delete_oldest        Delete oldest event, create new event
    # protected by self._event_status.lock

    def _drops_event(self, ty: LimitKind, event: Event, limit: int, action: str) -> bool:
        """Tells whether the limit of the given kind drops the new event, as it's reached already

        Only the events open before any of them is deleted count, so deleting the oldest events for
        another limit never makes room for the new event.
        """
        num_already_open = self._event_status.get_num_existing_events_by(ty, event)
        self._logger.log(
            VERBOSE,
            "  Type: %(type)s, already open events: %(num_open)d, Limit: %(limit)d",
            {"type": ty, "num_open": num_already_open, "limit": limit},
        )

        # Even with this event, the limit isn't exceeded, or deleting the oldest events keeps it
        if num_already_open + 1 <= limit or action == "delete_oldest":
            return False

        # Limit reached already in the past: Simply drop silently
        # Just log in verbose mode! Otherwise log file will be flooded
        self._logger.log(VERBOSE, "  Skip processing because limit is already in effect")
        self._perfcounters.count("overflows")
        return True

    # protected by self._event_status.lock
    def _delete_oldest_events(
        self, ty: LimitKind, event: Event, limit: int, *, at_most: int | None = None
    ) -> None:
        """Deletes the oldest events counting towards the limit of the given kind, making room for
        the new event, which no limit drops, but at most the given number of events"""
        num_open = self._event_status.get_num_existing_events_by(ty, event) + 1  # after adding it
        num_deleted = 0
        while num_open > limit and (at_most is None or num_deleted < at_most):
            self._perfcounters.count("overflows")
            self._event_status.remove_oldest_event(ty, event)
            num_open -= 1
            num_deleted += 1

    # protected by self._event_status.lock
    def _reaches_limit(self, ty: LimitKind, event: Event, limit: int, action: str) -> bool:
        """Tells whether the new event, for which the limits made room, reaches the limit of the
        given kind

        A limit deleting the oldest events is never reached, it keeps the limit instead.
        """
        # This is the event which reached the limit, allow creation of it. Further
        # events will be stopped.
        return (
            action != "delete_oldest"
            and self._event_status.get_num_existing_events_by(ty, event) + 1 == limit
        )

    # protected by self._event_status.lock
    def _act_on_reached_limit(self, ty: LimitKind, event: Event, limit: int, action: str) -> None:
        """Performs the one time actions for the event which reaches the limit of the given kind"""
        # Not again as long as their overflow event is still open, though.
        if self._event_status.has_overflow_event(ty, event):
            self._logger.info(
                "  The %(type)s limit has been reached, overflow event still open", {"type": ty}
            )
            return
        self._logger.info("  The %(type)s limit has been reached", {"type": ty})
        overflow_event = self._create_overflow_event(ty, event, limit)

        if "overflow" in action:
            self._logger.info("  Creating overflow event")
            self._event_status.new_event(overflow_event)

        if "notify" in action:
            self._logger.info("  Creating overflow notification")
            do_notify(
                self.host_config,
                self._logger,
                self._connection,
                overflow_event,
                action_runner=self._action_runner,
                # It matters most in a flood of events, and there's at most one per limit.
                droppable=False,
            )

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

    def get_rule_by_id(self, rule_id: str) -> Rule | None:
        return self._rule_by_id.get(rule_id)

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
            overflowed_limit=ty,
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
                        # Like the event reaching the limit, so it counts towards the same one.
                        "host": event["host"],
                        "core_host": event["core_host"],
                        "host_in_downtime": event["host_in_downtime"],
                        "ipaddress": event["ipaddress"],
                        "text": (
                            f'The host event limit of {limit} open events has been reached for host "{event["host"]}". '
                            "Not opening any additional event for this host until open events have "
                            "been archived."
                        ),
                    }
                )

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


def partition[T](pred: Callable[[T], bool], iterable: Iterable[T]) -> tuple[list[T], list[T]]:
    yay = list[T]()
    nay = list[T]()
    for x in iterable:
        (yay if pred(x) else nay).append(x)
    return yay, nay


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
    """Reading the status queries of a client"""

    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock
        self._buffer = b""

    def __iter__(self) -> Iterator[bytes]:
        while True:
            parts = self._buffer.split(b"\n\n", 1)
            if len(parts) > 1:
                request, self._buffer = parts
                yield request
            else:
                data = self._socket.recv(4096)
                if data:
                    self._buffer += data
                elif self._buffer:
                    request, self._buffer = [self._buffer, b""]
                    yield request
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
    filters_itself = True
    columns: ClassVar[Columns] = [
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

    def __init__(
        self, logger: Logger, get_events: Callable[[], Iterable[Mapping[str, object]]]
    ) -> None:
        super().__init__(logger)
        self._get_events = get_events
        # NOTE: We depend on the dict insertion order below, but this is guaranteed for Python >= 3.7.
        self._columns_dict = dict(self.columns)

    @override
    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        # Filtering an event takes much less time than building its row, e.g. for the
        # filters of check_mkevents, which select only a few of many events. The row has
        # the values of the event, so the filters select the same.
        filters = [
            (f.predicate, f.column_name[6:], self._columns_dict[f.column_name])
            for f in query.filters
        ]
        for event in self._get_events():
            for predicate, key, default in filters:  # faster than all() with a generator
                if not predicate(event.get(key, default)):
                    break
            else:
                yield [
                    event.get(column_name[6:], default)
                    for column_name, default in self._columns_dict.items()
                ]


class StatusTableHistory(StatusTable):
    name = "history"
    prefix = "history"
    filters_itself = True  # The history filters the entries while reading them.
    columns: ClassVar[Columns] = list(
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

    @override
    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return self._history.get(query)


class StatusTableRules(StatusTable):
    name = "rules"
    prefix = "rule"
    columns: ClassVar[Columns] = [
        ("rule_id", ""),
        ("rule_hits", 0),
    ]

    def __init__(self, logger: Logger, event_status: EventStatus) -> None:
        super().__init__(logger)
        self._event_status = event_status

    @override
    def _enumerate(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return self._event_status.get_rule_stats()


class StatusTableStatus(StatusTable):
    name = "status"
    prefix = "status"
    columns: ClassVar[Columns] = EventServer.status_columns()

    def __init__(self, logger: Logger, event_server: EventServer) -> None:
        super().__init__(logger)
        self._event_server = event_server

    @override
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


# How long CREATE waits for room in a full event pipe, holding up other queries
_CREATE_TIMEOUT = 5.0  # seconds


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
        connection: Connection,
        action_runner: ActionRunner,
        *,
        clock: Callable[[], float] = time.monotonic,
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

        self._table_events = StatusTableEvents(logger, event_status.get_events)
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
        self._connection = connection
        self._action_runner = action_runner
        # Only tests pass another clock for the deadline of CREATE.
        self._clock = clock

        self.open_unix_socket()
        self.open_tcp_socket()

    @override
    def _clean_up(self) -> None:
        # Right away, so that clients get an error instead of waiting while the EC terminates
        self.close_unix_socket()
        self.close_tcp_socket()

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
                    self._logger.warning("%(error)s, disabling all TCP access", {"error": e})
                    self._tcp_access_list = []
                try:
                    self._logger.info("Trying to use ipv6 for TCP socket port")
                    self._tcp_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self._logger.info("Trying to enable ipv6 dualstack for tcp socket...")
                        self._tcp_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except AttributeError, OSError:
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
                    self._tcp_socket.bind(("0.0.0.0", self._tcp_port))  # nosec B104 # BNS:3d8f2a
                self._tcp_socket.listen(self._config["socket_queue_len"])
                self._logger.info(
                    "Going to listen for status queries on TCP port %(port)d",
                    {"port": self._tcp_port},
                )
            except Exception:
                if self.settings.options.debug:
                    raise
                self._logger.exception(
                    "Cannot listen on TCP socket port %(port)d", {"port": self._tcp_port}
                )
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

    @override
    def serve(self) -> None:
        while not self._terminate_event.is_set():
            client_socket = None
            addr_info = None
            try:
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
                                "Handle status connection from %(host)s:%(port)d",
                                {"host": addr_info[0], "port": addr_info[1]},
                            )
                        if self._tcp_access_list is not None and not allowed_ip(
                            ipaddress.ip_address(addr_info[0]), self._tcp_access_list
                        ):
                            client_socket.close()
                            client_socket = None
                            self._logger.info(
                                "Denying access to status socket from %(host)s (allowed is only %(allowed)s)",
                                {
                                    "host": addr_info[0],
                                    "allowed": ", ".join(str(x) for x in self._tcp_access_list),
                                },
                            )
                            continue
                    else:
                        allow_commands = True

                    self.handle_client(
                        client_socket, allow_commands, addr_info and addr_info[0] or ""
                    )

                    duration = time.time() - before
                    self._logger.log(
                        VERBOSE,
                        "Answered request in %(duration_ms)0.2f ms",
                        {"duration_ms": duration * 1000},
                    )
                    self._perfcounters.count_time("request", duration)

            except Exception as e:
                # Do not log a stack trace for client errors, they are not *our* fault.
                if isinstance(e, MKClientError):
                    self._logger.error(  # noqa: TRY400
                        "Error handling client %(client)s: %(error)s",
                        {"client": addr_info, "error": e},
                    )
                else:
                    self._logger.exception(
                        "Error handling client %(client)s", {"client": addr_info}
                    )
                if client_socket:
                    client_socket.close()
                    client_socket = None
                time.sleep(0.2)
            client_socket = None  # close without danger of exception

    def handle_client(
        self, client_socket: socket.socket, allow_commands: bool, client_ip: str
    ) -> None:
        for request in Queries(client_socket):
            created_event: bytes | None = None
            with self._event_status.lock:
                # Reloading the configuration closes the previous history while holding the lock,
                # so parse the query only now, when its table can't be that history anymore.
                query = Query.make(self.table, request_lines(request), self._logger)
                self._logger.log(VERBOSE, "Client livestatus query: %(query)r", {"query": query})

                # TODO: What we really want is a method in Query returning a response instead of this dispatching horror.
                if isinstance(query, QueryGET):
                    response: Response = query.table.query(query)
                elif isinstance(query, QueryREPLICATE):
                    response = self.handle_replicate(query.method_arg, client_ip)
                elif isinstance(query, QueryCOMMAND):
                    created_event = self.handle_command_request(query.method_arg, allow_commands)
                    response = None
                else:
                    raise NotImplementedError  # can never happen

                if not isinstance(query, QueryCOMMAND):
                    self._answer_unless_client_is_gone(client_socket, query, response)

            if isinstance(query, QueryCOMMAND):
                # Without the lock, which the event server needs to make room in the pipe, but
                # before answering, so that the client gets the error
                if created_event is not None:
                    self._write_to_event_pipe(created_event)
                self._answer_unless_client_is_gone(client_socket, query, response)

        client_socket.close()  # TODO: This should be in a finally somehow.

    def _answer_unless_client_is_gone(
        self, client_socket: socket.socket, query: Query, response: Response
    ) -> None:
        try:
            self._answer_query(client_socket, query, response)
        except OSError as e:
            if e.errno != errno.EPIPE:
                raise

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

    # All commands are already locked with self._event_status.lock. Returns the line of an event
    # to create, which the caller writes to the event pipe without the lock.
    def handle_command_request(self, commandline: str, allow_commands: bool) -> bytes | None:
        if not allow_commands:
            raise MKClientError("Sorry. Commands are disallowed via TCP")
        self._logger.info("Executing command: %(commandline)s", {"commandline": commandline})
        parts = commandline.split(";")
        command = parts[0]
        replication_allow_command(self._config, command, self._slave_status)
        arguments = parts[1:]
        created_event: bytes | None = None
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
            created_event = self.handle_command_create(arguments)
        elif command == "CHANGESTATE":
            self.handle_command_changestate(arguments)
        elif command == "ACTION":
            self.handle_command_action(arguments)
        elif command == "SWITCHMODE":
            self.handle_command_switchmode(arguments)
        else:
            raise MKClientError(f"Unknown command {command}")
        return created_event

    def handle_command_delete(self, arguments: list[str]) -> None:
        if len(arguments) != 2:
            raise MKClientError("Wrong number of arguments for DELETE")
        event_ids, user = arguments
        ids = {int(event_id) for event_id in event_ids.split(",")}
        self._event_status.delete_events_by(
            lambda event: event["id"] in ids, user, self._event_server.get_rule_by_id
        )

    def handle_command_delete_events_of_host(self, arguments: list[str]) -> None:
        if len(arguments) != 2:
            raise MKClientError("Wrong number of arguments for DELETE_EVENTS_OF_HOST")
        hostname, user = arguments
        # Views assign events to hosts when showing them, so the core host of an event from
        # before the core knew the host doesn't suffice.
        designations = self._event_server.host_config.get_designations(hostname)
        self._event_status.delete_events_by(
            lambda event: (
                hostname in (event["core_host"], event["host"])
                or event["host"].lower() in designations
            ),
            user,
            self._event_server.get_rule_by_id,
        )

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
            # Spaces instead of tabs, like for the rewritten texts, see _rewritten(). A user ID
            # can't contain one, so like the other commands, we take the owner as it is.
            if comment:
                event["comment"] = scrub_string(comment)
            if contact:
                event["contact"] = scrub_string(contact)
            if user:
                event["owner"] = user
            self._history.add(event, "UPDATE", user)
        if failures:
            raise MKClientError(" ".join(failures))

    def handle_command_create(self, arguments: list[str]) -> bytes:
        # Would rather use process_syslog_messages(), but we are already
        # holding self._event_status.lock and it's sub functions are setting
        # self._event_status.lock too. The lock can not be allocated twice.
        # So handle_client() writes it to the event pipe once it has released the lock.
        return f"{';'.join(arguments)}\n".encode()

    def _write_to_event_pipe(self, line: bytes) -> None:
        # Without O_CREAT, which would create a file where the terminating event server removed the
        # pipe, and without waiting for a reader
        path = self.settings.paths.event_pipe.value
        try:
            fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            try:
                # Writing to a regular file would overwrite it from its start.
                if not stat.S_ISFIFO(os.fstat(fd).st_mode):
                    raise MKClientError(f"Cannot write to event pipe '{path}': Not a FIFO")
                if not self._write_waiting_for_room(fd, line):
                    raise MKClientError(
                        f"Cannot write to event pipe '{path}': Still full after "
                        f"{_CREATE_TIMEOUT:g} seconds. Is the Event Console overloaded?"
                    )
            finally:
                os.close(fd)
        except OSError as e:
            # Logged in one line, like a client error: It's no bug, e.g. while terminating.
            raise MKClientError(f"Cannot write to event pipe '{path}': {e.strerror}") from e

    def _write_waiting_for_room(self, fd: int, line: bytes) -> bool:
        """
        Writes the line, waiting for room until the deadline, or for good once a part of a line
        longer than PIPE_BUF is in: The next writer's line mustn't get glued to it, see pipe(7).
        Returns whether the line is in the pipe.
        """
        deadline = self._clock() + _CREATE_TIMEOUT
        poller = select.poll()
        poller.register(fd, select.POLLOUT)
        rest = memoryview(line)
        while rest:
            try:
                rest = rest[os.write(fd, rest) :]
                continue
            except BlockingIOError:
                pass
            # Until there is room or the reader is gone, which makes writing fail then
            if len(rest) < len(line):
                poller.poll()
            elif (left := deadline - self._clock()) > 0:
                poller.poll(left * 1000)
            else:
                return False
        return True

    def handle_command_changestate(self, arguments: list[str]) -> None:
        event_ids, user, newstate = arguments
        # Checked before changing any event. int() alone would accept e.g. 4, " 1" or "+1", and
        # check_mkevents reports an event with a state other than 0 to 3 as an invalid answer.
        if newstate not in {"0", "1", "2", "3"}:
            raise MKClientError(f"Invalid state '{newstate}', expected 0, 1, 2 or 3")
        state = int(newstate)
        failures = list[str]()
        for event_id in event_ids.split(","):
            event = self._event_status.event(int(event_id))
            if not event:
                failures.append(f"No event with id {event_id}.")
                continue
            event["state"] = state
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
        # The replication stays as it is, so e.g. a slave which took over keeps processing messages.
        self._logger.info("Flushed current status and historic events.")

    def handle_command_sync(self) -> None:
        self._event_status.save_status()

    def handle_command_resetcounters(self, arguments: list[str]) -> None:
        if arguments:
            self._logger.info("Resetting counters of rule %(rule)s", {"rule": arguments[0]})
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
                    self._event_server.host_config,
                    self._logger,
                    self._connection,
                    event,
                    user,
                    is_cancelling=False,
                    action_runner=self._action_runner,
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
                        self.settings,
                        self._config,
                        self._logger,
                        self._event_columns,
                        action,
                        event,
                        user,
                        action_runner=self._action_runner,
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
        self._logger.info(
            "Switched replication mode to '%(new_mode)s' by external command.",
            {"new_mode": new_mode},
        )

    def handle_replicate(self, argument: str, client_ip: str) -> Response:
        # Last time our slave got a config update
        try:
            last_update = int(argument)
            if self.settings.options.debug:
                self._logger.info(
                    "Replication: sync request from %(client_ip)s, last update %(seconds_ago)d seconds ago",
                    {"client_ip": client_ip, "seconds_ago": time.time() - last_update},
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
    *,
    fetch_master_state: FetchMasterState,
    signal_handler: SignalHandler,
) -> None:
    """Dispatching: starting and managing the two threads."""
    status_server.start()
    event_server.start()
    # Each task is due an interval after its last run, so reloaded intervals apply right away.
    last_housekeeping = last_retention = last_statistics = time.time()
    last_replication = 0.0  # force immediate replication after restart

    while not terminate_main_event.is_set():
        try:
            # Reload before using the configuration: If a reloaded one breaks the code below,
            # reloading a fixed one still works.
            if reload_config_event.is_set():
                reload_config_event.clear()
                try:
                    previous_master = _replication_master(config)
                    config, history = reload_configuration(
                        settings,
                        logger,
                        history,
                        event_status,
                        event_server,
                        status_server,
                        slave_status,
                    )
                    # Like a new one, a slave of another master syncs with it right away.
                    if _replication_master(config) != previous_master:
                        last_replication = 0.0
                except Exception:
                    # The previous configuration stays in effect.
                    logger.exception("Cannot reload the configuration")
                    if settings.options.debug:
                        raise

            # Act on the signals only between the tasks, see SignalHandler, right before waiting
            if (signum := signal_handler.take()) == signal.SIGHUP:
                logger.info("Received SIGHUP - going to reload configuration")
                reload_config_event.set()  # like the RELOAD command
                continue
            if signum is not None:
                logger.info("Signalled to death by signal %(signum)d", {"signum": signum})
                terminate(terminate_main_event, event_server, status_server)
                break

            # Wait until the next task is due or a reload is requested, but at most a second, as
            # neither a signal nor the SHUTDOWN command ends the wait.
            event_list = [
                last_housekeeping + config["housekeeping_interval"],
                last_retention + config["retention_interval"],
                last_statistics + config["statistics_interval"],
            ]
            if (next_replication := _next_replication(config, last_replication)) is not None:
                event_list.append(next_replication)

            time_left = max(0, min(event_list) - time.time())
            if reload_config_event.wait(min(time_left, 1)):
                continue  # reload before running any task
            # Terminate before the tasks, too: One can take long, e.g. vacuuming the SQLite history.
            if signal_handler.terminating():
                continue
            now = time.time()

            # Each task counts as run even if it fails, so a failing one doesn't keep failing
            # every second, keeping the tasks after it from running.
            if now > last_housekeeping + config["housekeeping_interval"]:
                last_housekeeping = now
                event_server.do_housekeeping()

            if now > last_retention + config["retention_interval"]:
                last_retention = now
                with event_status.lock:
                    event_status.save_status()

            if now > last_statistics + config["statistics_interval"]:
                last_statistics = now
                perfcounters.do_statistics()

            next_replication = _next_replication(config, last_replication)
            if next_replication is not None and now > next_replication:
                last_replication = now
                replication_pull(
                    settings,
                    config,
                    lock_configuration,
                    perfcounters,
                    event_status,
                    event_server,
                    slave_status,
                    logger,
                    fetch_master_state=fetch_master_state,
                )
        except Exception:
            logger.exception("Exception in main thread")
            if settings.options.debug:
                raise
            time.sleep(1)

    # Now wait for termination of the server threads
    event_server.join()
    status_server.join()


def _next_replication(config: Config, last_replication: float) -> float | None:
    """Returns when a replication slave syncs with its master next, None for any other EC"""
    replication = config["replication"]
    if replication is None or not is_replication_slave(config):  # None only helps mypy
        return None
    return last_replication + replication["interval"]


def _replication_master(config: Config) -> tuple[str, int] | None:
    """Returns the master of a replication slave, None for any other EC"""
    replication = config["replication"]
    if replication is None or not is_replication_slave(config):  # None only helps mypy
        return None
    return replication["master"]


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


def _changed_rule_ids(previous: Mapping[str, str], current: Mapping[str, str]) -> set[str]:
    """The IDs of the current rules which differ from the previous ones, or which are new

    Both map the IDs of the rules to their digests, see _rule_digests()."""
    return {id_ for id_, digest in current.items() if previous.get(id_) != digest}


def _rules_by_id(rule_packs: Iterable[ECRulePack]) -> dict[str, list[Rule]]:
    rules: dict[str, list[Rule]] = {}
    for rule_pack in rule_packs:
        for rule in rule_pack["rules"]:
            # Nobody validates rules written by hand, and the EC compiles no disabled ones, which
            # count no hits anyway, so they may lack an ID.
            if (id_ := rule.get("id")) is not None:
                rules.setdefault(id_, []).append(rule)
    return rules


def _rule_digests(rule_packs: Iterable[ECRulePack]) -> dict[str, str]:
    """A digest of all rules with each ID, telling which rules changed, also across restarts

    Several rules may have the same ID, so the digest covers all of them, but not their order, which
    e.g. moving their rule packs changes."""
    return {
        id_: hashlib.sha256(repr(sorted(map(_sorted_repr, rules))).encode("utf-8")).hexdigest()
        for id_, rules in _rules_by_id(rule_packs).items()
    }


def _sorted_repr(value: object) -> str:
    """Like repr(), but sorting the keys of dictionaries and the elements of sets

    So equal rules have the same text, also in other processes: Pretty printing the rules sorts the
    keys, but only of the sets it breaks into several lines, and equal sets may list their elements
    in different orders, e.g. sets of strings in other processes."""
    match value:
        case dict():
            items = (f"{_sorted_repr(key)}: {_sorted_repr(item)}" for key, item in value.items())
            return "{" + ", ".join(sorted(items)) + "}"
        case set() | frozenset():
            return f"{type(value).__name__}([{', '.join(sorted(map(_sorted_repr, value)))}])"
        case list():
            return "[" + ", ".join(map(_sorted_repr, value)) + "]"
        case tuple():
            return "(" + ", ".join(map(_sorted_repr, value)) + ",)"
        case _:
            return repr(value)


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
        connection: Connection,
    ) -> None:
        self.settings = settings
        self._config = config
        self._rule_digests: Mapping[str, str] = _rule_digests(config["rule_packs"])
        self._perfcounters = perfcounters
        self.lock = threading.Lock()
        self._history = history
        self._logger = logger
        self._connection = connection
        self.flush()

    def reload_configuration(self, config: Config, history: History) -> None:
        self._config = config
        self._history = history

    @property
    def rule_digests(self) -> Mapping[str, str]:
        """The digests of the rules in use, see _rule_digests()

        Using other rules replaces them instead of changing them, see use_rules()."""
        return self._rule_digests

    def use_rules(self, rule_digests: Mapping[str, str]) -> None:
        """Tells the rules the event server uses from now on, forgetting the hits of changed ones

        The hits of a changed rule would mix the ones of its previous version, so they start over.
        The event server replaces its rules holding the lock, so no hit of the new ones gets lost,
        and a message still running through the previous ones counts none, see count_rule_match().
        Like counted hits, saving the status later on keeps this, as failing to save it here would
        leave the reload half done. The rules come as their digests, see _rule_digests(), which the
        event server computes before taking the lock."""
        self._forget_hits_of_changed_rules(_changed_rule_ids(self._rule_digests, rule_digests))
        self._rule_digests = rule_digests

    def use_rules_of_master(self, rule_packs: Iterable[ECRulePack]) -> None:
        """Tells the rules a replication slave got from its master

        The hits of the rules come with the status of the master, see unpack_status(), so a restart
        of the slave keeps them. Like for unpack_status(), the caller holds the lock."""
        self._rule_digests = _rule_digests(rule_packs)

    def _forget_hits_of_changed_rules(self, changed_rule_ids: set[str]) -> None:
        if reset := sorted(changed_rule_ids & self._rule_stats.keys()):
            self._logger.info(
                "Resetting counters of changed rules %(rules)s", {"rules": ", ".join(reset)}
            )
            for rule_id in reset:
                del self._rule_stats[rule_id]

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
        Return beginning of current expectation interval.
        For new rules we should start with the inclusive start time for the event.
        """
        now = time.time()
        if rule_id not in self._interval_starts:
            start = self.clamp_timestamp_to_interval(interval, now, interval_count=0)
            self._interval_starts[rule_id] = start
            return start
        start = self._interval_starts[rule_id]

        # Make sure that if the user switches from day to hour and we
        # are still waiting for the first interval to begin, that we
        # do not wait for the next day.
        # Or if the start interval is stale then reset the interval.
        previous_interval = self.clamp_timestamp_to_interval(interval, now, interval_count=-1)
        next_interval = self.clamp_timestamp_to_interval(interval, now, interval_count=0)
        if not (previous_interval <= start <= next_interval):
            self._interval_starts[rule_id] = start = next_interval
        return start

    @staticmethod
    def clamp_timestamp_to_interval(
        interval: ExpectInterval, timestamp: float, interval_count: int
    ) -> int:
        length, offset = interval if isinstance(interval, tuple) else (interval, 0)
        offset *= 3600

        timestamp -= offset  # take into account timezone offset
        next_start = (timestamp // length + interval_count) * length
        next_start += offset
        return int(next_start)

    def start_next_interval(self, rule_id: str, interval: ExpectInterval) -> None:
        if rule_id not in self._interval_starts:
            next_start = self.interval_start(rule_id, interval)
        else:
            current_start = self.interval_start(rule_id, interval)
            next_start = self.clamp_timestamp_to_interval(interval, current_start, interval_count=1)
            self._interval_starts[rule_id] = next_start
        self._logger.debug(
            "Rule %(rule_id)s: next interval starts %(next_start)s (i.e. now + %(delay).2f sec)",
            {
                "rule_id": rule_id,
                "next_start": next_start,
                "delay": time.time() - next_start,
            },
        )

    def clear_interval_start(self, rule_id: str) -> None:
        self._interval_starts.pop(rule_id, None)

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
        self._initialize_event_limit_status()

    def save_status(self) -> None:
        now = time.time()
        status = self.pack_status()
        # Unlike replicating the status, restoring it needs to tell which counted rules changed.
        saved_status = {
            **status,
            "rule_digests": {
                id_: self._rule_digests[id_]
                for id_ in status["rule_stats"]
                if id_ in self._rule_digests
            },
        }
        path = self.settings.paths.status_file.value
        path_new = path.parent / (path.name + ".new")
        # Believe it or not: cPickle is more than two times slower than repr()
        with path_new.open(mode="wb") as f:
            f.write((repr(saved_status) + "\n").encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        path_new.rename(path)
        elapsed = time.time() - now
        self._logger.log(
            VERBOSE,
            "Saved event state to %(path)s in %(elapsed_ms).3fms.",
            {"path": path, "elapsed_ms": elapsed * 1000},
        )

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
                self._logger.info("Loaded event state from %(path)s.", {"path": path})
                # Like reloading, forget the hits of the rules changed meanwhile, e.g. by activating
                # changes while the EC was stopped. A previous version saved no digests, though.
                if (rule_digests := status.get("rule_digests")) is not None:
                    self._forget_hits_of_changed_rules(
                        _changed_rule_ids(rule_digests, self._rule_digests)
                    )
            except Exception:
                self._logger.exception("Error loading event state from %(path)s", {"path": path})
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
        self._num_overflow_events: dict[tuple[LimitKind, _LimitKey], int] = {}
        # The host names each open event is counted for by the host limit, by the identity of the
        # event, which unlike its fields never changes
        self._counted_host_keys: dict[int, tuple[str, HostName | None]] = {}
        for event in self._events:
            self._count_event_add(event)

    def _count_event_add(self, event: Event) -> None:
        host_key = self._host_key(event)
        self._counted_host_keys[id(event)] = host_key
        if host_key not in self.num_existing_events_by_host:
            self.num_existing_events_by_host[host_key] = 1
        else:
            self.num_existing_events_by_host[host_key] += 1

        if event["rule_id"] not in self.num_existing_events_by_rule:
            self.num_existing_events_by_rule[event["rule_id"]] = 1
        else:
            self.num_existing_events_by_rule[event["rule_id"]] += 1

        if (overflow_key := self._overflow_key(event)) is not None:
            self._num_overflow_events[overflow_key] = (
                self._num_overflow_events.get(overflow_key, 0) + 1
            )

    def _count_event_remove(self, event: Event) -> None:
        # Even if the host names of the event changed unnoticed, take back exactly what was counted.
        host_key = self._counted_host_keys.pop(id(event))

        self.num_existing_events -= 1
        self.num_existing_events_by_host[host_key] -= 1
        self.num_existing_events_by_rule[event["rule_id"]] -= 1
        if (overflow_key := self._overflow_key(event)) is not None:
            self._num_overflow_events[overflow_key] -= 1

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
        except ValueError:
            self._logger.exception(
                "Cannot remove event %(event_id)d: not present", {"event_id": event["id"]}
            )
            return
        # Before adding its history entry, so it no longer counts for the event limits even if that
        # raises, e.g. in debug mode.
        self._count_event_remove(event)
        self._history.add(event, delete_reason, user)

    # protected by self.lock
    def remove_oldest_event(self, ty: LimitKind, event: Event) -> None:
        """Removes the oldest event counting towards the same limit of the given kind as the event"""
        key = self._limit_key(ty, event)
        for other in self._events:
            if self._limit_key(ty, other) == key:
                self._logger.log(
                    VERBOSE,
                    "  Removing oldest event %(event_id)d of the %(type)s limit",
                    {"event_id": other["id"], "type": ty},
                )
                self.remove_event(other, "AUTODELETE")
                return

    # protected by self.lock
    def get_num_existing_events_by(self, ty: LimitKind, event: Event) -> int:
        match ty:
            case "overall":
                return self.num_existing_events
            case "by_rule":
                return self.num_existing_events_by_rule.get(event["rule_id"], 0)
            case "by_host":
                return self.num_existing_events_by_host.get(self._host_key(event), 0)
            case _ as unreachable:
                assert_never(unreachable)

    # protected by self.lock
    def has_overflow_event(self, ty: LimitKind, event: Event) -> bool:
        """Whether the overflow event about the limit of the given kind for the event is open"""
        return self._num_overflow_events.get((ty, self._limit_key(ty, event)), 0) > 0

    @classmethod
    def _overflow_key(cls, event: Event) -> tuple[LimitKind, _LimitKey] | None:
        """Returns which limit an overflow event is about, None for any other event"""
        if (ty := event.get("overflowed_limit")) is None:
            return None
        return ty, cls._limit_key(ty, event)

    @staticmethod
    def is_overflow_event(event: Event) -> bool:
        """Whether the event is about reaching an event limit, also if an older version created it"""
        return "overflowed_limit" in event or (
            event.get("application") == "Event Console"
            and _OVERFLOW_EVENT_TEXT.match(event.get("text", "")) is not None
        )

    @classmethod
    def creating_rule_id(cls, event: Event) -> str | None:
        """Returns the ID of the rule which created the event, None for an overflow event

        The overflow event about a rule limit has the rule's ID only to count towards that limit.
        """
        return None if cls.is_overflow_event(event) else event["rule_id"]

    @classmethod
    def _limit_key(cls, ty: LimitKind, event: Event) -> _LimitKey:
        """Returns what all events counting towards the same limit of the given kind share"""
        match ty:
            case "overall":
                return None
            case "by_rule":
                return event["rule_id"]
            case "by_host":
                return cls._host_key(event)
            case _ as unreachable:
                assert_never(unreachable)

    @staticmethod
    def _host_key(event: Event) -> tuple[str, HostName | None]:
        """Returns the combination of both host names, which the host limit counts separately"""
        return event["host"], event["core_host"]

    # protected by self.lock
    def follow_hosts_of(self, event: Event) -> None:
        """Lets the host limit count an open event for the host names it has now"""
        host_key = self._host_key(event)
        previous_host_key = self._counted_host_keys[id(event)]
        if host_key != previous_host_key:
            self.num_existing_events_by_host[previous_host_key] -= 1
            self.num_existing_events_by_host[host_key] = (
                self.num_existing_events_by_host.get(host_key, 0) + 1
            )
            self._counted_host_keys[id(event)] = host_key

    def cancel_events(
        self,
        event_server: EventServer,
        event_columns: Iterable[tuple[str, object]],
        new_event: Event,
        match_groups: MatchGroups,
        rule: Rule,
        *,
        action_runner: ActionRunner,
    ) -> None:
        """
        Cancel all events the belong to a certain rule id and are
        of the same "breed" as a new event.
        """
        with self.lock:
            to_delete = []
            for event in self._events:
                if self.creating_rule_id(event) == rule["id"] and self.cancelling_match(
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
                        event["text"] = _rewritten(rule["set_text"], event["text"], match_groups)
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
                                "Do not execute cancelling actions, event %(event_id)s's phase "
                                "is not 'open' but '%(previous_phase)s'",
                                {"event_id": event["id"], "previous_phase": previous_phase},
                            )
                        else:
                            do_event_actions(
                                self.settings,
                                self._config,
                                self._logger,
                                self._connection,
                                event_server.host_config,
                                event_columns,
                                actions,
                                event,
                                is_cancelling=True,
                                action_runner=action_runner,
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
                    "Do not cancel event %(event_id)d: host is not the same (%(event_host)s != %(host)s)",
                    {"event_id": event["id"], "event_host": event["host"], "host": host},
                )
            return False

        # The same for the application. But in case there is cancelling based on the application
        # configured in the rule, then don't check for different applications.
        if "cancel_application" not in rule:
            application = new_event["application"]
            if "set_application" in rule:
                application = _rewritten(rule["set_application"], application, match_groups)
            if event["application"] != application:
                if debug:
                    self._logger.info(
                        "Do not cancel event %(event_id)d: application is not the same (%(event_application)s != %(application)s)",
                        {
                            "event_id": event["id"],
                            "event_application": event["application"],
                            "application": application,
                        },
                    )
                return False

        if event["facility"] != new_event["facility"] and debug:
            self._logger.info(
                "Do not cancel event %(event_id)d: syslog facility is not the same (%(event_facility)d != %(new_facility)d)",
                {
                    "event_id": event["id"],
                    "event_facility": event["facility"],
                    "new_facility": new_event["facility"],
                },
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
                        "Do not cancel event %(event_id)d: match group number %(group_nr)d does not match (%(prev_group)s != %(cur_group)s)",
                        {
                            "event_id": event["id"],
                            "group_nr": nr + 1,
                            "prev_group": prev_group,
                            "cur_group": cur_group,
                        },
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
                        "Do not cancel event %(event_id)d: syslog application match group number "
                        "%(group_nr)d does not match (%(prev_group)s != %(cur_group)s)",
                        {
                            "event_id": event["id"],
                            "group_nr": nr + 1,
                            "prev_group": prev_group,
                            "cur_group": cur_group,
                        },
                    )
                return False

        return True

    def count_rule_match(self, rule_id: str, *, rule_digests: Mapping[str, str]) -> None:
        """Counts a hit of the rule, unless a reload changed it since the message matched it

        The reload forgot the hits of the changed rule, so a hit of its previous version doesn't
        count. The digests of the rules the message ran through tell the version."""
        with self.lock:
            if rule_digests.get(rule_id) == self._rule_digests.get(rule_id):
                self._rule_stats.setdefault(rule_id, 0)
                self._rule_stats[rule_id] += 1

    # protected by self.lock
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
        # The event got the host names of the new occurrence, e.g. when counting several hosts.
        self.follow_hosts_of(found)

    def count_expected_event(self, event_server: EventServer, event: Event) -> None:
        # Holding the lock, nothing else removes the event before it is counted up.
        with self.lock:
            for ev in self._events:
                if self.creating_rule_id(ev) == event["rule_id"] and ev["phase"] == "counting":
                    self.count_event_up(ev, event)
                    return

        # None found, create one. No event limit drops it: The expected message would count as
        # missing otherwise, and as there is only one such event per rule, it can't flood the EC.
        event["count"] = 1
        event["phase"] = "counting"
        event_server.new_event_respecting_limits(event, droppable=False)

    def count_event(self, event_server: EventServer, event: Event, count: Count) -> Event | None:
        """
        Find previous occurrence of this event and account for
        one new occurrence. In case of negated count (expecting rules)
        we do never modify events that are already in the state "open"
        since the event has been created because the count was too
        low in the specified period of time.
        """
        found: Event | None = None
        # Holding the lock, nothing else removes the event before it is counted up.
        with self.lock:
            for ev in self._events:
                if self.creating_rule_id(ev) != event["rule_id"]:
                    continue  # e.g. the overflow event about the rule's limit

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

        if found is None:
            event["count"] = 1
            event["phase"] = "counting"
            if not event_server.new_event_respecting_limits(event):
                return None  # dropped because of an event limit, so don't open it
            found = event

        # Did we just count the event that was just one too much?
        if found["phase"] == "counting" and found["count"] >= count["count"]:
            found["phase"] = "open"
            return found  # do event action, return found copy of event
        return None  # do not do event action

    def delete_events_by(
        self, predicate: Callable[[Event], bool], user: str, get_rule: Callable[[str], Rule | None]
    ) -> None:
        for event in self._events[:]:
            if predicate(event):
                event["phase"] = "closed"
                if user:
                    event["owner"] = user
                self.remove_event(event, "DELETE", user)
                rule_id = self.creating_rule_id(event)
                if event["id"] + 1 == self._next_event_id and rule_id in self._interval_starts:
                    event_rule = get_rule(rule_id)
                    if event_rule is not None and "expect" in event_rule:
                        self.clear_interval_start(rule_id)
                        self.interval_start(rule_id, event_rule["expect"]["interval"])

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


def is_syncing_replication_slave(config: ConfigFromWATO, slave_status: SlaveStatus) -> bool:
    """Whether the EC replicates its events from its master, which then handles them"""
    return is_replication_slave(config) and slave_status["mode"] == "sync"


# The next sync replaces the events of a syncing slave anyway.
_COMMANDS_CHANGING_THE_SYNCED_STATUS = {
    "ACTION",
    "CHANGESTATE",
    "DELETE",
    "DELETE_EVENTS_OF_HOST",
    "UPDATE",
}


def replication_allow_command(config: Config, command: str, slave_status: SlaveStatus) -> None:
    if (
        is_syncing_replication_slave(config, slave_status)
        and command in _COMMANDS_CHANGING_THE_SYNCED_STATUS
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
        # Both are whole seconds, so if the slave synced in the second of the reload, it might have
        # synced before the reload: Better send the configuration once more.
        if last_update <= config["last_reload"]:
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
    *,
    fetch_master_state: FetchMasterState,
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
        # Without the locks, so that the EC goes on working while it waits for its master
        try:
            fetched: dict[str, Any] | Exception = fetch_master_state(config, slave_status)
        except ReplicationInterrupted:
            # Not counting as the master being down, which could lead to a takeover
            logger.info("Replication: not waiting for the master any longer, as the EC terminates")
            return
        except Exception as e:
            fetched = e
        with event_status.lock, lock_configuration:
            # Switched by the SWITCHMODE command meanwhile, so the sync is outdated
            if slave_status["mode"] != mode:
                logger.info(
                    "Replication: dropping the sync with the master, as the mode switched to "
                    "%(mode)s meanwhile",
                    {"mode": slave_status["mode"]},
                )
                return
            try:
                if isinstance(fetched, Exception):
                    raise fetched  # handled like failing to update the state below
                replication_update_state(settings, config, event_status, event_server, fetched)
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
                            "Replication: master reachable again after %(seconds)d seconds, "
                            "switching back to sync mode",
                            {"seconds": (now - slave_status["last_master_down"])},
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
                            logger.exception(
                                "Replication: no takeover since master was never reached."
                            )
                    else:
                        offline = now - slave_status["last_sync"]
                        if offline < repl_settings["takeover"]:
                            if repl_settings.get("logging"):
                                logger.warning(
                                    "Replication: no takeover yet, still %(seconds)d seconds to wait",
                                    {"seconds": repl_settings["takeover"] - offline},
                                )
                        else:
                            logger.info(
                                "Replication: master not reached for %(seconds)d seconds, taking over!",
                                {"seconds": offline},
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
        replication = config["replication"]
        if replication is None:  # help mypy a bit
            raise ValueError("no replication settings")
        save_master_config(settings, replication["master"], new_state)
        # Like loading the configuration of a slave, use the master's rules and actions.
        slave_config = make_config(_with_master_config(config, new_state))
        event_server.compile_rules(slave_config["rule_packs"])
        # Update the configuration in place, as the main loop and the threads share it.
        config.update(slave_config)
        event_status.use_rules_of_master(slave_config["rule_packs"])

    # Update to the masters' event state
    event_status.unpack_status(new_state["status"])


def save_master_config(
    settings: Settings, master: tuple[str, int], new_state: Mapping[str, object]
) -> None:
    cmk.ccc.store.save_object_to_file(
        settings.paths.master_config_file.value,
        {
            "master": master,
            "rules": new_state["rules"],
            "rule_packs": new_state["rule_packs"],
            "actions": new_state["actions"],
        },
    )


def _with_master_config(config: ConfigFromWATO, master_config: Mapping[str, Any]) -> ConfigFromWATO:
    """Returns the configuration of a replication slave using the rules and actions of its master"""
    return {
        **config,
        "rules": master_config["rules"],
        "rule_packs": master_config.get("rule_packs", []),
        "actions": master_config["actions"],
    }


def load_master_config(settings: Settings, config: ConfigFromWATO, logger: Logger) -> bool:
    """Uses the saved configuration of the master of a replication slave

    Returns whether it is from another master than the configured one, so the slave ignores it.
    """
    path = settings.paths.master_config_file.value
    try:
        # Like a missing file, an empty one left behind by an interrupted save yields None.
        if (
            master_config := cmk.ccc.store.load_object_from_file(path, default=None, debug=False)
        ) is None:
            logger.info("Replication: no previously saved master state available")
            return False
        if _is_from_other_master(master_config, config):
            logger.info(
                "Replication: ignoring the saved configuration of the previous master %(master)r",
                {"master": master_config["master"]},
            )
            return True
        config.update(_with_master_config(config, master_config))
        logger.info(
            "Replication: restored %(rule_packs)d rule packs and %(actions)d actions from %(path)s",
            {
                "rule_packs": len(config["rule_packs"]),
                "actions": len(config["actions"]),
                "path": path,
            },
        )
    except Exception:
        logger.exception("Replication: no previously saved master state available")
    return False


def _is_from_other_master(master_config: Mapping[str, object], config: ConfigFromWATO) -> bool:
    """Whether a saved configuration of a master is from another one than the configured master

    Older versions didn't save the master, so assume that it's the configured one then.
    """
    replication = config["replication"]
    return (
        replication is not None
        and master_config.get("master", replication["master"]) != replication["master"]
    )


class ReplicationInterrupted(Exception):
    """Ends pulling the state from the master early, as the EC terminates"""


# How often a slave waiting for its master looks whether the EC terminates: "omd stop" kills it
# after a minute, and the connect timeout can be longer.
_TERMINATION_CHECK_INTERVAL = 1.0  # seconds


def get_state_from_master(
    config: Config, slave_status: SlaveStatus, *, terminating: Callable[[], bool]
) -> Any:
    """Raises ReplicationInterrupted once the given function tells that the EC terminates"""
    repl_settings = config["replication"]
    if repl_settings is None:
        raise ValueError("no replication settings")
    timeout = repl_settings["connect_timeout"]
    response_text = b""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Without blocking, so that waiting can look whether the EC terminates
            sock.setblocking(False)
            if (err := sock.connect_ex(repl_settings["master"])) not in (0, errno.EINPROGRESS):
                raise OSError(err, os.strerror(err))
            _wait_for_master(sock, select.POLLOUT, timeout=timeout, terminating=terminating)
            if err := sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR):
                raise OSError(err, os.strerror(err))
            # The request fits into the empty send buffer of the new connection.
            sock.sendall(
                b"REPLICATE %d\n" % (slave_status["last_sync"] if slave_status["last_sync"] else 0)
            )
            sock.shutdown(socket.SHUT_WR)

            while True:
                _wait_for_master(sock, select.POLLIN, timeout=timeout, terminating=terminating)
                chunk = sock.recv(8192)
                response_text += chunk
                if not chunk:
                    break

        return ast.literal_eval(response_text.decode("utf-8"))
    except ReplicationInterrupted:
        raise

    except SyntaxError as e:
        raise Exception(
            f"Invalid response from event daemon: <pre>{repr(response_text)}</pre>"
        ) from e

    except OSError as e:
        raise Exception("Master not responding") from e

    except Exception as e:
        raise Exception("Cannot connect to event daemon") from e


def _wait_for_master(
    sock: socket.socket, events: int, *, timeout: float, terminating: Callable[[], bool]
) -> None:
    """Waits for the events like a socket with the timeout, but raises ReplicationInterrupted once
    the EC terminates"""
    poller = select.poll()  # unlike select(), for file descriptors beyond FD_SETSIZE, too
    poller.register(sock, events)
    deadline = time.monotonic() + timeout
    while not terminating():
        if (left := deadline - time.monotonic()) <= 0:
            raise TimeoutError("timed out")
        if poller.poll(min(left, _TERMINATION_CHECK_INTERVAL) * 1000):
            return
    raise ReplicationInterrupted


def save_slave_status(settings: Settings, slave_status: SlaveStatus) -> None:
    # The store never leaves a partially written file behind, even if threads save at once.
    cmk.ccc.store.save_object_to_file(settings.paths.slave_status_file.value, slave_status)


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
            # Like a missing file, an empty one left behind by an interrupted save yields None.
            saved_status = cmk.ccc.store.load_object_from_file(path, default=None, debug=False)
            if saved_status is not None:
                slave_status.update(saved_status)
        except Exception:  # e.g. a file edited by hand
            saved_status = None
        if saved_status is None:
            # A new slave starts syncing, but e.g. a slave which took over keeps doing so.
            if slave_status["mode"] == "master":
                slave_status.update(default_slave_status_sync())
            save_slave_status(settings, slave_status)
    else:
        if path.exists():
            path.unlink()
        slave_status.update(default_slave_status_master())


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
    """Adds the fields derived from the configuration, replacing any existing ones"""
    return {
        **config,
        "action": {action["id"]: action for action in config["actions"]},
        "last_reload": int(time.time()),
    }


def load_configuration(settings: Settings, logger: Logger, slave_status: SlaveStatus) -> Config:
    config, start_over = _read_configuration(settings, logger)
    _set_log_levels(_configured_log_levels(settings, logger, config))
    _update_replication_status(settings, logger, slave_status, config, start_over=start_over)
    return config


def _read_configuration(settings: Settings, logger: Logger) -> tuple[Config, bool]:
    """Returns the configuration and whether the EC has to start over as a replication slave

    That's the case if the saved configuration of the master is from another master.
    """
    config = load_active_config(settings)
    # Are we a replication slave? Parts of the configuration will be overridden by values from the
    # master. Only slaves, not former ones, use the saved configuration of their master.
    start_over = False
    if is_replication_slave(config):
        start_over = load_master_config(settings, config, logger)
    return make_config(config), start_over


def _configured_log_levels(settings: Settings, logger: Logger, config: Config) -> dict[Logger, int]:
    """Returns the log levels of the configuration, unless the command line sets the verbosity"""
    if settings.options.verbosity != 0:
        return {}
    levels = config["log_level"]
    log_levels = {
        logger: levels["cmk.mkeventd"],
        logger.getChild("EventServer"): levels["cmk.mkeventd.EventServer"],
        logger.getChild("EventStatus"): levels["cmk.mkeventd.EventStatus"],
        logger.getChild("StatusServer"): levels["cmk.mkeventd.StatusServer"],
        logger.getChild("lock"): levels["cmk.mkeventd.lock"],
    }
    if "cmk.mkeventd.EventServer.snmp" in levels:
        log_levels[logger.getChild("EventServer.snmp")] = levels["cmk.mkeventd.EventServer.snmp"]
    return log_levels


def _set_log_levels(log_levels: Mapping[Logger, int]) -> None:
    for each_logger, level in log_levels.items():
        each_logger.setLevel(level)


def _update_replication_status(
    settings: Settings,
    logger: Logger,
    slave_status: SlaveStatus,
    config: Config,
    *,
    start_over: bool,
) -> None:
    if start_over:
        # Like a newly set up slave, sync completely with the new master.
        settings.paths.master_config_file.value.unlink()
        slave_status.update(default_slave_status_sync())
        save_slave_status(settings, slave_status)
    else:
        update_slave_status(slave_status, settings, config)
    if is_replication_slave(config):
        logger.info(
            "Replication: slave configuration, current mode: %(mode)s",
            {"mode": slave_status["mode"]},
        )


def reload_configuration(
    settings: Settings,
    logger: Logger,
    history: History,
    event_status: EventStatus,
    event_server: EventServer,
    status_server: StatusServer,
    slave_status: SlaveStatus,
) -> tuple[Config, History]:
    config, start_over = _read_configuration(settings, logger)
    log_levels = _configured_log_levels(settings, logger, config)
    previous_log_levels = {each_logger: each_logger.level for each_logger in log_levels}
    try:
        # Creating the history depends on the log levels, so set them first.
        _set_log_levels(log_levels)
        new_history = create_history(
            settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
        )
        try:
            # It takes the locks for replacing its configuration itself.
            event_server.reload_configuration(config, new_history)
        except Exception:
            new_history.close()
            raise
    except Exception:
        _set_log_levels(previous_log_levels)
        raise
    # Update the replication status only now that the new configuration is in effect, so a failed
    # reload keeps the previous one. Like the status server switching the replication mode, hold the
    # lock of the event status, so neither undoes what the other one changes. As the event server
    # uses the new configuration already, complete the reload even if updating the replication
    # status fails.
    with event_status.lock:
        try:
            _update_replication_status(
                settings, logger, slave_status, config, start_over=start_over
            )
        except Exception:
            logger.exception("Cannot update the replication status")

    # Until now, the status server answered replication requests with the previous configuration,
    # so stamp the reload only now: A slave which synced meanwhile gets the new one with its next
    # sync then.
    config["last_reload"] = int(time.time())
    event_status.reload_configuration(config, new_history)
    status_server.reload_configuration(config, new_history)
    # Once a status query still reading it is answered, only the event server may still use the
    # previous history where it doesn't hold the lock, e.g. to record that an event reached its
    # count. With SQLite, recording that then fails, which the history logs, while MongoDB
    # reconnects.
    with event_status.lock:
        try:
            history.close()
        except Exception:
            logger.exception("Cannot close the previous history")
    logger.info("Reloaded configuration.")
    return config, new_history


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
    omd_root = Path(os.environ.get("OMD_ROOT", ""))
    os.unsetenv("LANG")
    logger = getLogger("cmk.mkeventd")
    version_info = get_general_version_infos(omd_root)
    settings = create_settings(version_info["version"], omd_root, sys.argv)
    pid_path = settings.paths.pid_file.value
    try:
        setup_logging_handler(sys.stderr)
        logging.getLogger("cmk").setLevel(verbosity_to_log_level(settings.options.verbosity))

        settings.paths.log_file.value.parent.mkdir(parents=True, exist_ok=True)
        if not settings.options.foreground:
            open_log(settings.paths.log_file.value)

        logger.info("-" * 65)
        logger.info("mkeventd version %(version)s starting", {"version": version_info["version"]})

        slave_status = default_slave_status_master()
        config = load_configuration(settings, logger, slave_status)
        history = create_history(
            settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
        )

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
                "Removed orphaned PID file %(pid_path)s (process %(pid)d not running anymore).",
                {"pid_path": pid_path, "pid": old_pid},
            )

        # Make sure paths exist
        settings.paths.event_pipe.value.parent.mkdir(parents=True, exist_ok=True)
        settings.paths.event_pipe.value.parent.chmod(0o751)
        settings.paths.status_file.value.parent.mkdir(parents=True, exist_ok=True)

        # First do all things that might fail, before daemonizing
        perfcounters = Perfcounters(logger.getChild("lock.perfcounters"))
        connection = LocalConnection()
        event_status = EventStatus(
            settings, config, perfcounters, history, logger.getChild("EventStatus"), connection
        )
        lock_configuration = ECLock(logger.getChild("lock.configuration"))
        action_runner = ActionRunner(logger, history)
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
            connection,
            omd_site(),
            action_runner,
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
            connection,
            action_runner,
        )

        event_status.load_status(event_server)
        event_server.compile_rules(config["rule_packs"])

        if not settings.options.foreground:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            cmk.ccc.daemon.daemonize()
            logger.info("Daemonized with PID %(pid)d.", {"pid": os.getpid()})

        with cmk.ccc.daemon.pid_file_lock(pid_path):
            signal_handler = SignalHandler(logger)
            signal.signal(signal.SIGHUP, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGQUIT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Now let's go...
            action_runner.start()
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
                fetch_master_state=functools.partial(
                    get_state_from_master,
                    # On a signal, and on the SHUTDOWN command, too
                    terminating=lambda: (
                        signal_handler.terminating() or terminate_main_event.is_set()
                    ),
                ),
                signal_handler=signal_handler,
            )

            # We reach this point, if the server has been killed by
            # a signal or hitting Ctrl-C (in foreground mode)

            # TODO: Move this cleanup stuff to the classes that are responsible for these resources

            logger.log(VERBOSE, "Saving final event state")
            event_status.save_status()

            # Those triggered by the rest of the event pipe, see EventServer._keep_serving(), well
            # before "omd stop" kills the EC after a minute
            logger.log(VERBOSE, "Running pending actions")
            action_runner.stop(timeout=10)

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

    except Exception:
        if settings.options.debug:
            raise

        CrashReportStore().save(
            ECCrashReport(
                crash_report_base_path=make_crash_report_base_path(omd_root),
                crash_info=ECCrashReport.make_crash_info(version_info, None),
            )
        )
        bail_out(logger, traceback.format_exc())


class ECCrashReport(ABCCrashReport[None]):
    @classmethod
    @override
    def type(cls) -> str:
        return "ec"
