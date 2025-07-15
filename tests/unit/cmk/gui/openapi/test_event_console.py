#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from time import time
from typing import Any

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from tests.testlib.unit.rest_api_client import ClientRegistry


def add_event_console_events_to_live_status_table(live: MockLiveStatusConnection) -> None:
    def create_ec_event(
        event_id: int, state: int = 0, phase: str = "open", host: str = "heute"
    ) -> dict[str, Any]:
        return {
            "event_id": event_id,
            "event_state": state,
            "event_sl": 10,
            "event_host": host,
            "event_rule_id": f"Rule{event_id}",
            "event_application": f"App{event_id}",
            "event_comment": "",
            "event_contact": "",
            "event_ipaddress": "",
            "event_facility": "",
            "event_priority": "",
            "event_last": time(),
            "event_first": time() - 7 * 24 * 60 * 60,
            "event_count": 1,
            "event_phase": phase,
            "event_text": "Test event text",
        }

    live.add_table(
        "eventconsoleevents",
        [
            create_ec_event(1, host="test_host"),
            create_ec_event(2, state=3, phase="ack", host="test_host_b"),
            create_ec_event(3, state=2, host="test_host_b"),
            create_ec_event(4, phase="ack"),
            create_ec_event(5, state=1),
            create_ec_event(6, phase="ack"),
        ],
    )


def test_get_all_ec_events(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text"
    )
    with mock_livestatus:
        resp = clients.EventConsole.get_all()
        assert {event["id"] for event in resp.json["value"]} == {"1", "2", "3", "4", "5", "6"}
        assert {event["extensions"]["host"] for event in resp.json["value"]} == {
            "heute",
            "test_host",
            "test_host_b",
        }
        assert {event["extensions"]["application"] for event in resp.json["value"]} == {
            "App1",
            "App2",
            "App3",
            "App4",
            "App5",
            "App6",
        }
        assert {event["extensions"]["phase"] for event in resp.json["value"]} == {"open", "ack"}
        assert {event["extensions"]["state"] for event in resp.json["value"]} == {
            "critical",
            "warning",
            "ok",
            "unknown",
        }


def test_get_all_ec_events_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host_b"
    )
    with mock_livestatus:
        clients.EventConsole.get_all(host="test_host_b")


def test_get_all_ec_events_state(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 0"
    )
    with mock_livestatus:
        clients.EventConsole.get_all(state="ok")


def test_get_all_ec_events_app(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_application = App2"
    )
    with mock_livestatus:
        clients.EventConsole.get_all(application="App2")


def test_get_all_ec_events_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host"
    )
    with mock_livestatus:
        clients.EventConsole.get_all(
            query='{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}'
        )


def test_get_ec_event_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 2",
        sites=["NO_SITE"],
    )
    with mock_livestatus:
        resp = clients.EventConsole.get(event_id="2", site_id="NO_SITE")
        assert resp.json["domainType"] == clients.EventConsole.domain
        assert {link["method"] for link in resp.json["links"]} == {"GET", "DELETE"}
        assert set((resp.json["extensions"]).keys()) == {
            "site_id",
            "state",
            "service_level",
            "host",
            "rule_id",
            "application",
            "comment",
            "contact",
            "ipaddress",
            "facility",
            "phase",
            "text",
            "priority",
            "count",
            "last",
            "first",
        }


def test_get_ec_event_by_str_id(clients: ClientRegistry) -> None:
    resp = clients.EventConsole.get(
        event_id="non_int_str",
        site_id="NO_SITE",
        expect_ok=False,
    )
    resp.assert_status_code(404)
    assert resp.json["fields"]["event_id"] == ["'non_int_str' does not match pattern '^[0-9]+$'."]


def test_get_ec_event_that_doesnt_exist_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 20",
        sites=["NO_SITE"],
    )
    with mock_livestatus:
        resp = clients.EventConsole.get(
            event_id="20",
            site_id="NO_SITE",
            expect_ok=False,
        )
        resp.assert_status_code(404)
        assert resp.json == {
            "title": "The requested event was not found",
            "status": 404,
            "detail": "Could not find event with id 20.",
        }


def test_delete_event_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 1",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;1;test123-...", match_type="ellipsis")
    with mock_livestatus:
        clients.EventConsole.delete(
            site_id="NO_SITE",
            filter_type="by_id",
            event_id=1,
        )


def test_delete_event_by_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host",
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;1;test123-...", match_type="ellipsis")
    with mock_livestatus:
        clients.EventConsole.delete(
            filter_type="query",
            query='{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
        )


