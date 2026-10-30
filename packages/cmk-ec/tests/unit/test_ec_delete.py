#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC delete methods with one or more event IDs"""

from dataclasses import replace

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ec.main import EventStatus, StatusServer

from .helpers import FakeConnection, FakeStatusSocket, new_event, new_host


def test_delete_event(event_status: EventStatus, status_server: StatusServer) -> None:
    """Delete 1 event"""
    event = ec.Event(
        host=HostName("ABC1"),
        text="not important",
        core_host=HostName("ABC"),
    )
    event_status.new_event(new_event(event))

    assert len(event_status.events()) == 1

    s = FakeStatusSocket(b"COMMAND DELETE;1;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert len(event_status.events()) == 0


def test_delete_multiple_events(event_status: EventStatus, status_server: StatusServer) -> None:
    """Delete event list"""
    events: list[ec.Event] = [
        {
            "host": HostName("ABC1"),
            "text": "event1 text",
            "core_host": HostName("ABC"),
        },
        {
            "host": HostName("ABC2"),
            "text": "event2 text",
            "core_host": HostName("ABC"),
        },
    ]
    for event in events:
        event_status.new_event(new_event(event))

    assert len(event_status.events()) == 2

    s = FakeStatusSocket(b"COMMAND DELETE;1,2;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert len(event_status.events()) == 0


def test_delete_partially_existing_multiple_events(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    """Event list with a missing ID still deletes the existing ID"""
    events: list[ec.Event] = [
        {
            "host": HostName("ABC1"),
            "text": "event1 text",
            "core_host": HostName("ABC"),
        },
        {
            "host": HostName("ABC2"),
            "text": "event2 text",
            "core_host": HostName("ABC"),
        },
    ]
    for event in events:
        event_status.new_event(new_event(event))

    assert len(event_status.events()) == 2

    s = FakeStatusSocket(b"COMMAND DELETE;2;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert len(event_status.events()) == 1

    s = FakeStatusSocket(b"COMMAND DELETE;1,2;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert len(event_status.events()) == 0


def test_delete_events_of_host(event_status: EventStatus, status_server: StatusServer) -> None:
    """Delete all events of host"""
    events: list[ec.Event] = [
        {
            "host": HostName("ABC1"),
            "text": "event1 text",
            "core_host": HostName("ABC"),
        },
        {
            "host": HostName("ABC1"),
            "text": "event2 text",
            "core_host": HostName("ABC"),
        },
    ]
    for event in events:
        event_status.new_event(new_event(event))

    assert len(event_status.events()) == 2

    s = FakeStatusSocket(b"COMMAND DELETE_EVENTS_OF_HOST;ABC1;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert len(event_status.events()) == 0


def test_delete_events_of_host_deletes_the_events_of_the_monitored_host(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    """Events reach a monitored host via its address or alias, too"""
    events: list[ec.Event] = [
        {"host": HostName("10.0.0.1"), "text": "via address", "core_host": HostName("myhost")},
        {"host": HostName("my-alias"), "text": "via alias", "core_host": HostName("myhost")},
        {"host": HostName("10.0.0.2"), "text": "other host", "core_host": HostName("otherhost")},
    ]
    for event in events:
        event_status.new_event(new_event(event))

    s = FakeStatusSocket(b"COMMAND DELETE_EVENTS_OF_HOST;myhost;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert [event["text"] for event in event_status.events()] == ["other host"]


def test_delete_events_of_host_deletes_events_from_before_the_core_knew_the_host(
    event_status: EventStatus, status_server: StatusServer, core_connection: FakeConnection
) -> None:
    """Views assign events to hosts when showing them, not when the events arrive"""
    core_connection.hosts = [replace(new_host("myhost"), address=HostAddress("10.0.0.1"))]
    event_status.new_event(
        new_event({"host": HostName("10.0.0.1"), "text": "before the host", "core_host": None})
    )

    s = FakeStatusSocket(b"COMMAND DELETE_EVENTS_OF_HOST;myhost;testuser")
    status_server.handle_client(s, True, "127.0.0.1")

    assert event_status.events() == []
