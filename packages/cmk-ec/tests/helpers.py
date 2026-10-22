#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import ast
import socket
import time
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, override

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
START = 475_000 * HOUR + 100.0  # a bit after the start of an hour


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
    replication = Replication(connect_timeout=10, interval=60, master=("master.example.com", 6558))
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


class FakeConnection:
    """A monitoring core answering the Livestatus queries of the Event Console

    All columns of its status are 0, so e.g. notifications are disabled and no test accidentally
    tries to notify via Checkmk. The EC copes with failing queries itself, e.g. it assumes that
    notifications are enabled, so the queries the core can't answer are recorded, too.
    The host configuration is read only once, so set the hosts before using them.
    """

    def __init__(self) -> None:
        self.hosts: list[HostInfo] = []
        self.hosts_in_downtime: set[HostName] = set()
        self.unexpected_queries: list[str] = []

    def query(self, query: str) -> Sequence[Sequence[Any]]:
        match query.splitlines():
            case ["GET status", columns, *_headers] if columns.startswith("Columns: "):
                return [[0 for _column in columns.removeprefix("Columns: ").split()]]
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
    """Records in memory what happened to which events"""

    def __init__(self) -> None:
        self.entries: list[tuple[HistoryWhat, Event]] = []

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
        pass