def test_delete_event_by_params_all(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_host = heute\nAnd: 2",
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;5;test123-...", match_type="ellipsis")
    with mock_livestatus:
        clients.EventConsole.delete(
            filter_type="params",
            state="warning",
            host="heute",
            application="App5",
        )


def test_delete_event_by_phase(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_phase = ack",
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;2,4,6;test123-...", match_type="ellipsis")

    with mock_livestatus:
        clients.EventConsole.delete(
            filter_type="params",
            phase="ack",
        )


def test_delete_event_no_params(clients: ClientRegistry) -> None:
    clients.EventConsole.delete(
        site_id="NO_SITE",
        filter_type="params",
        expect_ok=False,
    ).assert_status_code(400)


def test_change_existing_event_state_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 1",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;1;test123-...;1", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.change_event_state(
            event_id="1",
            site_id="NO_SITE",
            new_state="warning",
        )


def test_change_non_existing_event_state_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 7",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.EventConsole.change_event_state(
            event_id="7",
            site_id="NO_SITE",
            new_state="warning",
            expect_ok=False,
        ).assert_status_code(404)


def test_change_existing_event_states_query_filter(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;1;test123-...;3", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.change_multiple_event_states(
            site_id="NO_SITE",
            filter_type="query",
            new_state="unknown",
            query='{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
        )


def test_change_existing_event_states_params_filter(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_phase = open\nAnd: 2\nFilter: event_host = heute\nAnd: 2",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;5;test123-...;3", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.change_multiple_event_states(
            site_id="NO_SITE",
            filter_type="params",
            new_state="unknown",
            state="warning",
            host="heute",
            application="App5",
            phase="open",
        )


def test_change_existing_event_states_no_filters(
    clients: ClientRegistry,
) -> None:
    clients.EventConsole.change_multiple_event_states(
        site_id="NO_SITE",
        filter_type="params",
        new_state="unknown",
        expect_ok=False,
    ).assert_status_code(400)


def test_update_and_acknowledge_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 1",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;1;test123-...;1;comment_changed;Checkmk", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge(
            event_id="1",
            site_id="NO_SITE",
            change_comment="comment_changed",
            change_contact="Checkmk",
        )


def test_update_and_acknowledge_withdrawal_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 4",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;4;test123-...;0;comment_changed;Checkmk", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge(
            event_id="4",
            site_id="NO_SITE",
            change_comment="comment_changed",
            change_contact="Checkmk",
            phase="open",
        )


def test_update_and_acknowledge_non_existing_event_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 7",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge(
            event_id="7",
            site_id="NO_SITE",
            change_comment="testcontact",
            change_contact="testcomment",
            expect_ok=False,
        ).assert_status_code(404)


def test_update_and_acknowledge_query_filter(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host\nFilter: event_phase = open\nAnd: 2",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;1;test123-...;1;testcomment;testcontact", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge_multiple(
            site_id="NO_SITE",
            filter_type="query",
            query='{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
            change_contact="testcontact",
            change_comment="testcomment",
        )


def test_update_and_acknowledge_params_filter(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_phase = open\nAnd: 2\nFilter: event_host = heute\nAnd: 2",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;5;test123-...;1;testcomment;testcontact", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge_multiple(
            site_id="NO_SITE",
            filter_type="params",
            state="warning",
            host="heute",
            application="App5",
            change_contact="testcontact",
            change_comment="testcomment",
        )


def test_update_and_acknowledge_all_filter(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_phase = open",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;1,3,5;test123-...;1;testcomment;testcontact", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge_multiple(
            site_id="NO_SITE",
            filter_type="all",
            change_contact="testcontact",
            change_comment="testcomment",
        )


def test_update_and_acknowledge_withdrawal_params_filter(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_phase = ack",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;2,4,6;test123-...;0;;", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge_multiple(
            site_id="NO_SITE",
            filter_type="all",
            phase="open",
        )


def test_update_and_acknowledge_no_filters(clients: ClientRegistry) -> None:
    resp = clients.EventConsole.update_and_acknowledge_multiple(
        site_id="NO_SITE",
        filter_type="params",
        change_contact="testcontact",
        change_comment="testcomment",
        expect_ok=False,
    )
    assert resp.json["detail"] == "These fields have problems: filters"


def test_update_and_acknowledge_all_filter_no_site_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_phase = open",
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;1,3,5;test123-...;1;testcomment;testcontact", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.update_and_acknowledge_multiple(
            filter_type="all",
            change_comment="testcomment",
            change_contact="testcontact",
        )


def test_change_existing_event_states_params_filter_no_site_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_phase = open\nAnd: 2\nFilter: event_host = heute\nAnd: 2",
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;5;test123-...;3", match_type="ellipsis"
    )

    with mock_livestatus:
        clients.EventConsole.change_multiple_event_states(
            filter_type="params",
            new_state="unknown",
            state="warning",
            host="heute",
            application="App5",
            phase="open",
        )


def test_update_and_acknowledge_by_id_but_no_site_id(clients: ClientRegistry) -> None:
    resp = clients.EventConsole.update_and_acknowledge(
        event_id="1",
        site_id=None,
        change_comment="testcontact",
        change_contact="testcomment",
        expect_ok=False,
    )
    assert resp.json["fields"] == {"site_id": ["Missing data for required field."]}


def test_change_existing_event_state_by_id_no_site_id(clients: ClientRegistry) -> None:
    resp = clients.EventConsole.change_event_state(
        event_id="1", new_state="warning", expect_ok=False
    )
    assert resp.json["fields"] == {"site_id": ["Missing data for required field."]}
