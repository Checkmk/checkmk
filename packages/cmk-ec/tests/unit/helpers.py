#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import array
import ast
import fcntl
import os
import socket
import termios
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, override

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ec.config import Config, Count, Replication, Rule, ServiceLevel
from cmk.ec.core_queries import HostInfo
from cmk.ec.defaults import default_rule_pack
from cmk.ec.event import Event
from cmk.ec.history import History, HistoryWhat
from cmk.ec.main import EventServer, StatusServer
from cmk.ec.query import QueryGET
from cmk.ec.settings import Settings

HOUR = 3600
INTERVAL_START = 475_000 * HOUR
START = INTERVAL_START + 100.0  # a bit after the start of an hour
MASTER = ("master.example.com", 6558)  # of a replication slave

# Events whose first times are their texts, for TIME_FILTER_CASES
EVENTS_WITH_FIRST_TIMES: Sequence[Event] = [
    Event(text=text, first=float(text))
    for text in ["-1.5", "-0.5", "0.5", "4.5", "5.0", "5.5", "6.0"]
]

# Filters on the first times of these events and the texts of the events they select, like
# in Livestatus, which compares the times truncated to integers
TIME_FILTER_CASES = [
    pytest.param("=",  "5",  {"5.0", "5.5"},                                   id="equal"),
    pytest.param("!=", "5",  {"-1.5", "-0.5", "0.5", "4.5", "6.0"},            id="not equal"),
    pytest.param("<",  "5",  {"-1.5", "-0.5", "0.5", "4.5"},                   id="less"),
    pytest.param("<=", "5",  {"-1.5", "-0.5", "0.5", "4.5", "5.0", "5.5"},     id="less or equal"),
    pytest.param(">",  "5",  {"6.0"},                                          id="greater"),
    pytest.param(">=", "5",  {"5.0", "5.5", "6.0"},                            id="greater or equal"),
    pytest.param("=",  "0",  {"-0.5", "0.5"},                                  id="truncated toward zero"),
    pytest.param("<",  "0",  {"-1.5"},                                         id="less than zero"),
    pytest.param(">",  "-1", {"-0.5", "0.5", "4.5", "5.0", "5.5", "6.0"},      id="greater than a negative number"),
    pytest.param("<=", "-1", {"-1.5"},                                         id="less or equal to a negative number"),
]  # fmt: skip

# Events with contact groups, a list column, for LIST_FILTER_CASES. Like an archived orphan,
# i.e. an event that no rule matched, the one with the text "missing" has none at all. For
# Livestatus, a last empty string is lost, so it sees ["ops", ""] as ["ops"].
EVENTS_WITH_CONTACT_GROUPS: Sequence[Event] = [
    Event(text="missing"),
    Event(text="none", contact_groups=None),
    Event(text="empty", contact_groups=[]),
    Event(text="admins", contact_groups=["admins", "ops"]),
    Event(text="Admins", contact_groups=["Admins"]),
    Event(text="empty string", contact_groups=[""]),
    Event(text="last empty", contact_groups=["ops", ""]),
    Event(text="first empty", contact_groups=["", "ops"]),
]

_ALL = {event["text"] for event in EVENTS_WITH_CONTACT_GROUPS}

# Filters on the contact groups and the texts of the events they select, like in Livestatus
LIST_FILTER_CASES = [
    pytest.param("=",   "",         {"missing", "none", "empty", "empty string"},      id="empty"),
    pytest.param("=",   "admins",   set(),                                             id="equal tests only for emptiness"),
    pytest.param("!=",  "",         {"admins", "Admins", "last empty", "first empty"}, id="not empty"),
    pytest.param("!=",  "admins",   set(),                                             id="not equal tests only for emptiness"),
    pytest.param(">=",  "admins",   {"admins"},                                        id="contains"),
    pytest.param(">=",  "adm",      set(),                                             id="contains only whole elements"),
    pytest.param(">=",  "",         {"first empty"},                                   id="contains an empty string before the last element"),
    pytest.param("<",   "admins",   _ALL - {"admins"},                                 id="doesn't contain"),
    pytest.param("<",   "",         _ALL - {"first empty"},                            id="doesn't contain an empty string before the last element"),
    pytest.param("<=",  "ADMINS",   {"admins", "Admins"},                              id="contains ignoring case"),
    pytest.param(">",   "ADMINS",   _ALL - {"admins", "Admins"},                       id="doesn't contain ignoring case"),
    pytest.param("~",   "^adm",     {"admins"},                                        id="an element matches"),
    pytest.param("~",   "^(ops)?$", {"admins", "last empty", "first empty"},           id="an element or an empty string before the last one matches"),
    pytest.param("!~",  "^adm",     _ALL - {"admins"},                                 id="no element matches"),
    pytest.param("~~",  "^ADM",     {"admins", "Admins"},                              id="an element matches ignoring case"),
    pytest.param("!~~", "^ADM",     _ALL - {"admins", "Admins"},                       id="no element matches ignoring case"),
    pytest.param("!~~", "^$",       _ALL - {"first empty"},                            id="no empty string before the last element matches"),
    pytest.param("=~",  "admins",   set(),                                             id="equal ignoring case never holds"),
    pytest.param("!=~", "admins",   set(),                                             id="not equal ignoring case never holds"),
]  # fmt: skip


