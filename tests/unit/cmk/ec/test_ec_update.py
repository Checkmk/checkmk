#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC UPDATE methods with one or more event IDs"""
import pytest

from tests.testlib import CMKEventConsole

from tests.unit.cmk.ec.helpers import FakeStatusSocket

from cmk.ec.main import Event, EventStatus, StatusServer
from cmk.ec.query import MKClientError


@pytest.mark.parametrize(
    "start_phase,set_phase_to", [("open", "0"), ("open", "1"), ("ack", "0"), ("ack", "1")]
)
def test_update_event(
    event_status: EventStatus,
    status_server: StatusServer,
    start_phase: str,
    set_phase_to: str,
) -> None:
    """Update and acknowledge one event"""
    event: Event = {
        "host": "host_1",
        "phase": start_phase,
        "core_host": "ABC",
    }
    event_status.new_event(CMKEventConsole.new_event(event))
    s = FakeStatusSocket(
        bytes(f"COMMAND UPDATE;1;testuser;{set_phase_to};test_comment;test_contact_name", "utf-8")
    )
    status_server.handle_client(s, True, "127.0.0.1")

    assert event_status.events()[0]["phase"] == "ack" if set_phase_to == "1" else "open"
    assert event_status.events()[0]["comment"] == "test_comment"
    assert event_status.events()[0]["contact"] == "test_contact_name"


@pytest.mark.parametrize("test_phase", ["delayed", "closed", "counting"])
def test_update_events_that_cant_be_acked(
    event_status: EventStatus,
    status_server: StatusServer,
    test_phase: str,
) -> None:
    """Update and acknowledge an event when the phase is not 'ack' or 'open'"""
    event: Event = {
        "host": "host_1",
        "phase": test_phase,
        "core_host": "ABC",
    }
    event_status.new_event(CMKEventConsole.new_event(event))
    s = FakeStatusSocket(b"COMMAND UPDATE;1;testuser;1;test_comment;test_contact_name")
    with pytest.raises(MKClientError) as excinfo:
        status_server.handle_client(s, True, "127.0.0.1")

    assert "You cannot acknowledge an event that is not open." in str(excinfo.value)


def test_update_multiple_events(event_status: EventStatus, status_server: StatusServer) -> None:
    """Update and acknowledge multiple events"""
    events: list[Event] = [
        {
            "host": f"host_{i}",
            "phase": "open",
            "core_host": "ABC",
        }
        for i in range(1, 11)
    ]

    for event in events:
        event_status.new_event(CMKEventConsole.new_event(event))

    event_ids = ",".join([str(n + 1) for n, _ in enumerate(event_status.events())])
    s = FakeStatusSocket(
        bytes(f"COMMAND UPDATE;{event_ids};testuser;1;test_comment;test_contact_name", "utf-8")
    )
    status_server.handle_client(s, True, "127.0.0.1")

    for i in range(len(events)):
        assert event_status.events()[i]["phase"] == "ack"
        assert event_status.events()[i]["comment"] == "test_comment"
        assert event_status.events()[i]["contact"] == "test_contact_name"
