#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Refactor/document locking. It is not clear when and how to apply
# locks or when they are held by which component.

# TODO: Refactor events to be handled as objects, e.g. in case when
# creating objects. Or at least update the documentation. It is not clear
# which fields are mandatory for the events.

import abc
import ast
import datetime
import errno
import json
from logging import Logger, getLogger
import os
from pathlib import Path
import pprint
import re
import select
import signal
import socket
import sys
import threading
import time
import traceback
from types import FrameType
from typing import Any, AnyStr, Dict, Iterable, Iterator, List, Optional, Tuple, Type, Union

import dateutil.parser
import dateutil.tz
from six import ensure_binary

import cmk.utils.version as cmk_version
import cmk.utils.daemon
import cmk.utils.defines
import cmk.utils.log as log
from cmk.utils.log import VERBOSE
import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.render
import cmk.utils.regex
import cmk.utils.debug
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.exceptions import MKException
from cmk.utils.type_defs import HostName
import cmk.utils.store as store
import livestatus

from .actions import do_notify, do_event_action, do_event_actions, event_has_opened
from .crash_reporting import ECCrashReport, CrashReportStore
from .history import ActiveHistoryPeriod, History, scrub_string, quote_tab, get_logfile
from .host_config import HostConfig, HostInfo
from .query import MKClientError, Query, QueryGET, filter_operator_in
from .rule_packs import load_config as load_config_using
from .settings import FileDescriptor, PortNumber, Settings, settings as create_settings
from .snmp import SNMPTrapEngine

# TODO: We really, really need a stricter type here, this is *the* central data structure in the EC!
Event = Dict[str, Any]


class SyslogPriority:
    NAMES = {
        0: "emerg",
        1: "alert",
        2: "crit",
        3: "err",
        4: "warning",
        5: "notice",
        6: "info",
        7: "debug",
    }

    def __init__(self, value: int) -> None:
        super().__init__()
        self.value = value

    def __repr__(self):
        return "SyslogPriority(%d)" % self.value

    def __str__(self):
        try:
            return self.NAMES[self.value]
        except KeyError:
            return "(unknown priority %d)" % self.value


class SyslogFacility:
    NAMES = {
        0: 'kern',
        1: 'user',
        2: 'mail',
        3: 'daemon',
        4: 'auth',
        5: 'syslog',
        6: 'lpr',
        7: 'news',
        8: 'uucp',
        9: 'cron',
        10: 'authpriv',
        11: 'ftp',
        12: "ntp",
        13: "logaudit",
        14: "logalert",
        15: "clock",
        16: 'local0',
        17: 'local1',
        18: 'local2',
        19: 'local3',
        20: 'local4',
        21: 'local5',
        22: 'local6',
        23: 'local7',
        31: 'snmptrap',  # HACK!
    }

    def __init__(self, value: int) -> None:
        super().__init__()
        self.value = int(value)

    def __repr__(self):
        return "SyslogFacility(%d)" % self.value

    def __str__(self):
        try:
            return self.NAMES[self.value]
        except KeyError:
            return "(unknown facility %d)" % self.value


def scrub_and_decode(s: AnyStr) -> str:
    return ensure_str_with_fallback(scrub_string(s), encoding="utf-8", fallback="latin-1")


#.
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


class ECLock:
    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger
        self._lock = threading.Lock()

    def acquire(self, blocking: bool = True) -> bool:
        self._logger.debug("[%s] Trying to acquire lock", threading.current_thread().name)
        # Suppression due to https://github.com/PyCQA/pylint/issues/3212,
        # already fixed in astroid, but no released version yet. :-/
        ret = self._lock.acquire(blocking)  # pylint: disable=assignment-from-no-return
        if ret is True:
            self._logger.debug("[%s] Acquired lock", threading.current_thread().name)
        else:
            self._logger.debug("[%s] Non-blocking aquire failed", threading.current_thread().name)
        return ret

    def release(self) -> None:
        self._logger.debug("[%s] Releasing lock", threading.current_thread().name)
        self._lock.release()

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False  # Do not swallow exceptions


class ECServerThread(threading.Thread):
    @abc.abstractmethod
    def serve(self) -> None:
        raise NotImplementedError()

    def __init__(self, name: Any, logger: Logger, settings: Settings, config: Dict[str, Any],
                 slave_status: Dict[str, Any], profiling_enabled: bool, profile_file: Path) -> None:
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
        while not self._terminate_event.is_set():
            try:
                with cmk.utils.profile.Profile(enabled=self._profiling_enabled,
                                               profile_file=str(self._profile_file)):
                    self.serve()
            except Exception:
                self._logger.exception("Exception in %s server" % self.name)
                if self.settings.options.debug:
                    raise
                time.sleep(1)
        self._logger.info("Terminated")

    def terminate(self) -> None:
        self._terminate_event.set()


def terminate(terminate_main_event: threading.Event, event_server: 'EventServer',
              status_server: 'StatusServer') -> None:
    terminate_main_event.set()
    status_server.terminate()
    event_server.terminate()


def bail_out(logger: Logger, reason: str) -> None:
    logger.error("FATAL ERROR: %s" % reason)
    sys.exit(1)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def drain_pipe(pipe):
    while True:
        try:
            readable = select.select([pipe], [], [], 0.1)[0]
        except select.error as e:
            if e.args[0] != errno.EINTR:
                raise
            continue

        data = None
        if pipe in readable:
            try:
                data = os.read(pipe, 4096)
                if not data:  # EOF
                    break
            except Exception:
                break  # Error while reading
        else:
            break  # No data available


def match(pattern: str, text: str, complete: bool = True) -> Union[bool, Tuple[str, ...]]:
    """Performs an EC style matching test of pattern on text

    Returns False in case of no match or a tuple with the match groups.
    In case no match group is produced, it returns an empty tuple."""
    if pattern is None:
        return ()

    if isinstance(pattern, str):
        if complete:
            return () if pattern == text.lower() else False
        return () if pattern in text.lower() else False

    # Assume compiled regex
    m = pattern.search(text)
    return bool(m) and tuple('' if g is None else g for g in m.groups())


def format_pattern(pat):
    try:
        return pat.pattern
    except Exception:
        return pat


# Sorry: this code is dupliated in web/plugins/wato/mkeventd.py
def match_ipv4_network(pattern, ipaddress_text):
    network, network_bits = parse_ipv4_network(pattern)  # is validated by valuespec
    if network_bits == 0:
        return True  # event if ipaddress is empty
    try:
        ipaddress = parse_ipv4_address(ipaddress_text)
    except Exception:
        return False  # invalid address never matches

    # first network_bits of network and ipaddress must be
    # identical. Create a bitmask.
    bitmask = 0
    for n in range(32):
        bitmask = bitmask << 1
        if n < network_bits:
            bit = 1
        else:
            bit = 0
        bitmask += bit

    return (network & bitmask) == (ipaddress & bitmask)


def parse_ipv4_address(text):
    parts = list(map(int, text.split(".")))
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]


def parse_ipv4_network(text):
    if "/" not in text:
        return parse_ipv4_address(text), 32

    network_text, bits_text = text.split("/")
    return parse_ipv4_address(network_text), int(bits_text)


def replace_groups(text, origtext, match_groups):
    # replace \0 with text itself. This allows to add information
    # in front or and the end of a message
    text = text.replace("\\0", origtext)

    # Generic replacement with \1, \2, ...
    match_groups_message = match_groups.get("match_groups_message")
    if isinstance(match_groups_message, tuple):
        for nr, g in enumerate(match_groups_message):
            text = text.replace("\\%d" % (nr + 1), g)

    # Replacement with keyword
    # Right now we have
    # $MATCH_GROUPS_MESSAGE_x$
    # $MATCH_GROUPS_SYSLOG_APPLICATION_x$
    for key_prefix, values in match_groups.items():
        if not isinstance(values, tuple):
            continue

        for idx, match_value in enumerate(values):
            text = text.replace("$%s_%d$" % (key_prefix.upper(), idx + 1), match_value)

    return text


class MKSignalException(MKException):
    def __init__(self, signum: int) -> None:
        MKException.__init__(self, "Got signal %d" % signum)
        self._signum = signum


#.
#   .--Timeperiods---------------------------------------------------------.
#   |      _____ _                                _           _            |
#   |     |_   _(_)_ __ ___   ___ _ __   ___ _ __(_) ___   __| |___        |
#   |       | | | | '_ ` _ \ / _ \ '_ \ / _ \ '__| |/ _ \ / _` / __|       |
#   |       | | | | | | | | |  __/ |_) |  __/ |  | | (_) | (_| \__ \       |
#   |       |_| |_|_| |_| |_|\___| .__/ \___|_|  |_|\___/ \__,_|___/       |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   |  Timeperiods are used in rule conditions                             |
#   '----------------------------------------------------------------------'


class TimePeriods:
    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger
        self._periods: Optional[Dict[str, Tuple[str, bool]]] = None
        self._last_update = 0

    def _update(self) -> None:
        if self._periods is not None and int(time.time() / 60.0) == self._last_update:
            return  # only update once a minute
        try:
            table = livestatus.LocalConnection().query("GET timeperiods\nColumns: name alias in")
            periods: Dict[str, Tuple[str, bool]] = {}
            for tpname, alias, isin in table:
                periods[tpname] = (alias, bool(isin))
            self._periods = periods
            self._last_update = int(time.time() / 60.0)
        except Exception as e:
            self._logger.exception("Cannot update timeperiod information: %s" % e)
            raise

    def check(self, tpname: str) -> bool:
        self._update()
        if not self._periods:
            self._logger.warning("no timeperiod information, assuming %s is active" % tpname)
            return True
        if tpname not in self._periods:
            self._logger.warning("no such timeperiod %s, assuming it is active" % tpname)
            return True
        return self._periods[tpname][1]


#.
#   .--Perfcounters--------------------------------------------------------.
#   |      ____            __                       _                      |
#   |     |  _ \ ___ _ __ / _| ___ ___  _   _ _ __ | |_ ___ _ __ ___       |
#   |     | |_) / _ \ '__| |_ / __/ _ \| | | | '_ \| __/ _ \ '__/ __|      |
#   |     |  __/  __/ |  |  _| (_| (_) | |_| | | | | ||  __/ |  \__ \      |
#   |     |_|   \___|_|  |_|  \___\___/ \__,_|_| |_|\__\___|_|  |___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper class for performance counting                               |
#   '----------------------------------------------------------------------'


def lerp(a, b, t):
    """Linear interpolation between a and b with weight t"""
    return (1 - t) * a + t * b


class Perfcounters:
    _counter_names = [
        "messages",
        "rule_tries",
        "rule_hits",
        "drops",
        "overflows",
        "events",
        "connects",
    ]

    # Average processing times
    _weights = {
        "processing": 0.99,  # event processing
        "sync": 0.95,  # Replication sync
        "request": 0.95,  # Client requests
    }

    # TODO: Why aren't self._times / self._rates / ... not initialized with their defaults?
    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._lock = ECLock(logger)

        # Initialize counters
        self._counters = {n: 0 for n in self._counter_names}
        self._old_counters: Dict[str, int] = {}
        self._rates: Dict[str, float] = {}
        self._average_rates: Dict[str, float] = {}
        self._times: Dict[str, float] = {}
        self._last_statistics: Optional[float] = None

        self._logger = logger.getChild("Perfcounters")

    def count(self, counter: str) -> None:
        with self._lock:
            self._counters[counter] += 1

    def count_time(self, counter: str, ptime: float) -> None:
        with self._lock:
            if counter in self._times:
                self._times[counter] = lerp(ptime, self._times[counter], self._weights[counter])
            else:
                self._times[counter] = ptime

    def do_statistics(self) -> None:
        with self._lock:
            now = time.time()
            if self._last_statistics:
                duration = now - self._last_statistics
            else:
                duration = 0
            for name, value in self._counters.items():
                if duration:
                    delta = value - self._old_counters[name]
                    rate = delta / duration
                    self._rates[name] = rate
                    if name in self._average_rates:
                        # We could make the weight configurable
                        self._average_rates[name] = lerp(rate, self._average_rates[name], 0.9)
                    else:
                        self._average_rates[name] = rate

            self._last_statistics = now
            self._old_counters = self._counters.copy()

    @classmethod
    def status_columns(cls: Type['Perfcounters']) -> List[Tuple[str, float]]:
        columns: List[Tuple[str, float]] = []
        # Please note: status_columns() and get_status() need to produce lists with exact same column order
        for name in cls._counter_names:
            columns.append(("status_" + name, 0))
            columns.append(("status_" + name.rstrip("s") + "_rate", 0.0))
            columns.append(("status_average_" + name.rstrip("s") + "_rate", 0.0))

        for name in cls._weights:
            columns.append(("status_average_%s_time" % name, 0.0))

        return columns

    def get_status(self) -> List[float]:
        with self._lock:
            row: List[float] = []
            # Please note: status_columns() and get_status() need to produce lists with exact same column order
            for name in self._counter_names:
                row.append(self._counters[name])
                row.append(self._rates.get(name, 0.0))
                row.append(self._average_rates.get(name, 0.0))

            for name in self._weights:
                row.append(self._times.get(name, 0.0))

            return row