class FakeStatusSocket(socket.socket):
    def __init__(self, query: bytes) -> None:
        super().__init__()
        super().close()  # Only the type is needed, so don't leak the OS socket.
        self._query = query
        self._sent = False
        self._response = b""

    @override
    def recv(self, buflen: int, flags: int = 4711) -> bytes:
        if self._sent:
            return b""

        self._sent = True
        return self._query

    @override
    def sendall(self, b: Any, flags: int = 4711) -> None:
        self._response += b

    @override
    def close(self) -> None:
        pass

    def get_response(self) -> Any:
        return ast.literal_eval(self._response.decode("utf-8"))
        # assert isinstance(response, list)

    def get_raw_response(self) -> bytes:
        return self._response


# Makes a status server with the given clock for CREATE, see the fixture make_status_server
type MakeStatusServer = Callable[[Callable[[], float]], StatusServer]


def query_status_server(
    status_server: StatusServer, query: str, *, allow_commands: bool = True
) -> FakeStatusSocket:
    """Lets the status server handle a single query of a client"""
    status_socket = FakeStatusSocket(query.encode())
    status_server.handle_client(status_socket, allow_commands, "127.0.0.1")
    return status_socket


def new_event(attrs: Event) -> Event:
    now = time.time()
    default_event = Event(
        rule_id="815",
        text="",
        phase="open",
        count=1,
        time=now,
        first=now,
        last=now,
        comment="",
        host=HostName("test-host"),
        ipaddress="127.0.0.1",
        application="",
        pid=0,
        priority=3,
        facility=1,  # user
        match_groups=(),
        core_host=None,
        host_in_downtime=False,
    )

    event = default_event.copy()
    event.update(attrs)
    return event


def new_message(attrs: Event) -> Event:
    """Returns an event like it is created from an incoming message, i.e. before applying rules"""
    message = Event(
        facility=1,  # user
        priority=3,
        text="",
        host=HostName("test-host"),
        ipaddress="127.0.0.1",
        application="",
        pid=0,
        time=time.time(),
        core_host=None,
        host_in_downtime=False,
    )
    message.update(attrs)
    return message


def process_message(event_server: EventServer, attrs: Event | None = None) -> None:
    """Lets the event server process an incoming message"""
    event_server.process_potential_event(new_message(Event() if attrs is None else attrs))


def new_rule(attrs: Rule) -> Rule:
    """Returns a rule which matches any message and opens an OK event"""
    rule = Rule(
        id="rule",
        actions=[],
        actions_in_downtime=True,
        autodelete=False,
        cancel_action_phases="always",
        cancel_actions=[],
        comment="",
        description="",
        disabled=False,
        docu_url="",
        invert_matching=False,
        sl=ServiceLevel(precedence="message", value=0),
        state=0,
    )
    rule.update(attrs)
    return rule


def use_rules(event_server: EventServer, *rules: Rule) -> None:
    """Makes the event server use the given rules without reloading its configuration"""
    event_server.compile_rules([default_rule_pack(rules)])


def new_count(count: int, period: int) -> Count:
    """Returns how many messages within a period open an event, counting all messages together"""
    return Count(
        count=count,
        period=period,
        algorithm="interval",
        count_duration=None,
        count_ack=False,
        separate_host=False,
        separate_application=False,
        separate_match_groups=False,
    )


def new_host(name: str, custom_variables: Mapping[str, str] | None = None) -> HostInfo:
    """Returns a host of the monitoring core"""
    return HostInfo(
        name=HostName(name),
        alias="",
        address=HostAddress(""),
        custom_variables={} if custom_variables is None else custom_variables,
        contacts=set(),
        contact_groups=set(),
        host_groups=set(),
    )


def replication_slave_config(
    config: Config, *, takeover: int | None = None, fallback: int | None = None
) -> Config:
    """Turns the configuration of an EC into one of a replication slave"""
    replication = Replication(connect_timeout=10, interval=60, master=MASTER)
    if takeover is not None:
        replication["takeover"] = takeover
    if fallback is not None:
        replication["fallback"] = fallback
    return config | {"replication": replication}


def activate_config(settings: Settings, config_text: str) -> None:
    """Makes the given configuration the active one of the EC, like activating changes does"""
    path = settings.paths.active_config_dir.value / "mkeventd.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config_text)


def wait_until_bytes_in_pipe(fd: int, count: int) -> None:
    deadline = time.monotonic() + 30
    while _bytes_in_pipe(fd) < count:
        assert time.monotonic() < deadline, f"pipe didn't get {count} bytes"
        time.sleep(0.01)


def _bytes_in_pipe(fd: int) -> int:
    buffer = array.array("i", [0])
    fcntl.ioctl(fd, termios.FIONREAD, buffer)
    return buffer[0]


def wait_until_exists(path: Path) -> None:
    deadline = time.monotonic() + 30
    while not path.exists():
        assert time.monotonic() < deadline, f"{path} doesn't exist"
        time.sleep(0.01)


def put_on_path(monkeypatch: pytest.MonkeyPatch, directory: Path, name: str, script: str) -> None:
    """Puts a command of the name running the shell script into the directory, first on the PATH"""
    command = directory / name
    directory.mkdir()
    command.write_text(f"#!/bin/sh\n{script}\n")
    command.chmod(0o755)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")


class FakeConnection:
    """A monitoring core answering the Livestatus queries of the Event Console

    All columns of its status are 0, unless notifications are enabled, so no test accidentally
    tries to notify via Checkmk. The EC copes with failing queries itself, e.g. it assumes that
    notifications are enabled, so the queries the core can't answer are recorded, too.
    The host configuration is read only once, so set the hosts before using them.
    """

    def __init__(self) -> None:
        self.hosts: list[HostInfo] = []
        self.hosts_in_downtime: set[HostName] = set()
        self.notifications_enabled = False
        self.unexpected_queries: list[str] = []

    def query(self, query: str) -> Sequence[Sequence[Any]]:
        match query.splitlines():
            case ["GET status", columns, *_headers] if columns.startswith("Columns: "):
                return [
                    [
                        int(self.notifications_enabled) if column == "enable_notifications" else 0
                        for column in columns.removeprefix("Columns: ").split()
                    ]
                ]
            case [
                "GET hosts",
                "Columns: name alias address custom_variables contacts contact_groups groups",
            ]:
                return [
                    [
                        host.name,
                        host.alias,
                        host.address,
                        host.custom_variables,
                        host.contacts,
                        host.contact_groups,
                        host.host_groups,
                    ]
                    for host in self.hosts
                ]
            case ["GET hosts", "Columns: scheduled_downtime_depth", host_filter]:
                host_name = host_filter.removeprefix("Filter: host_name = ")
                return [[1 if host_name in self.hosts_in_downtime else 0]]
            case _:
                self.unexpected_queries.append(query)
                raise ValueError(f"unexpected Livestatus query {query!r}")


class RecordingHistory(History):
    """Records in memory what happened to which events, and whether it got closed"""

    def __init__(self) -> None:
        self.entries: list[tuple[HistoryWhat, Event]] = []
        self.closed = False

    @property
    def whats(self) -> list[HistoryWhat]:
        return [what for what, _event in self.entries]

    @override
    def flush(self) -> None:
        self.entries.clear()

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        self.entries.append((what, event.copy()))

    @override
    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        raise NotImplementedError("querying is not recorded")

    @override
    def housekeeping(self) -> None:
        pass

    @override
    def close(self) -> None:
        self.closed = True