#.
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
    month_names = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    def __init__(self,
                 logger: Logger,
                 settings: Settings,
                 config: Dict[str, Any],
                 slave_status: Dict[str, Any],
                 perfcounters: Perfcounters,
                 lock_configuration: ECLock,
                 history: History,
                 event_status: 'EventStatus',
                 event_columns: List[Tuple[str, Any]],
                 create_pipes_and_sockets: bool = True) -> None:
        super().__init__(name="EventServer",
                         logger=logger,
                         settings=settings,
                         config=config,
                         slave_status=slave_status,
                         profiling_enabled=settings.options.profile_event,
                         profile_file=settings.paths.event_server_profile.value)
        self._syslog: Optional[socket.socket] = None
        self._syslog_tcp: Optional[socket.socket] = None
        self._snmptrap: Optional[socket.socket] = None

        # TODO: Improve type!
        self._rules: List[Any] = []
        self._hash_stats = []
        for _unused_facility in range(32):
            self._hash_stats.append([0] * 8)

        self.host_config = HostConfig(self._logger)
        self._perfcounters = perfcounters
        self._lock_configuration = lock_configuration
        self._history = history
        self._event_status = event_status
        self._event_columns = event_columns
        self._message_period = ActiveHistoryPeriod()
        self._rule_matcher = RuleMatcher(self._logger, config)
        self._event_creator = EventCreator(self._logger, config)

        # HACK for testing: The real fix would involve breaking up these huge
        # class monsters.
        if not create_pipes_and_sockets:
            return

        self.create_pipe()
        self.open_eventsocket()
        self.open_syslog()
        self.open_syslog_tcp()
        self.open_snmptrap()
        self._snmp_trap_engine = SNMPTrapEngine(self.settings, self._config,
                                                self._logger.getChild("snmp"), self.handle_snmptrap)

    @classmethod
    def status_columns(cls):
        columns = cls._general_columns()
        columns += Perfcounters.status_columns()
        columns += cls._replication_columns()
        columns += cls._event_limit_columns()
        return columns

    @classmethod
    def _general_columns(cls):
        return [
            ("status_config_load_time", 0),
            ("status_num_open_events", 0),
            ("status_virtual_memory_size", 0),
        ]

    @classmethod
    def _replication_columns(cls):
        return [
            ("status_replication_slavemode", ""),
            ("status_replication_last_sync", 0.0),
            ("status_replication_success", False),
        ]

    @classmethod
    def _event_limit_columns(cls):
        return [
            ("status_event_limit_host", 0),
            ("status_event_limit_rule", 0),
            ("status_event_limit_overall", 0),
            ("status_event_limit_active_hosts", []),
            ("status_event_limit_active_rules", []),
            ("status_event_limit_active_overall", False),
        ]

    def get_status(self):
        row: List[Any] = []

        row += self._add_general_status()
        row += self._perfcounters.get_status()
        row += self._add_replication_status()
        row += self._add_event_limit_status()

        return [row]

    def _add_general_status(self) -> List[Any]:
        return [
            self._config["last_reload"],
            self._event_status.num_existing_events,
            self._virtual_memory_size(),
        ]

    def _virtual_memory_size(self):
        parts = open('/proc/self/stat').read().split()
        return int(parts[22])  # in Bytes

    def _add_replication_status(self) -> List[Any]:
        if is_replication_slave(self._config):
            return [
                self._slave_status["mode"],
                self._slave_status["last_sync"],
                self._slave_status["success"],
            ]
        return ["master", 0.0, False]

    def _add_event_limit_status(self) -> List[Any]:
        return [
            self._config["event_limit"]["by_host"]["limit"],
            self._config["event_limit"]["by_rule"]["limit"],
            self._config["event_limit"]["overall"]["limit"],
            self.get_hosts_with_active_event_limit(),
            self.get_rules_with_active_event_limit(),
            self.is_overall_event_limit_active(),
        ]

    def create_pipe(self):
        path = self.settings.paths.event_pipe.value
        try:
            if not path.is_fifo():
                path.unlink()
        except Exception:
            pass

        if not path.exists():
            os.mkfifo(str(path))

        # We want to be able to receive events from all users on the local system
        path.chmod(0o666)  # nosec

        self._logger.info("Created FIFO '%s' for receiving events" % path)

    def open_syslog(self):
        endpoint = self.settings.options.syslog_udp
        try:
            if isinstance(endpoint, FileDescriptor):
                self._syslog = socket.fromfd(endpoint.value, socket.AF_INET, socket.SOCK_DGRAM)
                os.close(endpoint.value)
                self._logger.info("Opened builtin syslog server on inherited filedescriptor %d" %
                                  endpoint.value)
            if isinstance(endpoint, PortNumber):
                self._syslog = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._syslog.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._syslog.bind(("0.0.0.0", endpoint.value))
                self._logger.info("Opened builtin syslog server on UDP port %d" % endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin syslog server: %s" % e)

    def open_syslog_tcp(self):
        endpoint = self.settings.options.syslog_tcp
        try:
            if isinstance(endpoint, FileDescriptor):
                self._syslog_tcp = socket.fromfd(endpoint.value, socket.AF_INET, socket.SOCK_STREAM)
                self._syslog_tcp.listen(20)
                os.close(endpoint.value)
                self._logger.info(
                    "Opened builtin syslog-tcp server on inherited filedescriptor %d" %
                    endpoint.value)
            if isinstance(endpoint, PortNumber):
                self._syslog_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._syslog_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._syslog_tcp.bind(("0.0.0.0", endpoint.value))
                self._syslog_tcp.listen(20)
                self._logger.info("Opened builtin syslog-tcp server on TCP port %d" %
                                  endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin syslog-tcp server: %s" % e)

    def open_snmptrap(self):
        endpoint = self.settings.options.snmptrap_udp
        try:
            if isinstance(endpoint, FileDescriptor):
                self._snmptrap = socket.fromfd(endpoint.value, socket.AF_INET, socket.SOCK_DGRAM)
                os.close(endpoint.value)
                self._logger.info("Opened builtin snmptrap server on inherited filedescriptor %d" %
                                  endpoint.value)
            if isinstance(endpoint, PortNumber):
                self._snmptrap = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._snmptrap.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._snmptrap.bind(("0.0.0.0", endpoint.value))
                self._logger.info("Opened builtin snmptrap server on UDP port %d" % endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin snmptrap server: %s" % e)

    def open_eventsocket(self):
        path = self.settings.paths.event_socket.value
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._eventsocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._eventsocket.bind(str(path))
        path.chmod(0o664)
        self._eventsocket.listen(self._config['eventsocket_queue_len'])
        self._logger.info("Opened UNIX socket '%s' for receiving events" % path)

    def open_pipe(self):
        # Beware: we must open the pipe also for writing. Otherwise
        # we will see EOF forever after one writer has finished and
        # select() will trigger even if there is no data. A good article
        # about this is here:
        # http://www.outflux.net/blog/archives/2008/03/09/using-select-on-a-fifo/
        return os.open(str(self.settings.paths.event_pipe.value), os.O_RDWR | os.O_NONBLOCK)

    def handle_snmptrap(self, trap, ipaddress):
        self.process_event(self._event_creator.create_event_from_trap(trap, ipaddress))

    def serve(self) -> None:
        pipe_fragment = b''
        pipe = self.open_pipe()
        listen_list = [pipe]

        # Wait for incoming syslog packets via UDP
        if self._syslog is not None:
            listen_list.append(self._syslog.fileno())

        # Wait for new connections for events via TCP socket
        if self._syslog_tcp is not None:
            listen_list.append(self._syslog_tcp)

        # Wait for new connections for events via unix socket
        if self._eventsocket:
            listen_list.append(self._eventsocket)

        # Wait for incomding SNMP traps
        if self._snmptrap is not None:
            listen_list.append(self._snmptrap.fileno())

        # Keep list of client connections via UNIX socket and
        # read data that is not yet processed. Map from
        # fd to (fileobject, data)
        client_sockets: Dict[int, Tuple[socket.socket, Any, bytes]] = {}
        select_timeout = 1
        while not self._terminate_event.is_set():
            try:
                readable = select.select(listen_list + list(client_sockets.keys()), [], [],
                                         select_timeout)[0]
            except select.error as e:
                if e.args[0] != errno.EINTR:
                    raise
                continue
            data: Optional[bytes] = None

            # Accept new connection on event unix socket
            if self._eventsocket in readable:
                client_socket, address = self._eventsocket.accept()

                client_sockets[client_socket.fileno()] = (client_socket, address, b"")

            # Same for the TCP syslog socket
            if self._syslog_tcp and self._syslog_tcp in readable:
                client_socket, address = self._syslog_tcp.accept()

                client_sockets[client_socket.fileno()] = (client_socket, address, b"")

            # Read data from existing event unix socket connections
            # NOTE: We modify client_socket in the loop, so we need to copy below!
            for fd, (cs, address, previous_data) in list(client_sockets.items()):
                if fd in readable:
                    # Receive next part of data
                    try:
                        new_data = cs.recv(4096)
                    except Exception:
                        new_data = b""
                        address = None

                    # Put together with incomplete messages from last time
                    data = previous_data + new_data

                    # Do we have incomplete data? (if the socket has been
                    # closed then we consider the pending message always
                    # as complete, even if there was no trailing \n)
                    if new_data and not data.endswith(b"\n"):  # keep fragment
                        # Do we have any complete messages?
                        if b'\n' in data:
                            complete, rest = data.rsplit(b"\n", 1)
                            self.process_raw_lines(complete + b"\n", address)
                        else:
                            rest = data  # keep for next time

                    # Only complete messages
                    else:
                        if data:
                            self.process_raw_lines(data, address)
                        rest = b""

                    # Connection still open?
                    if new_data:
                        client_sockets[fd] = (cs, address, rest)
                    else:
                        cs.close()
                        del client_sockets[fd]

            # Read data from pipe
            if pipe in readable:
                try:
                    data = os.read(pipe, 4096)
                    if data:
                        # Prepend previous beginning of message to read data
                        data = pipe_fragment + data
                        pipe_fragment = b""

                        # Last message still incomplete?
                        if data[-1:] != b'\n':
                            if b'\n' in data:  # at least one complete message contained
                                messages, pipe_fragment = data.rsplit(b'\n', 1)
                                self.process_raw_lines(messages + b'\n')  # got lost in split
                            else:
                                pipe_fragment = data  # keep beginning of message, wait for \n
                        else:
                            self.process_raw_lines(data)
                    else:  # EOF
                        os.close(pipe)
                        pipe = self.open_pipe()
                        listen_list[0] = pipe
                        # Pending fragments from previos reads that are not terminated
                        # by a \n are ignored.
                        if pipe_fragment:
                            self._logger.warning("Ignoring incomplete message '%r' from pipe" %
                                                 pipe_fragment)
                            pipe_fragment = b""
                except Exception:
                    pass

            # Read events from builtin syslog server
            if self._syslog is not None and self._syslog.fileno() in readable:
                self.process_raw_lines(*self._syslog.recvfrom(4096))

            # Read events from builtin snmptrap server
            if self._snmptrap is not None and self._snmptrap.fileno() in readable:
                try:
                    message, sender_address = self._snmptrap.recvfrom(65535)
                    self.process_raw_data(
                        lambda: self._snmp_trap_engine.process_snmptrap(message, sender_address))
                except Exception:
                    self._logger.exception(
                        'Exception handling a SNMP trap from "%s". Skipping this one' %
                        sender_address[0])

            try:
                # process the first spool file we get
                spool_file = next(self.settings.paths.spool_dir.value.glob('[!.]*'))
                self.process_raw_lines(spool_file.read_bytes())
                spool_file.unlink()
                select_timeout = 0  # enable fast processing to process further files
            except StopIteration:
                select_timeout = 1  # restore default select timeout

    # Processes incoming data, just a wrapper between the real data and the
    # handler function to record some statistics etc.
    def process_raw_data(self, handler):
        self._perfcounters.count("messages")
        before = time.time()
        # In replication slave mode (when not took over), ignore all events
        if not is_replication_slave(self._config) or self._slave_status["mode"] != "sync":
            handler()
        elif self.settings.options.debug:
            self._logger.info("Replication: we are in slave mode, ignoring event")
        elapsed = time.time() - before
        self._perfcounters.count_time("processing", elapsed)

    # Takes several lines of messages, handles encoding and processes them separated
    def process_raw_lines(self, data: bytes, address: Optional[Any] = None) -> None:
        lines = data.splitlines()
        for line_bytes in lines:
            line = scrub_and_decode(line_bytes.rstrip())
            if line:
                try:

                    def handler(line=line):
                        self.process_line(line, address)

                    self.process_raw_data(handler)
                except Exception as e:
                    self._logger.exception('Exception handling a log line (skipping this one): %s' %
                                           e)

    def do_housekeeping(self) -> None:
        with self._event_status.lock:
            with self._lock_configuration:
                self.hk_handle_event_timeouts()
                self.hk_check_expected_messages()
                self.hk_cleanup_downtime_events()
        self._history.housekeeping()

    # For all events that have been created in a host downtime check the host
    # whether or not it is still in downtime. In case the downtime has ended
    # archive the events that have been created in a downtime.
    def hk_cleanup_downtime_events(self) -> None:
        host_downtimes: Dict[str, bool] = {}

        for event in self._event_status.events():
            if not event["host_in_downtime"]:
                continue  # only care about events created in downtime

            try:
                in_downtime = host_downtimes[event["core_host"]]
            except KeyError:
                in_downtime = self._is_host_in_downtime(event)
                host_downtimes[event["core_host"]] = in_downtime

            if in_downtime:
                continue  # (still) in downtime, don't delete any event

            self._logger.log(VERBOSE, "Remove event %d (created in downtime, host left downtime)",
                             event["id"])
            self._event_status.remove_event(event)

    def hk_handle_event_timeouts(self) -> None:
        # 1. Automatically delete all events that are in state "counting"
        #    and have not reached the required number of hits and whose
        #    time is elapsed.
        # 2. Automatically delete all events that are in state "open"
        #    and whose livetime is elapsed.
        events_to_delete = []
        events = self._event_status.events()
        now = time.time()
        for nr, event in enumerate(events):
            rule = self._rule_by_id.get(event["rule_id"])

            if event["phase"] == "counting":
                # Event belongs to a rule that does not longer exist? It
                # will never reach its count. Better delete it.
                if not rule:
                    self._logger.info("Deleting orphaned event %d created by obsolete rule %s" %
                                      (event["id"], event["rule_id"]))
                    event["phase"] = "closed"
                    self._history.add(event, "ORPHANED")
                    events_to_delete.append(nr)

                elif "count" not in rule and "expect" not in rule:
                    self._logger.info("Count-based event %d belonging to rule %s: rule does not "
                                      "count/expect anymore. Deleting event." %
                                      (event["id"], event["rule_id"]))
                    event["phase"] = "closed"
                    self._history.add(event, "NOCOUNT")
                    events_to_delete.append(nr)

                # handle counting
                elif "count" in rule:
                    count = rule["count"]
                    if count.get("algorithm") in ["tokenbucket", "dynabucket"]:
                        last_token = event.get("last_token", event["first"])
                        secs_per_token = count["period"] / float(count["count"])
                        if count["algorithm"] == "dynabucket":  # get fewer tokens if count is lower
                            if event["count"] <= 1:
                                secs_per_token = count["period"]
                            else:
                                secs_per_token *= (float(count["count"]) / float(event["count"]))
                        elapsed_secs = now - last_token
                        new_tokens = int(elapsed_secs / secs_per_token)
                        if new_tokens:
                            if self.settings.options.debug:
                                self._logger.info(
                                    "Rule %s/%s, event %d: got %d new tokens" %
                                    (rule["pack"], rule["id"], event["id"], new_tokens))
                            event["count"] = max(0, event["count"] - new_tokens)
                            event[
                                "last_token"] = last_token + new_tokens * secs_per_token  # not now! would be unfair
                            if event["count"] == 0:
                                self._logger.info(
                                    "Rule %s/%s, event %d: again without allowed rate, dropping event"
                                    % (rule["pack"], rule["id"], event["id"]))
                                event["phase"] = "closed"
                                self._history.add(event, "COUNTFAILED")
                                events_to_delete.append(nr)

                    else:  # algorithm 'interval'
                        if event["first"] + count["period"] <= now:  # End of period reached
                            self._logger.info(
                                "Rule %s/%s: reached only %d out of %d events within %d seconds. "
                                "Resetting to zero." % (rule["pack"], rule["id"], event["count"],
                                                        count["count"], count["period"]))
                            event["phase"] = "closed"
                            self._history.add(event, "COUNTFAILED")
                            events_to_delete.append(nr)

            # Handle delayed actions
            elif event["phase"] == "delayed":
                delay_until = event.get("delay_until", 0)  # should always be present
                if now >= delay_until:
                    self._logger.info("Delayed event %d of rule %s is now activated." %
                                      (event["id"], event["rule_id"]))
                    event["phase"] = "open"
                    self._history.add(event, "DELAYOVER")
                    if rule:
                        event_has_opened(self._history, self.settings, self._config, self._logger,
                                         self.host_config, self._event_columns, rule, event)
                        if rule.get("autodelete"):
                            event["phase"] = "closed"
                            self._history.add(event, "AUTODELETE")
                            events_to_delete.append(nr)

                    else:
                        self._logger.info("Cannot do rule action: rule %s not present anymore." %
                                          event["rule_id"])

            # Handle events with a limited lifetime
            elif "live_until" in event:
                if now >= event["live_until"]:
                    allowed_phases = event.get("live_until_phases", ["open"])
                    if event["phase"] in allowed_phases:
                        event["phase"] = "closed"
                        events_to_delete.append(nr)
                        self._logger.info(
                            "Livetime of event %d (rule %s) exceeded. Deleting event." %
                            (event["id"], event["rule_id"]))
                        self._history.add(event, "EXPIRED")

        # Do delayed deletion now (was delayed in order to keep list indices OK)
        for nr in events_to_delete[::-1]:
            self._event_status.remove_event(events[nr])

    def hk_check_expected_messages(self) -> None:
        now = time.time()
        # "Expecting"-rules are rules that require one or several
        # occurrances of a message within a defined time period.
        # Whenever one period of time has elapsed, we need to check
        # how many messages have been seen for that rule. If these
        # are too few, we open an event.
        # We need to handle to cases:
        # 1. An event for such a rule already exists and is
        #    in the state "counting" -> this can only be the case if
        #    more than one occurrance is required.
        # 2. No event at all exists.
        #    in that case.
        for rule in self._rules:
            if "expect" in rule:

                if not self._rule_matcher.event_rule_matches_site(rule, event=None):
                    continue

                # Interval is either a number of seconds, or pair of a number of seconds
                # (e.g. 86400, meaning one day) and a timezone offset relative to UTC in hours.
                interval = rule["expect"]["interval"]
                expected_count = rule["expect"]["count"]

                interval_start = self._event_status.interval_start(rule["id"], interval)
                if interval_start >= now:
                    continue

                next_interval_start = self._event_status.next_interval_start(
                    interval, interval_start)
                if next_interval_start > now:
                    continue

                # Interval has been elapsed. Now comes the truth: do we have enough
                # rule matches?

                # First do not forget to switch to next interval
                self._event_status.start_next_interval(rule["id"], interval)

                # First look for case 1: rule that already have at least one hit
                # and this events in the state "counting" exist.
                events_to_delete = []
                events = self._event_status.events()
                for nr, event in enumerate(events):
                    if event["rule_id"] == rule["id"] and event["phase"] == "counting":
                        # time has elapsed. Now lets see if we have reached
                        # the neccessary count:
                        if event["count"] < expected_count:  # no -> trigger alarm
                            self._handle_absent_event(rule, event["count"], expected_count,
                                                      event["last"])
                        else:  # yes -> everything is fine. Just log.
                            self._logger.info(
                                "Rule %s/%s has reached %d occurrances (%d required). "
                                "Starting next period." %
                                (rule["pack"], rule["id"], event["count"], expected_count))
                            self._history.add(event, "COUNTREACHED")
                        # Counting event is no longer needed.
                        events_to_delete.append(nr)
                        break

                # Ou ou, no event found at all.
                else:
                    self._handle_absent_event(rule, 0, expected_count, interval_start)

                for nr in events_to_delete[::-1]:
                    self._event_status.remove_event(events[nr])

    def _handle_absent_event(self, rule, event_count, expected_count, interval_start):
        now = time.time()
        if event_count:
            text = "Expected message arrived only %d out of %d times since %s" % \
                   (event_count, expected_count, time.strftime("%F %T", time.localtime(interval_start)))
        else:
            text = "Expected message did not arrive since %s" % \
                   time.strftime("%F %T", time.localtime(interval_start))

        # If there is already an incidence about this absent message, we can merge and
        # not create a new event. There is a setting for this.
        merge_event = None

        reset_ack = True
        merge = rule["expect"].get("merge", "open")

        # Changed "acked" to ("acked", bool) with 1.6.0p20
        if isinstance(merge, tuple):
            merge, reset_ack = merge

        if merge != "never":
            for event in self._event_status.events():
                if event["rule_id"] == rule["id"] and \
                        (event["phase"] == "open" or
                         (event["phase"] == "ack" and merge == "acked")):
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
            self.rewrite_event(rule, merge_event, {}, set_first=False)
            self._history.add(merge_event, "COUNTFAILED")
        else:
            # Create artifical event from scratch. Make sure that all important
            # fields are defined.
            event = {
                "rule_id": rule["id"],
                "text": text,
                "phase": "open",
                "count": 1,
                "time": now,
                "first": now,
                "last": now,
                "comment": "",
                "host": "",
                "ipaddress": "",
                "application": "",
                "pid": 0,
                "priority": 3,
                "facility": 1,  # user
                "match_groups": (),
                "match_groups_syslog_application": (),
                "core_host": "",
                "host_in_downtime": False,
            }
            self._add_rule_contact_groups_to_event(rule, event)
            self.rewrite_event(rule, event, {})
            self._event_status.new_event(event)
            self._history.add(event, "COUNTFAILED")
            event_has_opened(self._history, self.settings, self._config, self._logger,
                             self.host_config, self._event_columns, rule, event)
            if rule.get("autodelete"):
                event["phase"] = "closed"
                self._history.add(event, "AUTODELETE")
                self._event_status.remove_event(event)

    def reload_configuration(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._snmp_trap_engine = SNMPTrapEngine(self.settings, self._config,
                                                self._logger.getChild("snmp"), self.handle_snmptrap)
        self.compile_rules(self._config["rules"], self._config["rule_packs"])
        self.host_config = HostConfig(self._logger)

    # Precompile regular expressions and similar stuff. Also convert legacy
    # "rules" parameter into new "rule_packs" parameter
    def compile_rules(self, legacy_rules, rule_packs):
        self._rules = []
        self._rule_by_id = {}
        # Speedup-Hash for rule execution
        self._rule_hash: Dict[int, Dict[int, Any]] = {}
        count_disabled = 0
        count_rules = 0
        count_unspecific = 0

        # Loop through all rule packages and with through their rules
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
                        for key in [
                                "match", "match_ok", "match_host", "match_application",
                                "cancel_application"
                        ]:
                            if key in rule:
                                value = self._compile_matching_value(key, rule[key])
                                if value is None:
                                    del rule[key]
                                    continue

                                rule[key] = value

                        if 'state' in rule and isinstance(rule['state'], tuple) \
                           and rule['state'][0] == 'text_pattern':
                            for key in ['2', '1', '0']:
                                if key in rule['state'][1]:
                                    value = self._compile_matching_value(
                                        'state', rule['state'][1][key])
                                    if value is None:
                                        del rule['state'][1][key]
                                    else:
                                        rule['state'][1][key] = value

                    except Exception as e:
                        if self.settings.options.debug:
                            raise
                        rule["disabled"] = True
                        count_disabled += 1
                        self._logger.exception(
                            "Ignoring rule '%s/%s' because of an invalid regex (%s)." %
                            (rule["pack"], rule["id"], e))

                    if self._config["rule_optimizer"]:
                        self.hash_rule(rule)
                        if "match_facility" not in rule \
                                and "match_priority" not in rule \
                                and "cancel_priority" not in rule \
                                and "cancel_application" not in rule:
                            count_unspecific += 1

        self._logger.info("Compiled %d active rules (ignoring %d disabled rules)" %
                          (count_rules, count_disabled))
        if self._config["rule_optimizer"]:
            self._logger.info(
                "Rule hash: %d rules - %d hashed, %d unspecific" %
                (len(self._rules), len(self._rules) - count_unspecific, count_unspecific))
            for facility in list(range(23)) + [31]:
                if facility in self._rule_hash:
                    stats = []
                    for prio, entries in self._rule_hash[facility].items():
                        stats.append("%s(%d)" % (SyslogPriority(prio), len(entries)))
                    self._logger.info(" %-12s: %s" % (SyslogFacility(facility), " ".join(stats)))

    @staticmethod
    def _compile_matching_value(key, val):
        value = val.strip()
        # Remove leading .* from regex. This is redundant and
        # dramatically destroys performance when doing an infix search.
        if key in ["match", "match_ok"]:
            while value.startswith(".*") and not value.startswith(".*?"):
                value = value[2:]

        if not value:
            return None

        if cmk.utils.regex.is_regex(value):
            return re.compile(value, re.IGNORECASE)
        return val.lower()

    def hash_rule(self, rule):
        # Construct rule hash for faster execution.
        facility = rule.get("match_facility")
        if facility and not rule.get("invert_matching"):
            self.hash_rule_facility(rule, facility)
        else:
            for facility in range(32):  # all syslog facilities
                self.hash_rule_facility(rule, facility)

    def hash_rule_facility(self, rule, facility):
        needed_prios = [False] * 8
        for key in ["match_priority", "cancel_priority"]:
            if key in rule:
                prio_from, prio_to = rule[key]
                # Beware: from > to!
                for p in range(prio_to, prio_from + 1):
                    needed_prios[p] = True
            elif key == "match_priority":  # all priorities match
                needed_prios = [True] * 8  # needed to check this rule for all event priorities
            elif "match_ok" in rule:  # a cancelling rule where all priorities cancel
                needed_prios = [True] * 8  # needed to check this rule for all event priorities

        if rule.get("invert_matching"):
            needed_prios = [True] * 8

        prio_hash = self._rule_hash.setdefault(facility, {})
        for prio, need in enumerate(needed_prios):
            if need:
                prio_hash.setdefault(prio, []).append(rule)

    def output_hash_stats(self):
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
            self._logger.info("  %s/%s - %d (%.2f%%)" %
                              (SyslogFacility(facility), SyslogPriority(priority), count,
                               (100.0 * count / float(total_count))))

    def process_line(self, line, address):
        line = line.rstrip()
        if self._config["debug_rules"]:
            if address:
                self._logger.info(u"Processing message from %r: '%s'" % (address, line))
            else:
                self._logger.info(u"Processing message '%s'" % line)

        event = self._event_creator.create_event_from_line(line, address)
        self.process_event(event)

    def process_event(self, event: Event) -> None:
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
                self._logger.exception('  Exception during matching:\n%s' % e)
                result = False

            if result:  # A tuple with (True/False, {match_info}).. O.o
                self._perfcounters.count("rule_hits")
                cancelling, match_groups = result

                if self._config["debug_rules"]:
                    self._logger.info("  matching groups:\n%s" % pprint.pformat(match_groups))

                self._event_status.count_rule_match(rule["id"])
                if self._config["log_rulehits"]:
                    self._logger.info("Rule '%s/%s' hit by message %s/%s - '%s'." %
                                      (rule["pack"], rule["id"], SyslogFacility(event["facility"]),
                                       SyslogPriority(event["priority"]), event["text"]))

                if rule.get("drop"):
                    if rule["drop"] == "skip_pack":
                        skip_pack = rule["pack"]
                        if self._config["debug_rules"]:
                            self._logger.info("  skipping this rule pack (%s)" % skip_pack)
                        continue
                    self._perfcounters.count("drops")
                    return

                if cancelling:
                    self._event_status.cancel_events(self, self._event_columns, event, match_groups,
                                                     rule)
                    return

                # Remember the rule id that this event originated from
                event["rule_id"] = rule["id"]

                # Attach optional contact group information for visibility
                # and eventually for notifications
                self._add_rule_contact_groups_to_event(rule, event)

                # Store groups from matching this event. In order to make
                # persistence easier, we do not safe them as list but join
                # them on ASCII-1.
                event["match_groups"] = match_groups.get("match_groups_message", ())
                event["match_groups_syslog_application"] = match_groups.get(
                    "match_groups_syslog_application", ())
                self.rewrite_event(rule, event, match_groups)

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
                    existing_event = \
                        self._event_status.count_event(self, event, rule, count)
                    if existing_event:
                        if "delay" in rule:
                            if self._config["debug_rules"]:
                                self._logger.info("Event opening will be delayed for %d seconds" %
                                                  rule["delay"])
                            existing_event["delay_until"] = time.time() + rule["delay"]
                            existing_event["phase"] = "delayed"
                        else:
                            event_has_opened(self._history, self.settings, self._config,
                                             self._logger, self.host_config, self._event_columns,
                                             rule, existing_event)

                        self._history.add(existing_event, "COUNTREACHED")

                        if "delay" not in rule and rule.get("autodelete"):
                            existing_event["phase"] = "closed"
                            self._history.add(existing_event, "AUTODELETE")
                            with self._event_status.lock:
                                self._event_status.remove_event(existing_event)
                elif "expect" in rule:
                    self._event_status.count_expected_event(self, event)
                else:
                    if "delay" in rule:
                        if self._config["debug_rules"]:
                            self._logger.info("Event opening will be delayed for %d seconds" %
                                              rule["delay"])
                        event["delay_until"] = time.time() + rule["delay"]
                        event["phase"] = "delayed"
                    else:
                        event["phase"] = "open"

                    if self.new_event_respecting_limits(event):
                        if event["phase"] == "open":
                            event_has_opened(self._history, self.settings, self._config,
                                             self._logger, self.host_config, self._event_columns,
                                             rule, event)
                            if rule.get("autodelete"):
                                event["phase"] = "closed"
                                self._history.add(event, "AUTODELETE")
                                with self._event_status.lock:
                                    self._event_status.remove_event(event)
                return

        # End of loop over rules.
        if self._config["archive_orphans"]:
            self._event_status.archive_event(event)

    def _add_rule_contact_groups_to_event(self, rule, event):
        if rule.get("contact_groups") is None:
            event.update({
                "contact_groups": None,
                "contact_groups_notify": False,
                "contact_groups_precedence": "host",
            })
        else:
            event.update({
                "contact_groups": rule["contact_groups"]["groups"],
                "contact_groups_notify": rule["contact_groups"]["notify"],
                "contact_groups_precedence": rule["contact_groups"]["precedence"],
            })

    def add_core_host_to_event(self, event: Event) -> None:
        name = self.host_config.get_canonical_name(event["host"])
        event["core_host"] = "" if name is None else name

    def _add_core_host_to_new_event(self, event):
        self.add_core_host_to_event(event)

        # Add some state dependent information (like host is in downtime etc.)
        event["host_in_downtime"] = self._is_host_in_downtime(event)

    def _is_host_in_downtime(self, event: Event) -> bool:
        if not event["core_host"]:
            return False  # Found no host in core: Not in downtime!

        query = ("GET hosts\n"
                 "Columns: scheduled_downtime_depth\n"
                 "Filter: host_name = %s\n" % (event["core_host"]))

        try:
            return livestatus.LocalConnection().query_value(query) >= 1

        except livestatus.MKLivestatusNotFoundError:
            return False

        except Exception:
            if cmk.utils.debug.enabled():
                raise
            return False

    # Checks if an event matches a rule. Returns either False (no match)
    # or a pair of matchtype, groups, where matchtype is False for a
    # normal match and True for a cancelling match and the groups is a tuple
    # if matched regex groups in either text (normal) or match_ok (cancelling)
    # match.
    def event_rule_matches(self, rule, event):
        self._perfcounters.count("rule_tries")
        with self._lock_configuration:
            result = self._rule_matcher.event_rule_matches_non_inverted(rule, event)
            if rule.get("invert_matching"):
                if result is False:
                    result = False, {}
                    if self._config["debug_rules"]:
                        self._logger.info(
                            "  Rule would not match, but due to inverted matching does.")
                else:
                    result = False
                    if self._config["debug_rules"]:
                        self._logger.info(
                            "  Rule would match, but due to inverted matching does not.")

            return result

    # Rewrite texts and compute other fields in the event
    def rewrite_event(self, rule, event, groups, set_first=True):
        if rule["state"] == -1:
            prio = event["priority"]
            if prio >= 5:
                event["state"] = 0
            elif prio < 4:
                event["state"] = 2
            else:
                event["state"] = 1
        elif isinstance(rule["state"], tuple) and rule["state"][0] == "text_pattern":
            for key in ['2', '1', '0', '3']:
                if key in rule["state"][1]:
                    match_groups = match(rule["state"][1][key], event["text"], complete=False)
                    if match_groups is not False:
                        event["state"] = int(key)
                        break
                elif key == '3':  # No rule matched!
                    event["state"] = 3
        else:
            event["state"] = rule["state"]

        if ("sl" not in event) or (rule["sl"]["precedence"] == "rule"):
            event["sl"] = rule["sl"]["value"]
        if set_first:
            event["first"] = event["time"]
        event["last"] = event["time"]
        if "set_comment" in rule:
            event["comment"] = replace_groups(rule["set_comment"], event["text"], groups)
        if "set_text" in rule:
            event["text"] = replace_groups(rule["set_text"], event["text"], groups)
        if "set_host" in rule:
            event["orig_host"] = event["host"]
            event["host"] = replace_groups(rule["set_host"], event["host"], groups)
        if "set_application" in rule:
            event["application"] = replace_groups(rule["set_application"], event["application"],
                                                  groups)
        if "set_contact" in rule and "contact" not in event:
            event["contact"] = replace_groups(rule["set_contact"], event.get("contact", ""), groups)

    # Translate a hostname if this is configured. We are
    # *really* sorry: this code snipped is copied from modules/check_mk_base.py.
    # There is still no common library. Please keep this in sync with the
    # original code
    def translate_hostname(self, backedhost):
        translation = self._config["hostname_translation"]

        # Here comes the original code from modules/check_mk_base.py
        if translation:
            # 1. Case conversion
            caseconf = translation.get("case")
            if caseconf == "upper":
                backedhost = backedhost.upper()
            elif caseconf == "lower":
                backedhost = backedhost.lower()

            # 2. Drop domain part (not applied to IP addresses!)
            if translation.get("drop_domain") and backedhost:
                # only apply if first part does not convert successfully into an int
                firstpart = backedhost.split(".", 1)[0]
                try:
                    int(firstpart)
                except Exception:
                    backedhost = firstpart

            # 3. Regular expression conversion
            if "regex" in translation:
                for regex, subst in translation["regex"]:
                    if not regex.endswith('$'):
                        regex += '$'
                    rcomp = cmk.utils.regex.regex(regex)
                    mo = rcomp.match(backedhost)
                    if mo:
                        backedhost = subst
                        for nr, text in enumerate(mo.groups()):
                            backedhost = backedhost.replace("\\%d" % (nr + 1), text)
                        break

            # 4. Explicity mapping
            for from_host, to_host in translation.get("mapping", []):
                if from_host == backedhost:
                    backedhost = to_host
                    break

        return backedhost

    def do_translate_hostname(self, event: Event) -> None:
        try:
            event["host"] = self.translate_hostname(event["host"])
        except Exception as e:
            if self._config["debug_rules"]:
                self._logger.exception('Unable to parse host "%s" (%s)' % (event.get("host"), e))
            event["host"] = ""

    def log_message(self, event: Event) -> None:
        try:
            with get_logfile(self._config, self.settings.paths.messages_dir.value,
                             self._message_period).open(mode='ab') as f:
                f.write(
                    ensure_binary("%s %s %s%s: %s\n" % (
                        time.strftime("%b %d %H:%M:%S", time.localtime(event["time"])),  #
                        event["host"],
                        event["application"],
                        event["pid"] and ("[%s]" % event["pid"]) or "",
                        event["text"])))
        except Exception:
            if self.settings.options.debug:
                raise
            # Better silently ignore errors. We could have run out of
            # diskspace and make things worse by logging that we could
            # not log.

    def get_hosts_with_active_event_limit(self) -> List[str]:
        hosts = []
        for (hostname, core_host), count in self._event_status.num_existing_events_by_host.items():
            host_config = self.host_config.get_config_for_host(core_host)
            if count >= self._get_host_event_limit(host_config)[0]:
                hosts.append(hostname)
        return hosts

    def get_rules_with_active_event_limit(self) -> List[str]:
        rule_ids = []
        for rule_id, num_events in self._event_status.num_existing_events_by_rule.items():
            if rule_id is None:
                continue  # Ignore rule unrelated overflow events. They have no rule id associated.
            if num_events >= self._get_rule_event_limit(rule_id)[0]:
                rule_ids.append(rule_id)
        return rule_ids

    def is_overall_event_limit_active(self) -> bool:
        return self._event_status.num_existing_events \
            >= self._config["event_limit"]["overall"]["limit"]

    # protected by self._event_status.lock
    def new_event_respecting_limits(self, event: Event) -> bool:
        self._logger.log(VERBOSE, "Checking limit for message from %s (rule '%s')",
                         (event["host"], event["rule_id"]))

        host_config = self.host_config.get_config_for_host(event["core_host"])
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
    # stop_overflow_notify Stop creating new events, create overflow event, notfy
    # delete_oldest        Delete oldest event, create new event
    # protected by self._event_status.lock

    # Returns False if the event has been created and actions should be
    # performed on that event
    def _handle_event_limit(self, ty: str, event: Event, host_config: Optional[HostInfo]) -> bool:
        assert ty in ["overall", "by_rule", "by_host"]

        num_already_open = self._event_status.get_num_existing_events_by(ty, event)

        limit, action = self._get_event_limit(ty, event, host_config)
        self._logger.log(VERBOSE, "  Type: %s, already open events: %d, Limit: %d", ty,
                         num_already_open, limit)

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

        self._logger.info("  The %s limit has been reached" % ty)

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
    def _get_event_limit(self, ty: str, event: Event,
                         host_config: Optional[HostInfo]) -> Tuple[int, str]:
        if ty == "overall":
            return self._get_overall_event_limit()
        if ty == "by_rule":
            return self._get_rule_event_limit(event["rule_id"])
        if ty == "by_host":
            return self._get_host_event_limit(host_config)
        raise NotImplementedError()

    def _get_overall_event_limit(self) -> Tuple[int, str]:
        return (self._config["event_limit"]["overall"]["limit"],
                self._config["event_limit"]["overall"]["action"])

    def _get_rule_event_limit(self, rule_id) -> Tuple[int, str]:
        """Prefer the rule individual limit for by_rule limit (in case there is some)"""
        rule_limit = self._rule_by_id.get(rule_id, {}).get("event_limit")
        if rule_limit:
            return rule_limit["limit"], rule_limit["action"]

        return (self._config["event_limit"]["by_rule"]["limit"],
                self._config["event_limit"]["by_rule"]["action"])

    def _get_host_event_limit(self, host_config: Optional[HostInfo]) -> Tuple[int, str]:
        """Prefer the host individual limit for by_host limit (in case there is some)"""
        host_limit = (None if host_config is None else host_config.get("custom_variables",
                                                                       {}).get("EC_EVENT_LIMIT"))
        if host_limit:
            limit, action = host_limit.split(":", 1)
            return int(limit), action

        return (self._config["event_limit"]["by_host"]["limit"],
                self._config["event_limit"]["by_host"]["action"])

    def _create_overflow_event(self, ty, event, limit):
        now = time.time()
        new_event = {
            "rule_id": None,
            "phase": "open",
            "count": 1,
            "time": now,
            "first": now,
            "last": now,
            "comment": "",
            "host": "",
            "ipaddress": "",
            "application": "Event Console",
            "pid": 0,
            "priority": 2,  # crit
            "facility": 1,  # user
            "match_groups": (),
            "match_groups_syslog_application": (),
            "state": 2,  # crit
            "sl": event["sl"],
            "core_host": "",
            "host_in_downtime": False,
        }
        self._add_rule_contact_groups_to_event({}, new_event)

        if ty == "overall":
            new_event["text"] = ("The overall event limit of %d open events has been reached. Not "
                                 "opening any additional event until open events have been "
                                 "archived." % limit)

        elif ty == "by_host":
            new_event.update({
                "host": event["host"],
                "ipaddress": event["ipaddress"],
                "text": ("The host event limit of %d open events has been reached for host \"%s\". "
                         "Not opening any additional event for this host until open events have "
                         "been archived." % (limit, event["host"]))
            })

            # Lookup the monitoring core hosts and add the core host
            # name to the event when one can be matched
            self._add_core_host_to_new_event(new_event)

        elif ty == "by_rule":
            new_event.update({
                "rule_id": event["rule_id"],
                "contact_groups": event["contact_groups"],
                "contact_groups_notify": event.get("contact_groups_notify", False),
                "contact_groups_precedence": event.get("contact_groups_precedence", "host"),
                "text": ("The rule event limit of %d open events has been reached for rule \"%s\". "
                         "Not opening any additional event for this rule until open events have "
                         "been archived." % (limit, event["rule_id"]))
            })

        else:
            raise NotImplementedError()

        return new_event


def current_utcoffset_seconds() -> int:
    utcoffset = datetime.datetime.now(dateutil.tz.tzlocal()).utcoffset()
    # utcoffset is an 'aware' datetime object (we explicitly passed a timezone above),
    # but the typing is too weak to express this. As a consequnce, we must help mypy.
    assert utcoffset is not None
    return round(utcoffset.total_seconds())


# Sophos firewalls use a braindead non-standard timestamp format with funny separators and without a timezone.
def fix_broken_sophos_timestamp(timestamp: str) -> str:
    # Step 1: Fix separator between date and time
    timestamp = timestamp.replace('-', 'T', 1)
    # Step 2: Fix separators between date parts
    timestamp = timestamp.replace(':', '-', 2)
    # Step 3: Add explicit offset for local time
    offset = current_utcoffset_seconds()
    hours, minutes = divmod(abs(offset) // 60, 60)
    return timestamp + f'{"-" if offset < 0 else "+"}{hours:02}{minutes:02}'


class EventCreator:
    def __init__(self, logger: Logger, config: Dict[str, Any]) -> None:
        super().__init__()
        self._logger = logger
        self._config = config

    def create_event_from_line(self, line: str, address: str) -> Event:
        event = {
            # address is either None or a tuple of (ipaddress, port)
            "ipaddress": address and address[0] or "",
            "core_host": "",
            "host_in_downtime": False,
        }
        try:
            # Variant 1: plain syslog message without priority/facility:
            # May 26 13:45:01 Klapprechner CRON[8046]:  message....

            # Variant 1a: plain syslog message without priority/facility/host:
            # May 26 13:45:01 Klapprechner CRON[8046]:  message....

            # Variant 2: syslog message including facility (RFC 3164)
            # <78>May 26 13:45:01 Klapprechner CRON[8046]:  message....

            # Variant 3: local Nagios alert posted by mkevent -n
            # <154>@1341847712;5;Contact Info; MyHost My Service: CRIT - This che

            # Variant 4: remote Nagios alert posted by mkevent -n -> syslog
            # <154>Jul  9 17:28:32 Klapprechner @1341847712;5;Contact Info;  MyHost My Service: CRIT - This che

            # Variant 5: syslog message
            #  Timestamp is RFC3339 with additional restrictions:
            #  - The "T" and "Z" characters in this syntax MUST be upper case.
            #  - Usage of the "T" character is REQUIRED.
            #  - Leap seconds MUST NOT be used.
            # <166>2013-04-05T13:49:31.685Z esx Vpxa: message....

            # Variant 6: syslog message without date / host:
            # <5>SYSTEM_INFO: [WLAN-1] Triggering Background Scan

            # Variant 7: logwatch.ec event forwarding
            # <78>@1341847712 Klapprechner /var/log/syslog: message....

            # Variant 7a: Event simulation
            # <%PRI%>@%TIMESTAMP%;%SL% %HOSTNAME% %syslogtag%: %msg%

            # Variant 8: syslog message from sophos firewall
            # <84>2015:03:25-12:02:06 gw pluto[7122]: listening for IKE messages

            # Variant 9: syslog message (RFC 5424)
            # <134>1 2016-06-02T12:49:05.181+02:00 chrissw7 ChrisApp - TestID - coming from  java code

            # Variant 10:
            # 2016 May 26 15:41:47 IST XYZ Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up
            # year month day hh:mm:ss timezone HOSTNAME KeyAgent:

            # FIXME: Would be better to parse the syslog messages in another way:
            # Split the message by the first ":", then split the syslog header part
            # and detect which information are present. Take a look at the syslog RFCs
            # for details.

            # Variant 2,3,4,5,6,7,7a,8
            if line.startswith('<'):
                i = line.find('>')
                prio = int(line[1:i])
                line = line[i + 1:]
                event["facility"] = prio >> 3
                event["priority"] = prio & 7

            # Variant 1,1a
            else:
                event["facility"] = 1  # user
                event["priority"] = 5  # notice

            # Variant 7 and 7a
            if line[0] == '@' and line[11] in [' ', ';'] and line.split(' ', 1)[0].count(';') <= 1:
                details, event['host'], line = line.split(' ', 2)
                detail_tokens = details.split(';')
                timestamp = detail_tokens[0]
                if len(detail_tokens) > 1:
                    event["sl"] = int(detail_tokens[1])
                event['time'] = float(timestamp[1:])
                event.update(self._parse_syslog_info(line))

            # Variant 3
            elif line.startswith("@"):
                event.update(self._parse_monitoring_info(line))

            # Variant 5
            elif len(line) > 24 and line[10] == 'T':
                timestamp, event['host'], rest = line.split(' ', 2)
                event['time'] = dateutil.parser.isoparse(timestamp).timestamp()
                event.update(self._parse_syslog_info(rest))

            # Variant 9
            elif len(line) > 24 and line[12] == "T":
                event.update(self._parse_rfc5424_syslog_info(line))

            # Variant 8
            elif line[10] == '-' and line[19] == ' ':
                timestamp, event['host'], rest = line.split(' ', 2)
                timestamp = fix_broken_sophos_timestamp(timestamp)
                event['time'] = dateutil.parser.isoparse(timestamp).timestamp()
                event.update(self._parse_syslog_info(rest))

            # Variant 6
            elif len(line.split(': ', 1)[0].split(' ')) == 1:
                event.update(self._parse_syslog_info(line))
                # There is no datetime information in the message, use current time
                event['time'] = time.time()
                # There is no host information, use the provided address
                event["host"] = address[0] if address and isinstance(address, tuple) else ""

            # Variant 10
            elif line[4] == " " and line[:4].isdigit():
                time_part = line[:20]  # ignoring tz info
                event["host"], application, line = line[25:].split(" ", 2)
                event["application"] = application.rstrip(":")
                event["pid"] = 0
                event["text"] = line
                event['time'] = time.mktime(time.strptime(time_part, '%Y %b %d %H:%M:%S'))

            # Variant 1,1a,2,4
            else:
                month_name, day, timeofday, rest = line.split(None, 3)

                # Special handling for variant 1a. Detect whether or not host
                # is a hostname or syslog tag
                host, tmp_rest = rest.split(None, 1)
                if host.endswith(":"):
                    # There is no host information sent, use the source address as "host"
                    host = address[0]
                else:
                    # Use the extracted host and continue with the remaining message text
                    rest = tmp_rest

                event["host"] = host

                # Variant 4
                if rest.startswith("@"):
                    # TODO: host gets overwritten, strange... Is this OK?
                    event.update(self._parse_monitoring_info(rest))

                # Variant 1, 2
                else:
                    event.update(self._parse_syslog_info(rest))

                    month = EventServer.month_names[month_name]
                    iday = int(day)

                    # Nasty: the year is not contained in the message. We cannot simply
                    # assume that the message if from the current year.
                    lt = time.localtime()
                    if lt.tm_mon < 6 < month:  # Assume that message is from last year
                        year = lt.tm_year - 1
                    else:
                        year = lt.tm_year  # Assume the current year

                    hours, minutes, seconds = map(int, timeofday.split(":"))

                    # A further problem here: we do not now whether the message is in DST or not
                    event["time"] = time.mktime(
                        (year, month, iday, hours, minutes, seconds, 0, 0, lt.tm_isdst))

            # The event simulator ships the simulated original IP address in the
            # hostname field, separated with a pipe, e.g. "myhost|1.2.3.4"
            if isinstance(event["host"], str) and "|" in event["host"]:
                event["host"], event["ipaddress"] = event["host"].split("|", 1)

        except Exception as e:
            if self._config["debug_rules"]:
                self._logger.exception('Got non-syslog message "%s" (%s)' % (line, e))
            event = {
                "facility": 1,
                "priority": 0,
                "text": line,
                "host": "",
                "ipaddress": address and address[0] or "",
                "application": "",
                "pid": 0,
                "time": time.time(),
                "core_host": "",
                "host_in_downtime": False,
            }

        if self._config["debug_rules"]:
            self._logger.info('Parsed message:\n' + ("".join(
                [" %-15s %s\n" % (k + ":", v) for (k, v) in sorted(event.items())])).rstrip())

        return event

    def _parse_rfc5424_syslog_info(self, line: str) -> Dict[str, Any]:
        event: Dict[str, Any] = {}

        (_unused_version, timestamp, hostname, app_name, procid, _unused_msgid,
         rest) = line.split(" ", 6)

        event['time'] = dateutil.parser.isoparse(timestamp).timestamp()
        event["host"] = "" if hostname == "-" else hostname
        event["application"] = "" if app_name == "-" else app_name
        event["pid"] = 0 if procid == "-" else procid

        if rest[0] == "[":
            # has stuctured data
            structured_data, message = rest[1:].split("] ", 1)
        elif rest.startswith("- "):
            # has no stuctured data
            structured_data, message = rest.split(" ", 1)
        else:
            raise Exception("Invalid RFC 5424 syslog message")

        if structured_data != "-":
            event["text"] = "[%s] %s" % (structured_data, message)
        else:
            event["text"] = message

        return event

    def _parse_syslog_info(self, content: str) -> Dict[str, Any]:
        # Replaced ":" by ": " here to make tags with ":" possible. This
        # is needed to process logs generated by windows agent logfiles
        # like "c://test.log".
        parts = content.split(": ", 1)
        if len(parts) == 1:  # no TAG at all
            application = ""
            pid = 0
            text = content.strip()
        elif "[" in parts[0]:  # TAG followed by pid
            application, pid_str = parts[0].split("[", 1)
            pid = int(pid_str.rstrip("]"))
            text = parts[1].strip()
        else:  # TAG not followed by pid
            application = parts[0]
            pid = 0
            text = parts[1].strip()
        return {
            "application": application,
            "pid": pid,
            "text": text,
        }

    def _parse_monitoring_info(self, line: str) -> Dict[str, Any]:
        event: Dict[str, Any] = {}
        # line starts with '@'
        if line[11] == ';':
            timestamp_str, sl, contact, rest = line[1:].split(';', 3)
            host, rest = rest.split(None, 1)
            if len(sl):
                event["sl"] = int(sl)
            if len(contact):
                event["contact"] = contact
        else:
            timestamp_str, host, rest = line[1:].split(None, 2)

        event["time"] = float(int(timestamp_str))
        service, message = rest.split(": ", 1)
        event["application"] = service
        event["text"] = message.strip()
        event["host"] = host
        event["pid"] = 0
        return event

    def create_event_from_trap(self, trap, ipaddress):
        # use the trap-oid as application
        application = u''
        for index, (oid, _unused_val) in enumerate(trap):
            if oid in ['1.3.6.1.6.3.1.1.4.1.0', 'SNMPv2-MIB::snmpTrapOID.0']:
                application = scrub_and_decode(trap.pop(index)[1])
                break

        # once we got here we have a real parsed trap which we convert to an event now
        safe_ipaddress = scrub_and_decode(ipaddress)
        text = scrub_and_decode(', '.join(['%s: %s' % (item[0], str(item[1])) for item in trap]))

        event = {
            'time': time.time(),
            'host': safe_ipaddress,
            'ipaddress': safe_ipaddress,
            'priority': 5,  # notice
            'facility': 31,  # not used by syslog -> we use this for all traps
            'application': application,
            'text': text,
            'core_host': '',
            'host_in_downtime': False,
        }

        return event


class RuleMatcher:
    def __init__(self, logger: Logger, config: Dict[str, Any]) -> None:
        super().__init__()
        self._logger = logger
        self._config = config
        self._time_periods = TimePeriods(logger)

    @property
    def _debug_rules(self):
        return self._config["debug_rules"]

    def event_rule_matches_non_inverted(self, rule, event):
        if self._debug_rules:
            self._logger.info("Trying rule %s/%s..." % (rule["pack"], rule["id"]))
            self._logger.info("  Text:   %s" % event["text"])
            self._logger.info("  Syslog: %d.%d" % (event["facility"], event["priority"]))
            self._logger.info("  Host:   %s" % event["host"])

        # Generic conditions without positive/canceling matches
        if not self.event_rule_matches_generic(rule, event):
            return False

        # Determine syslog priority
        match_priority: Dict[str, bool] = {}
        if not self.event_rule_determine_match_priority(rule, event, match_priority):
            # Abort on negative outcome, neither positive nor negative
            return False

        # Determine and cleanup match_groups
        match_groups: Dict[str, Union[bool, Tuple[str, ...]]] = {}
        if not self.event_rule_determine_match_groups(rule, event, match_groups):
            # Abort on negative outcome, neither positive nor negative
            return False

        return self._check_match_outcome(rule, match_groups, match_priority)

    def _check_match_outcome(
            self, rule: Dict[str, Any], match_groups: Dict[str, Any],
            match_priority: Dict[str, Any]) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """Decide or not a event is created, canceled or nothing is done"""

        # Check canceling-event
        has_canceling_condition = bool(
            [x for x in ["match_ok", "cancel_application", "cancel_priority"] if x in rule])
        if has_canceling_condition:
            if ("match_ok" not in rule or match_groups.get("match_groups_message_ok", False) is not False) and\
               ("cancel_application" not in rule or
                match_groups.get("match_groups_syslog_application_ok", False) is not False) and\
               ("cancel_priority" not in rule or match_priority["has_canceling_match"] is True):
                if self._debug_rules:
                    self._logger.info("  found canceling event")
                return True, match_groups

        # Check create-event
        if match_groups["match_groups_message"] is not False and\
            match_groups.get("match_groups_syslog_application", ()) is not False and\
            match_priority["has_match"] is True:
            if self._debug_rules:
                self._logger.info("  found new event")
            return False, match_groups

        # Looks like there was no match, output some additonal info
        # Reasons preventing create-event
        if self._debug_rules:
            if match_groups["match_groups_message"] is False:
                self._logger.info("  did not create event, because of wrong message")
            if "match_application" in rule and match_groups[
                    "match_groups_syslog_application"] is False:
                self._logger.info("  did not create event, because of wrong syslog application")
            if "match_priority" in rule and match_priority["has_match"] is False:
                self._logger.info("  did not create event, because of wrong syslog priority")

            if has_canceling_condition:
                # Reasons preventing cancel-event
                if "match_ok" in rule and match_groups.get("match_groups_message_ok",
                                                           False) is False:
                    self._logger.info("  did not cancel event, because of wrong message")
                if "cancel_application" in rule and \
                   match_groups.get("match_groups_syslog_application_ok", False) is False:
                    self._logger.info("  did not cancel event, because of wrong syslog application")
                if "cancel_priority" in rule and match_priority["has_canceling_match"] is False:
                    self._logger.info("  did not cancel event, because of wrong cancel priority")

        return False

    def event_rule_matches_generic(self, rule, event):
        generic_match_functions = [
            self.event_rule_matches_site,
            self.event_rule_matches_host,
            self.event_rule_matches_ip,
            self.event_rule_matches_facility,
            self.event_rule_matches_service_level,
            self.event_rule_matches_timeperiod,
        ]

        for match_function in generic_match_functions:
            if not match_function(rule, event):
                return False
        return True

    def event_rule_determine_match_priority(self, rule, event, match_priority):
        p = event["priority"]

        if "match_priority" in rule:
            prio_from, prio_to = sorted(rule["match_priority"])
            match_priority["has_match"] = prio_from <= p <= prio_to
        else:
            match_priority["has_match"] = True

        if "cancel_priority" in rule:
            cancel_from, cancel_to = sorted(rule["cancel_priority"])
            match_priority["has_canceling_match"] = cancel_from <= p <= cancel_to
        else:
            match_priority["has_canceling_match"] = False

        if match_priority["has_match"] is False and\
           match_priority["has_canceling_match"] is False:
            return False

        return True

    def event_rule_matches_site(self, rule, event):
        return "match_site" not in rule or cmk_version.omd_site() in rule["match_site"]

    def event_rule_matches_host(self, rule, event):
        if match(rule.get("match_host"), event["host"], complete=True) is False:
            if self._debug_rules:
                self._logger.info("  did not match because of wrong host '%s' (need '%s')" %
                                  (event["host"], format_pattern(rule.get("match_host"))))
            return False
        return True

    def event_rule_matches_ip(self, rule, event):
        if not match_ipv4_network(rule.get("match_ipaddress", "0.0.0.0/0"), event["ipaddress"]):
            if self._debug_rules:
                self._logger.info(
                    "  did not match because of wrong source IP address '%s' (need '%s')" %
                    (event["ipaddress"], rule.get("match_ipaddress")))
            return False
        return True

    def event_rule_matches_facility(self, rule, event):
        if "match_facility" in rule and event["facility"] != rule["match_facility"]:
            if self._debug_rules:
                self._logger.info("  did not match because of wrong syslog facility")
            return False
        return True

    def event_rule_matches_service_level(self, rule, event):
        if "match_sl" in rule:
            sl_from, sl_to = rule["match_sl"]
            if sl_from > sl_to:
                sl_to, sl_from = sl_from, sl_to
            p = event.get("sl", 0)
            if p < sl_from or p > sl_to:
                if self._debug_rules:
                    self._logger.info(
                        "  did not match because of wrong service level %d (need %d..%d)" %
                        (p, sl_from, sl_to),)
                return False
        return True

    def event_rule_matches_timeperiod(self, rule, event):
        if "match_timeperiod" in rule and not self._time_periods.check(rule["match_timeperiod"]):
            if self._debug_rules:
                self._logger.info("  did not match, because timeperiod %s is not active" %
                                  rule["match_timeperiod"])
            return False
        return True

    def event_rule_determine_match_groups(self, rule, event, match_groups):
        match_group_functions = [
            self.event_rule_matches_syslog_application,
            self.event_rule_matches_message,
        ]
        for match_function in match_group_functions:
            if not match_function(rule, event, match_groups):
                return False
        return True

    def event_rule_matches_syslog_application(self, rule, event, match_groups):
        if "match_application" not in rule and "cancel_application" not in rule:
            return True

        # Syslog application
        if "match_application" in rule:
            match_groups["match_groups_syslog_application"] = match(rule.get("match_application"),
                                                                    event["application"],
                                                                    complete=False)

        # Syslog application canceling, this option must be explictly set
        if "cancel_application" in rule:
            match_groups["match_groups_syslog_application_ok"] = match(
                rule.get("cancel_application"), event["application"], complete=False)

        # Detect impossible match
        if match_groups.get("match_groups_syslog_application", False) is False and\
           match_groups.get("match_groups_syslog_application_ok", False) is False:
            if self._debug_rules:
                self._logger.info("  did not match, syslog application does not match")
            return False

        return True

    def event_rule_matches_message(self, rule, event, match_groups):
        # Message matching, this condition is always active
        match_groups["match_groups_message"] = match(rule.get("match"),
                                                     event["text"],
                                                     complete=False)

        # Message canceling, this option must be explictly set
        if "match_ok" in rule:
            match_groups["match_groups_message_ok"] = match(rule.get("match_ok"),
                                                            event["text"],
                                                            complete=False)

        # Detect impossible match
        if match_groups["match_groups_message"] is False and\
           match_groups.get("match_groups_message_ok", False) is False:
            if self._debug_rules:
                self._logger.info("  did not match, message text does not match")
            return False

        return True


#.
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
    def __init__(self, status_server: 'StatusServer', sock: socket.socket, logger: Logger) -> None:
        super().__init__()
        self._status_server = status_server
        self._socket = sock
        self._logger = logger
        self._buffer = b""

    def _query(self, request: bytes) -> Query:
        return Query.make(self._status_server, request.decode("utf-8").splitlines(), self._logger)

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


#.
#   .--Status Tables-------------------------------------------------------.
#   |     ____  _        _               _____     _     _                 |
#   |    / ___|| |_ __ _| |_ _   _ ___  |_   _|_ _| |__ | | ___  ___       |
#   |    \___ \| __/ _` | __| | | / __|   | |/ _` | '_ \| |/ _ \/ __|      |
#   |     ___) | || (_| | |_| |_| \__ \   | | (_| | |_) | |  __/\__ \      |
#   |    |____/ \__\__,_|\__|\__,_|___/   |_|\__,_|_.__/|_|\___||___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Definitions of the tables available for status queries               |
#   '----------------------------------------------------------------------'
# If you need a new column here, then these are the places to change:
# bin/mkeventd:
# - add column to the end of StatusTableEvents.columns
# - add column to grepping_filters if it is a str column
# - deal with convert_history_line() (if not a str column)
# - make sure that the new column is filled at *every* place where
#   an event is being created:
#   * _create_event_from_trap()
#   * create_event_from_line()
#   * _handle_absent_event()
#   * _create_overflow_event()
# - When loading the status file add the possibly missing column to all
#   loaded events (load_status())
# - Maybe add matching/rewriting for the new column
# - write the actual code using the new column
# web:
# - Add column painter for the new column
# - Create a sorter
# - Create a filter
# - Add painter and filter to all views where appropriate
# - maybe add WATO code for matching rewriting
# - do not forget event_rule_matches() in web!
# - maybe add a field into the event simulator


class StatusTable:
    prefix: Optional[str] = None
    columns: List[Tuple[str, Any]] = []

    # Must return a enumerable type containing fully populated lists (rows) matching the
    # columns of the table
    @abc.abstractmethod
    def _enumerate(self, query: QueryGET) -> Iterable[List[Any]]:
        raise NotImplementedError()

    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger.getChild("status_table.%s" % self.prefix)
        self.column_defaults = dict(self.columns)
        self.column_names = [name for name, _def_val in self.columns]
        self.column_types = {name: type(def_val) for name, def_val in self.columns}
        self.column_indices = {name: index for index, name in enumerate(self.column_names)}

    def query(self, query: QueryGET) -> Iterable[List[Any]]:
        requested_column_indexes = query.requested_column_indexes()

        # Output the column headers
        # TODO: Add support for ColumnHeaders like in livestatus?
        yield query.requested_columns

        num_rows = 0
        for row in self._enumerate(query):
            if query.limit is not None and num_rows >= query.limit:
                break  # The maximum number of rows has been reached
            # Apply filters
            # TODO: History filtering is done in history load code. Check for improvements
            if query.table_name == "history" or query.filter_row(row):
                yield self._build_result_row(row, requested_column_indexes)
                num_rows += 1

    def _build_result_row(self, row: List[Any],
                          requested_column_indexes: List[Optional[int]]) -> List[Any]:
        return [
            (None if index is None else row[index])  #
            for index in requested_column_indexes
        ]


class StatusTableEvents(StatusTable):
    prefix = "event"
    columns = [
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

    def __init__(self, logger: Logger, event_status: 'EventStatus') -> None:
        super().__init__(logger)
        self._event_status = event_status

    def _enumerate(self, query: QueryGET) -> Iterable[List[Any]]:
        for event in self._event_status.get_events():
            # Optimize filters that are set by the check_mkevents active check. Since users
            # may have a lot of those checks running, it is a good idea to optimize this.
            if query.only_host and not filter_operator_in(event["host"], query.only_host):
                continue

            row = []
            for column_name in self.column_names:
                try:
                    row.append(event[column_name[6:]])
                except KeyError:
                    # The row does not have this value. Use the columns default value
                    row.append(self.column_defaults[column_name])

            yield row


class StatusTableHistory(StatusTable):
    prefix = "history"
    columns = [
        ("history_line", 0),  # Line number in event history file
        ("history_time", 0.0),
        ("history_what", ""),
        ("history_who", ""),
        ("history_addinfo", ""),
    ] + StatusTableEvents.columns

    def __init__(self, logger: Logger, history: History) -> None:
        super().__init__(logger)
        self._history = history

    def _enumerate(self, query: QueryGET) -> Iterable[List[Any]]:
        return self._history.get(query)


class StatusTableRules(StatusTable):
    prefix = "rule"
    columns = [
        ("rule_id", ""),
        ("rule_hits", 0),
    ]

    def __init__(self, logger: Logger, event_status: 'EventStatus') -> None:
        super().__init__(logger)
        self._event_status = event_status

    def _enumerate(self, query: QueryGET) -> Iterable[List[Any]]:
        return self._event_status.get_rule_stats()


class StatusTableStatus(StatusTable):
    prefix = "status"
    columns = EventServer.status_columns()

    def __init__(self, logger: Logger, event_server: EventServer) -> None:
        super().__init__(logger)
        self._event_server = event_server

    def _enumerate(self, query: QueryGET) -> Iterable[List[Any]]:
        return self._event_server.get_status()


#.
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
    def __init__(self, logger: Logger, settings: Settings, config: Dict[str, Any],
                 slave_status: Dict[str, Any], perfcounters: Perfcounters,
                 lock_configuration: ECLock, history: History, event_status: 'EventStatus',
                 event_server: EventServer, terminate_main_event: threading.Event) -> None:
        super().__init__(name="StatusServer",
                         logger=logger,
                         settings=settings,
                         config=config,
                         slave_status=slave_status,
                         profiling_enabled=settings.options.profile_status,
                         profile_file=settings.paths.status_server_profile.value)
        self._socket: Optional[socket.socket] = None
        self._tcp_socket: Optional[socket.socket] = None
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
        raise MKClientError("Invalid table: %s (allowed are: events, history, rules, status)" %
                            name)

    def open_unix_socket(self) -> None:
        path = self.settings.paths.unix_socket.value
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(path))
        # Make sure that socket is group writable
        path.chmod(0o664)
        self._socket.listen(self._config['socket_queue_len'])
        self._unix_socket_queue_len = self._config['socket_queue_len']  # detect changes in config

    def open_tcp_socket(self) -> None:
        if self._config["remote_status"]:
            try:
                self._tcp_port, self._tcp_allow_commands = self._config["remote_status"][:2]
                try:
                    self._tcp_access_list = self._config["remote_status"][2]
                except Exception:
                    self._tcp_access_list = None

                self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._tcp_socket.bind(("0.0.0.0", self._tcp_port))
                self._tcp_socket.listen(self._config['socket_queue_len'])
                self._logger.info("Going to listen for status queries on TCP port %d" %
                                  self._tcp_port)
            except Exception as e:
                if self.settings.options.debug:
                    raise
                self._logger.exception("Cannot listen on TCP socket port %d: %s" %
                                       (self._tcp_port, e))
        else:
            self._tcp_socket = None
            self._tcp_port = 0
            self._tcp_allow_commands = False
            self._tcp_access_list = None

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

    def reload_configuration(self, config):
        self._config = config
        self._reopen_sockets = True

    def serve(self) -> None:
        while not self._terminate_event.is_set():
            try:
                client_socket = None
                addr_info = None

                if self._reopen_sockets:
                    self.reopen_sockets()
                    self._reopen_sockets = False

                listen_list = [self._socket]
                if self._tcp_socket:
                    listen_list.append(self._tcp_socket)

                try:
                    readable = select.select(listen_list, [], [], 0.2)[0]
                except select.error as e:
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
                            self._logger.info("Handle status connection from %s:%d" % addr_info)
                        if self._tcp_access_list is not None and addr_info[0] not in \
                           self._tcp_access_list:
                            client_socket.close()
                            client_socket = None
                            self._logger.info(
                                "Denying access to status socket from %s (allowed is only %s)" %
                                (addr_info[0], ", ".join(self._tcp_access_list)))
                            continue
                    else:
                        allow_commands = True

                    self.handle_client(client_socket, allow_commands, addr_info and addr_info[0] or
                                       "")

                    duration = time.time() - before
                    self._logger.log(VERBOSE, "Answered request in %0.2f ms", duration * 1000)
                    self._perfcounters.count_time("request", duration)

            except Exception as e:
                msg = "Error handling client %s: %s" % (addr_info, e)
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

    def handle_client(self, client_socket: socket.socket, allow_commands: bool,
                      client_ip: str) -> Any:
        for query in Queries(self, client_socket, self._logger):
            self._logger.log(VERBOSE, "Client livestatus query: %r", query)

            with self._event_status.lock:
                if query.method == "GET":
                    if not isinstance(query, QueryGET):
                        raise NotImplementedError()  # make mypy happy
                    response: Optional[Iterable[List[Any]]] = self.table(
                        query.table_name).query(query)

                elif query.method == "REPLICATE":
                    response = self.handle_replicate(query.method_arg, client_ip)

                elif query.method == "COMMAND":
                    if not allow_commands:
                        raise MKClientError("Sorry. Commands are disallowed via TCP")
                    self.handle_command_request(query.method_arg)
                    response = None

                else:
                    raise NotImplementedError()

                try:
                    self._answer_query(client_socket, query, response)
                except socket.error as e:
                    if e.errno == errno.EPIPE:
                        pass
                    else:
                        raise

        client_socket.close()

    # Only GET queries have customizable output formats. COMMAND is always
    # a dictionay and COMMAND is always None and always output as "python"
    def _answer_query(self, client_socket: socket.socket, query: Query,
                      response: Optional[Iterable[List[Any]]]) -> None:
        if query.method != "GET":
            self._answer_query_python(client_socket, response)
            return
        if response is None:
            raise NotImplementedError()  # Make mypy happy

        if query.output_format == "plain":
            for row in response:
                client_socket.sendall(b"\t".join([quote_tab(c) for c in row]) + b"\n")

        elif query.output_format == "json":
            client_socket.sendall((json.dumps(list(response)) + "\n").encode("utf-8"))

        elif query.output_format == "python":
            self._answer_query_python(client_socket, list(response))

        else:
            raise NotImplementedError()

    def _answer_query_python(self, client_socket, response):
        client_socket.sendall((repr(response) + "\n").encode("utf-8"))

    # All commands are already locked with self._event_status.lock
    def handle_command_request(self, commandline: str) -> None:
        self._logger.info("Executing command: %s" % commandline)
        parts = commandline.split(";")
        command = parts[0]
        replication_allow_command(self._config, command, self._slave_status)
        arguments = parts[1:]
        if command == "DELETE":
            self.handle_command_delete(arguments)
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
            raise MKClientError("Unknown command %s" % command)

    def handle_command_delete(self, arguments: List[str]) -> None:
        if len(arguments) != 2:
            raise MKClientError("Wrong number of arguments for DELETE")
        event_ids, user = arguments
        for event_id in event_ids.split(","):
            self._event_status.delete_event(int(event_id), user)

    def handle_command_update(self, arguments: List[str]) -> None:
        event_id, user, acknowledged, comment, contact = arguments
        event = self._event_status.event(int(event_id))
        if not event:
            raise MKClientError("No event with id %s" % event_id)
        # Note the common practice: We validate parameters *before* doing any changes.
        if acknowledged:
            ack = int(acknowledged)
            if ack and event["phase"] not in ["open", "ack"]:
                raise MKClientError("You cannot acknowledge an event that is not open.")
            event["phase"] = "ack" if ack else "open"
        if comment:
            event["comment"] = comment
        if contact:
            event["contact"] = contact
        if user:
            event["owner"] = user
        self._history.add(event, "UPDATE", user)

    def handle_command_create(self, arguments: List[str]) -> None:
        # Would rather use process_raw_line(), but we are already
        # holding self._event_status.lock and it's sub functions are setting
        # self._event_status.lock too. The lock can not be allocated twice.
        # TODO: Change the lock type in future?
        # process_raw_lines("%s" % ";".join(arguments))
        with open(str(self.settings.paths.event_pipe.value), "wb") as pipe:
            pipe.write(("%s\n" % ";".join(arguments)).encode("utf-8"))

    def handle_command_changestate(self, arguments: List[str]) -> None:
        event_ids, user, newstate = arguments
        for event_id in event_ids.split(","):
            event = self._event_status.event(int(event_id))
            if not event:
                raise MKClientError("No event with id %s" % event_id)
            event["state"] = int(newstate)
            if user:
                event["owner"] = user
            self._history.add(event, "CHANGESTATE", user)

    def handle_command_reload(self) -> None:
        reload_configuration(self.settings, self._logger, self._lock_configuration, self._history,
                             self._event_status, self._event_server, self, self._slave_status)

    def handle_command_reopenlog(self) -> None:
        self._logger.info("Closing this logfile")
        log.open_log(str(self.settings.paths.log_file.value))
        self._logger.info("Opened new logfile")

    # Erase our current state and history!
    def handle_command_flush(self) -> None:
        self._history.flush()
        self._event_status.flush()
        self._event_status.save_status()
        if is_replication_slave(self._config):
            try:
                self.settings.paths.master_config_file.value.unlink()
                self.settings.paths.slave_status_file.value.unlink()
                update_slave_status(self._slave_status, self.settings, self._config)
            except Exception:
                pass
        self._logger.info("Flushed current status and historic events.")

    def handle_command_sync(self) -> None:
        self._event_status.save_status()

    def handle_command_resetcounters(self, arguments: List[str]) -> None:
        if arguments:
            self._logger.info("Resetting counters of rule " + arguments[0])
            self._event_status.reset_counters(arguments[0])
        else:
            self._logger.info("Resetting all rule counters")
            self._event_status.reset_counters(None)

    def handle_command_action(self, arguments):
        event_id, user, action_id = arguments
        event = self._event_status.event(int(event_id))
        if user:
            event["owner"] = user

        if action_id == "@NOTIFY":
            do_notify(self._event_server.host_config,
                      self._logger,
                      event,
                      user,
                      is_cancelling=False)
        else:
            with self._lock_configuration:
                if action_id not in self._config["action"]:
                    raise MKClientError(
                        "The action '%s' is not defined. After adding new commands please "
                        "make sure that you activate the changes in the Event Console." % action_id)
                action = self._config["action"][action_id]
            do_event_action(self._history, self.settings, self._config, self._logger,
                            self._event_columns, action, event, user)

    def handle_command_switchmode(self, arguments):
        new_mode = arguments[0]
        if not is_replication_slave(self._config):
            raise MKClientError("Cannot switch replication mode: this is not a replication slave.")
        if new_mode not in ["sync", "takeover"]:
            raise MKClientError("Invalid target mode '%s': allowed are only 'sync' and 'takeover'" %
                                new_mode)
        self._slave_status["mode"] = new_mode
        save_slave_status(self.settings, self._slave_status)
        self._logger.info("Switched replication mode to '%s' by external command." % new_mode)

    def handle_replicate(self, argument, client_ip):
        # Last time our slave got a config update
        try:
            last_update = int(argument)
            if self.settings.options.debug:
                self._logger.info("Replication: sync request from %s, last update %d seconds ago" %
                                  (client_ip, time.time() - last_update))

        except Exception:
            raise MKClientError("Invalid arguments to command REPLICATE")
        return replication_send(self._config, self._lock_configuration, self._event_status,
                                last_update)


#.
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


def run_eventd(terminate_main_event: Any, settings: Settings, config: Dict[str, Any],
               lock_configuration: ECLock, history: History, perfcounters: Perfcounters,
               event_status: 'EventStatus', event_server: EventServer, status_server: StatusServer,
               slave_status: Dict[str, Any], logger: Logger) -> None:
    status_server.start()
    event_server.start()
    now = time.time()
    next_housekeeping = now + config["housekeeping_interval"]
    next_retention = now + config["retention_interval"]
    next_statistics = now + config["statistics_interval"]
    next_replication = 0  # force immediate replication after restart

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
                time.sleep(min(time_left, 60))

                now = time.time()
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
                    replication_pull(settings, config, lock_configuration, perfcounters,
                                     event_status, event_server, slave_status, logger)
                    next_replication = now + config["replication"]["interval"]
            except MKSignalException as e:
                raise e
            except Exception as e:
                logger.exception("Exception in main thread:\n%s" % e)
                if settings.options.debug:
                    raise
                time.sleep(1)
        except MKSignalException as e:
            if e._signum == 1:
                logger.info("Received SIGHUP - going to reload configuration")
                reload_configuration(settings, logger, lock_configuration, history, event_status,
                                     event_server, status_server, slave_status)
            else:
                logger.info("Signalled to death by signal %d" % e._signum)
                terminate(terminate_main_event, event_server, status_server)

    # Now wait for termination of the server threads
    event_server.join()
    status_server.join()


#.
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
    def __init__(self, settings: Settings, config: Dict[str, Any], perfcounters: Perfcounters,
                 history: History, logger: Logger) -> None:
        self.settings = settings
        self._config = config
        self._perfcounters = perfcounters
        self.lock = threading.Lock()
        self._history = history
        self._logger = logger
        self.flush()

    def reload_configuration(self, config: Dict[str, Any]) -> None:
        self._config = config

    def flush(self) -> None:
        # TODO: Improve types!
        self._events: List[Any] = []
        self._next_event_id = 1
        self._rule_stats: Dict[str, int] = {}
        # needed for expecting rules
        self._interval_starts: Dict[str, int] = {}
        self._initialize_event_limit_status()

        # TODO: might introduce some performance counters, like:
        # - number of received messages
        # - number of rule hits
        # - number of rule misses

    def events(self) -> List[Any]:
        # TODO: Improve type!
        return self._events

    def event(self, eid):
        for event in self._events:
            if event["id"] == eid:
                return event

    # Return beginning of current expectation interval. For new rules
    # we start with the next interval in future.
    def interval_start(self, rule_id, interval):
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

    def next_interval_start(self, interval, previous_start):
        if isinstance(interval, tuple):
            length, offset = interval
            offset *= 3600
        else:
            length = interval
            offset = 0

        previous_start -= offset  # take into account timezone offset
        full_parts = divmod(previous_start, length)[0]
        next_start = (full_parts + 1) * length
        next_start += offset
        return next_start

    def start_next_interval(self, rule_id, interval):
        current_start = self.interval_start(rule_id, interval)
        next_start = self.next_interval_start(interval, current_start)
        self._interval_starts[rule_id] = next_start
        self._logger.debug("Rule %s: next interval starts %s (i.e. now + %.2f sec)" %
                           (rule_id, next_start, time.time() - next_start))

    def pack_status(self):
        return {
            "next_event_id": self._next_event_id,
            "events": self._events,
            "rule_stats": self._rule_stats,
            "interval_starts": self._interval_starts,
        }

    def unpack_status(self, status):
        self._next_event_id = status["next_event_id"]
        self._events = status["events"]
        self._rule_stats = status["rule_stats"]
        self._interval_starts = status["interval_starts"]

    def save_status(self):
        now = time.time()
        status = self.pack_status()
        path = self.settings.paths.status_file.value
        path_new = path.parent / (path.name + '.new')
        # Believe it or not: cPickle is more than two times slower than repr()
        with path_new.open(mode='wb') as f:
            f.write((repr(status) + "\n").encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        path_new.rename(path)
        elapsed = time.time() - now
        self._logger.log(VERBOSE, "Saved event state to %s in %.3fms.", path, elapsed * 1000)

    def reset_counters(self, rule_id):
        if rule_id:
            if rule_id in self._rule_stats:
                del self._rule_stats[rule_id]
        else:
            self._rule_stats = {}
        self.save_status()

    def load_status(self, event_server):
        path = self.settings.paths.status_file.value
        if path.exists():
            try:
                status = ast.literal_eval(path.read_text(encoding="utf-8"))
                self._next_event_id = status["next_event_id"]
                self._events = status["events"]
                self._rule_stats = status["rule_stats"]
                self._interval_starts = status.get("interval_starts", {})
                self._logger.info("Loaded event state from %s." % path)
            except Exception as e:
                self._logger.exception("Error loading event state from %s: %s" % (path, e))
                raise

        # Add new columns and fix broken events
        for event in self._events:
            event.setdefault("ipaddress", "")
            event.setdefault("host", "")
            event.setdefault("application", "")
            event.setdefault("pid", 0)

            if "core_host" not in event:
                event_server.add_core_host_to_event(event)
                event["host_in_downtime"] = False

        # core_host is needed to initialize the status
        self._initialize_event_limit_status()

    # Called on Event Console initialization from status file to initialize
    # the current event limit state -> Sets internal counters which are
    # updated during runtime.
    def _initialize_event_limit_status(self):
        self.num_existing_events = len(self._events)

        self.num_existing_events_by_host: Dict[Tuple[str, HostName], int] = {}
        self.num_existing_events_by_rule = {}
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

    def remove_event(self, event: Event) -> None:
        try:
            self._events.remove(event)
            self._count_event_remove(event)
        except ValueError:
            self._logger.exception("Cannot remove event %d: not present" % event["id"])

    # protected by self.lock
    def _remove_event_by_nr(self, index: int) -> None:
        event = self._events.pop(index)
        self._count_event_remove(event)

    # protected by self.lock
    def remove_oldest_event(self, ty, event):
        if ty == "overall":
            self._logger.log(VERBOSE, "  Removing oldest event")
            self._remove_event_by_nr(0)
        elif ty == "by_rule":
            self._logger.log(VERBOSE, "  Removing oldest event of rule \"%s\"", event["rule_id"])
            self._remove_oldest_event_of_rule(event["rule_id"])
        elif ty == "by_host":
            self._logger.log(VERBOSE, "  Removing oldest event of host \"%s\"", event["host"])
            self._remove_oldest_event_of_host(event["host"])

    # protected by self.lock
    def _remove_oldest_event_of_rule(self, rule_id) -> None:
        for event in self._events:
            if event["rule_id"] == rule_id:
                self.remove_event(event)
                return

    # protected by self.lock
    def _remove_oldest_event_of_host(self, hostname: str) -> None:
        for event in self._events:
            if event["host"] == hostname:
                self.remove_event(event)
                return

    # protected by self.lock
    def get_num_existing_events_by(self, ty: str, event: Event) -> int:
        if ty == "overall":
            return self.num_existing_events
        if ty == "by_rule":
            return self.num_existing_events_by_rule.get(event["rule_id"], 0)
        if ty == "by_host":
            return self.num_existing_events_by_host.get((event["host"], event["core_host"]), 0)
        raise NotImplementedError()

    # Cancel all events the belong to a certain rule id and are
    # of the same "breed" as a new event.
    def cancel_events(self, event_server, event_columns, new_event, match_groups, rule):
        with self.lock:
            to_delete = []
            for nr, event in enumerate(self._events):
                if event["rule_id"] == rule["id"]:
                    if self.cancelling_match(match_groups, new_event, event, rule):
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
                            event["text"] = replace_groups(rule["set_text"], event["text"],
                                                           match_groups)
                        event["time"] = new_event["time"]
                        event["last"] = new_event["time"]
                        event["priority"] = new_event["priority"]
                        self._history.add(event, "CANCELLED")
                        actions = rule.get("cancel_actions", [])
                        if actions:
                            if previous_phase != "open" \
                               and rule.get("cancel_action_phases", "always") == "open":
                                self._logger.info(
                                    "Do not execute cancelling actions, event %s's phase "
                                    "is not 'open' but '%s'" % (event["id"], previous_phase))
                            else:
                                do_event_actions(self._history,
                                                 self.settings,
                                                 self._config,
                                                 self._logger,
                                                 event_server.host_config,
                                                 event_columns,
                                                 actions,
                                                 event,
                                                 is_cancelling=True)

                        to_delete.append(nr)

            for nr in to_delete[::-1]:
                self._remove_event_by_nr(nr)

    def cancelling_match(self, match_groups, new_event, event, rule):
        debug = self._config["debug_rules"]

        # The match_groups of the canceling match only contain the *_ok match groups
        # Since the rewrite definitions are based on the positive match, we need to
        # create some missing keys. O.o
        for key in match_groups.keys():
            if key.endswith("_ok"):
                match_groups[key[:-3]] = match_groups[key]

        # Note: before we compare host and application we need to
        # apply the rewrite rules to the event. Because if in the previous
        # the hostname was rewritten, it wouldn't match anymore here.
        host = new_event["host"]
        if "set_host" in rule:
            host = replace_groups(rule["set_host"], host, match_groups)

        if event["host"] != host:
            if debug:
                self._logger.info("Do not cancel event %d: host is not the same (%s != %s)" %
                                  (event["id"], event["host"], host))
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
                        "Do not cancel event %d: application is not the same (%s != %s)" %
                        (event["id"], event["application"], application))
                return False

        if event["facility"] != new_event["facility"]:
            if debug:
                self._logger.info(
                    "Do not cancel event %d: syslog facility is not the same (%d != %d)" %
                    (event["id"], event["facility"], new_event["facility"]))

        # Make sure, that the matching groups are the same. If the OK match
        # has less groups, we do not care. If it has more groups, then we
        # do not care either. We just compare the common "prefix".
        for nr, (prev_group, cur_group) in enumerate(
                zip(event["match_groups"], match_groups.get("match_groups_message_ok", ()))):
            if prev_group != cur_group:
                if debug:
                    self._logger.info("Do not cancel event %d: match group number "
                                      "%d does not match (%s != %s)" %
                                      (event["id"], nr + 1, prev_group, cur_group))
                return False

        # Note: Duplicated code right above
        # Make sure, that the syslog_application matching groups are the same. If the OK match
        # has less groups, we do not care. If it has more groups, then we
        # do not care either. We just compare the common "prefix".
        for nr, (prev_group, cur_group) in enumerate(
                zip(event.get("match_groups_syslog_application", ()),
                    match_groups.get("match_groups_syslog_application_ok", ()))):
            if prev_group != cur_group:
                if debug:
                    self._logger.info(
                        "Do not cancel event %d: syslog application match group number "
                        "%d does not match (%s != %s)" %
                        (event["id"], nr + 1, prev_group, cur_group))
                return False

        return True

    def count_rule_match(self, rule_id):
        with self.lock:
            self._rule_stats.setdefault(rule_id, 0)
            self._rule_stats[rule_id] += 1

    def count_event_up(self, found, event):
        # Update event with new information from new occurrance,
        # but preserve certain attributes from the original (first)
        # event.
        preserve = {
            "count": found.get("count", 1) + 1,
            "first": found["first"],
        }
        # When event is already active then do not change
        # comment or contact information anymore
        if found["phase"] == "open":
            if "comment" in found:
                preserve["comment"] = found["comment"]
            if "contact" in found:
                preserve["contact"] = found["contact"]
        found.update(event)
        found.update(preserve)

    def count_expected_event(self, event_server, event):
        for ev in self._events:
            if ev["rule_id"] == event["rule_id"] and ev["phase"] == "counting":
                self.count_event_up(ev, event)
                return

        # None found, create one
        event["count"] = 1
        event["phase"] = "counting"
        event_server.new_event_respecting_limits(event)

    def count_event(self, event_server, event, rule, count):
        # Find previous occurrance of this event and acount for
        # one new occurrance. In case of negated count (expecting rules)
        # we do never modify events that are already in the state "open"
        # since the event has been created because the count was too
        # low in the specified period of time.
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

                if count.get("count_duration"
                            ) is not None and ev["first"] + count["count_duration"] < event["time"]:
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
        return False  # do not do event action

    # locked with self.lock
    def delete_event(self, event_id, user):
        for nr, event in enumerate(self._events):
            if event["id"] == event_id:
                event["phase"] = "closed"
                if user:
                    event["owner"] = user
                self._history.add(event, "DELETE", user)
                self._remove_event_by_nr(nr)
                return
        raise MKClientError("No event with id %s" % event_id)

    def get_events(self):
        return self._events

    def get_rule_stats(self):
        return sorted(self._rule_stats.items(), key=lambda x: x[0])


#.
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


def is_replication_slave(config: Dict[str, Any]) -> bool:
    repl_settings = config["replication"]
    return repl_settings and not repl_settings.get("disabled")


def replication_allow_command(config: Dict[str, Any], command: str,
                              slave_status: Dict[str, Any]) -> None:
    if is_replication_slave(config) and slave_status["mode"] == "sync" \
       and command in ["DELETE", "UPDATE", "CHANGESTATE", "ACTION"]:
        raise MKClientError("This command is not allowed on a replication slave "
                            "while it is in sync mode.")


def replication_send(config: Dict[str, Any], lock_configuration: ECLock, event_status: EventStatus,
                     last_update: int) -> Dict[str, Any]:
    response = {}
    with lock_configuration:
        response["status"] = event_status.pack_status()
        if last_update < config["last_reload"]:
            response["rules"] = config[
                "rules"]  # Remove one bright day, where legacy rules are not needed anymore
            response["rule_packs"] = config["rule_packs"]
            response["actions"] = config["actions"]
        return response


def replication_pull(settings: Settings, config: Dict[str, Any], lock_configuration: ECLock,
                     perfcounters: Perfcounters, event_status: EventStatus,
                     event_server: EventServer, slave_status: Dict[str,
                                                                   Any], logger: Logger) -> None:
    # We distinguish two modes:
    # 1. slave mode: just pull the current state from the master.
    #    if the master is not reachable then decide whether to
    #    switch to takeover mode.
    # 2. takeover mode: if automatic fallback is enabled and the
    #    time frame for that has not yet ellapsed, then try to
    #    pull the current state from the master. If that is successful
    #    then switch back to slave mode. If not automatic fallback
    #    is enabled then simply do nothing.
    now = time.time()
    repl_settings = config["replication"]
    mode = slave_status["mode"]
    need_sync = mode == "sync" or (
        mode == "takeover" and "fallback" in repl_settings and
        (slave_status["last_master_down"] is None or
         now - repl_settings["fallback"] < slave_status["last_master_down"]))

    if need_sync:
        with event_status.lock:
            with lock_configuration:

                try:
                    new_state = get_state_from_master(config, slave_status)
                    replication_update_state(settings, config, event_status, event_server,
                                             new_state)
                    if repl_settings.get("logging"):
                        logger.info("Successfully synchronized with master")
                    slave_status["last_sync"] = now
                    slave_status["success"] = True

                    # Fall back to slave mode after successful sync
                    # (time frame has already been checked)
                    if mode == "takeover":
                        if slave_status["last_master_down"] is None:
                            logger.info("Replication: master reachable for the first time, "
                                        "switching back to slave mode")
                            slave_status["mode"] = "sync"
                        else:
                            logger.info("Replication: master reachable again after %d seconds, "
                                        "switching back to sync mode" %
                                        (now - slave_status["last_master_down"]))
                            slave_status["mode"] = "sync"
                    slave_status["last_master_down"] = None

                except Exception as e:
                    logger.warning("Replication: cannot sync with master: %s" % e)
                    slave_status["success"] = False
                    if slave_status["last_master_down"] is None:
                        slave_status["last_master_down"] = now

                    # Takeover
                    if "takeover" in repl_settings and mode != "takeover":
                        if not slave_status["last_sync"]:
                            if repl_settings.get("logging"):
                                logger.error(
                                    "Replication: no takeover since master was never reached.")
                        else:
                            offline = now - slave_status["last_sync"]
                            if offline < repl_settings["takeover"]:
                                if repl_settings.get("logging"):
                                    logger.warning(
                                        "Replication: no takeover yet, still %d seconds to wait" %
                                        (repl_settings["takeover"] - offline))
                            else:
                                logger.info(
                                    "Replication: master not reached for %d seconds, taking over!" %
                                    offline)
                                slave_status["mode"] = "takeover"

                save_slave_status(settings, slave_status)

                # Compute statistics of the average time needed for a sync
                perfcounters.count_time("sync", time.time() - now)


def replication_update_state(settings: Settings, config: Dict[str, Any], event_status: EventStatus,
                             event_server: EventServer, new_state: Dict[str, Any]) -> None:
    # Keep a copy of the masters' rules and actions and also prepare using them
    if "rules" in new_state:
        save_master_config(settings, new_state)
        event_server.compile_rules(new_state["rules"], new_state.get("rule_packs", []))
        config["actions"] = new_state["actions"]

    # Update to the masters' event state
    event_status.unpack_status(new_state["status"])


def save_master_config(settings: Settings, new_state: Dict[str, Any]) -> None:
    path = settings.paths.master_config_file.value
    path_new = path.parent / (path.name + '.new')
    path_new.write_text(repr({
        "rules": new_state["rules"],
        "rule_packs": new_state["rule_packs"],
        "actions": new_state["actions"],
    }) + "\n",
                        encoding="utf-8")
    path_new.rename(path)


def load_master_config(settings: Settings, config: Dict[str, Any], logger: Logger) -> None:
    path = settings.paths.master_config_file.value
    try:
        master_config = ast.literal_eval(path.read_text(encoding="utf-8"))
        config["rules"] = master_config["rules"]
        config["rule_packs"] = master_config.get("rule_packs", [])
        config["actions"] = master_config["actions"]
        logger.info("Replication: restored %d rule packs and %d actions from %s" %
                    (len(config["rule_packs"]), len(config["actions"]), path))
    except Exception:
        if is_replication_slave(config):
            logger.error("Replication: no previously saved master state available")


def get_state_from_master(config: Dict[str, Any], slave_status: Dict[str, Any]) -> Any:
    repl_settings = config["replication"]
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(repl_settings["connect_timeout"])
        sock.connect(repl_settings["master"])
        sock.sendall(b"REPLICATE %d\n" %
                     (slave_status["last_sync"] and slave_status["last_sync"] or 0))
        sock.shutdown(socket.SHUT_WR)

        response_text = b""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return ast.literal_eval(response_text.decode("utf-8"))
    except SyntaxError:
        raise Exception("Invalid response from event daemon: <pre>%r</pre>" % response_text)

    except IOError as e:
        raise Exception("Master not responding: %s" % e)

    except Exception as e:
        raise Exception("Cannot connect to event daemon: %s" % e)


def save_slave_status(settings: Settings, slave_status: Dict[str, Any]) -> None:
    settings.paths.slave_status_file.value.write_text(repr(slave_status) + "\n", encoding="utf-8")


def default_slave_status_master() -> Dict[str, Any]:
    return {
        "last_sync": 0,
        "last_master_down": None,
        "mode": "master",
        "average_sync_time": None,
    }


def default_slave_status_sync() -> Dict[str, Any]:
    return {
        "last_sync": 0,
        "last_master_down": None,
        "mode": "sync",
        "average_sync_time": None,
    }


def update_slave_status(slave_status: Dict[str, Any], settings: Settings,
                        config: Dict[str, Any]) -> None:
    path = settings.paths.slave_status_file.value
    if is_replication_slave(config):
        try:
            slave_status.update(ast.literal_eval(path.read_text(encoding="utf-8")))
        except Exception:
            slave_status.update(default_slave_status_sync())
            save_slave_status(settings, slave_status)
    else:
        if path.exists():
            path.unlink()
        slave_status.update(default_slave_status_master())


#.
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


def load_configuration(settings: Settings, logger: Logger,
                       slave_status: Dict[str, Any]) -> Dict[str, Any]:
    config = load_config_using(settings)

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

    if config.get("translate_snmptraps") is True:
        config["translate_snmptraps"] = (True, {})  # convert from pre-1.6.0 format

    # Are we a replication slave? Parts of the configuration
    # will be overridden by values from the master.
    update_slave_status(slave_status, settings, config)
    if is_replication_slave(config):
        logger.info("Replication: slave configuration, current mode: %s" % slave_status["mode"])
    load_master_config(settings, config, logger)

    # Create dictionary for actions for easy access
    config["action"] = {}
    for action in config["actions"]:
        config["action"][action["id"]] = action

    config["last_reload"] = time.time()

    return config


def reload_configuration(settings: Settings, logger: Logger, lock_configuration: ECLock,
                         history: History, event_status: EventStatus, event_server: EventServer,
                         status_server: StatusServer, slave_status: Dict[str, Any]) -> None:
    with lock_configuration:
        config = load_configuration(settings, logger, slave_status)
        history.reload_configuration(config)
        event_server.reload_configuration(config)

    event_status.reload_configuration(config)
    status_server.reload_configuration(config)
    logger.info("Reloaded configuration.")


#.
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
    os.unsetenv("LANG")
    logger = getLogger("cmk.mkeventd")
    settings = create_settings(cmk_version.__version__, Path(cmk.utils.paths.omd_root),
                               Path(cmk.utils.paths.default_config_dir), sys.argv)

    pid_path = None
    try:
        log.setup_logging_handler(sys.stderr)
        log.logger.setLevel(log.verbosity_to_log_level(settings.options.verbosity))

        settings.paths.log_file.value.parent.mkdir(parents=True, exist_ok=True)
        if not settings.options.foreground:
            log.open_log(str(settings.paths.log_file.value))

        logger.info("-" * 65)
        logger.info("mkeventd version %s starting", cmk_version.__version__)

        slave_status = default_slave_status_master()
        config = load_configuration(settings, logger, slave_status)
        history = History(settings, config, logger, StatusTableEvents.columns,
                          StatusTableHistory.columns)

        pid_path = settings.paths.pid_file.value
        if pid_path.exists():
            old_pid = int(pid_path.read_text(encoding='utf-8'))
            if process_exists(old_pid):
                bail_out(
                    logger,
                    "Old PID file %s still existing and mkeventd still running with PID %d." %
                    (pid_path, old_pid))
            pid_path.unlink()
            logger.info("Removed orphaned PID file %s (process %d not running anymore).", pid_path,
                        old_pid)

        # Make sure paths exist
        settings.paths.event_pipe.value.parent.mkdir(parents=True, exist_ok=True)
        settings.paths.status_file.value.parent.mkdir(parents=True, exist_ok=True)

        # First do all things that might fail, before daemonizing
        perfcounters = Perfcounters(logger.getChild("lock.perfcounters"))
        event_status = EventStatus(settings, config, perfcounters, history,
                                   logger.getChild("EventStatus"))
        lock_configuration = ECLock(logger.getChild("lock.configuration"))
        event_server = EventServer(logger.getChild("EventServer"), settings, config, slave_status,
                                   perfcounters, lock_configuration, history, event_status,
                                   StatusTableEvents.columns)
        terminate_main_event = threading.Event()
        status_server = StatusServer(logger.getChild("StatusServer"), settings, config,
                                     slave_status, perfcounters, lock_configuration, history,
                                     event_status, event_server, terminate_main_event)

        event_status.load_status(event_server)
        event_server.compile_rules(config["rules"], config["rule_packs"])

        if not settings.options.foreground:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            cmk.utils.daemon.daemonize()
            logger.info("Daemonized with PID %d.", os.getpid())

        cmk.utils.daemon.lock_with_pid_file(pid_path)

        # Install signal hander
        def signal_handler(signum: int, stack_frame: Optional[FrameType]) -> None:
            logger.log(VERBOSE, "Got signal %d.", signum)
            raise MKSignalException(signum)

        signal.signal(signal.SIGHUP, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGQUIT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Now let's go...
        run_eventd(terminate_main_event, settings, config, lock_configuration, history,
                   perfcounters, event_status, event_server, status_server, slave_status, logger)

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
                settings.options.syslog_udp, settings.options.syslog_tcp,
                settings.options.snmptrap_udp
        ]:
            try:
                if isinstance(fd, FileDescriptor):
                    os.close(fd.value)
            except Exception:
                pass

        logger.info("Successfully shut down.")
        sys.exit(0)

    except MKSignalException:
        pass

    except Exception:
        if settings.options.debug:
            raise

        CrashReportStore().save(ECCrashReport.from_exception())
        bail_out(logger, traceback.format_exc())

    finally:
        if pid_path and store.have_lock(str(pid_path)):
            try:
                pid_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
