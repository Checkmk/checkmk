#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from time import time
from typing import Any

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry

EXPECTED_COLUMNS = (
    "history_time history_what event_id event_state event_sl event_host event_rule_id event_application "
    "event_comment event_contact event_ipaddress event_facility event_priority "
    "event_count event_phase event_text"
)


def add_event_console_events_to_live_status_table(live: MockLiveStatusConnection) -> None:
    _now = time()

    def create_ec_historical_event(
        event_id: int,
        state: int = 0,
        phase: str = "open",
        host: str = "heute",
        history_what: str = "NEW",
        history_time_offset: float = 0.0,
    ) -> dict[str, Any]:
        return {
            "history_time": _now + history_time_offset,
            "history_what": history_what,
            "event_id": event_id,
            "event_state": state,
            "event_sl": 10,
            "event_host": host,
            "event_rule_id": f"Rule{event_id}",
            "event_application": f"App{event_id}",
            "event_comment": "",
            "event_contact": "",
            "event_ipaddress": "",
            "event_facility": 2,
            "event_priority": 4,
            "event_count": 1,
            "event_phase": phase,
            "event_text": "Test event text",
        }

    live.add_table(
        "eventconsolehistory",
        [
            create_ec_historical_event(
                1,
                host="test_host",
            ),
            create_ec_historical_event(
                2,
                state=3,
                phase="open",
                host="test_host_b",
                history_what="NEW",
                history_time_offset=0,
            ),
            create_ec_historical_event(
                2,
                state=2,
                phase="open",
                host="test_host_b",
                history_what="CHANGESTATE",
                history_time_offset=30,
            ),
            create_ec_historical_event(
                2,
                state=1,
                phase="open",
                host="test_host_b",
                history_what="CHANGESTATE",
                history_time_offset=60,
            ),
            create_ec_historical_event(
                2,
                state=0,
                phase="open",
                host="test_host_b",
                history_what="CHANGESTATE",
                history_time_offset=90,
            ),
            create_ec_historical_event(
                2,
                state=0,
                phase="ack",
                host="test_host_b",
                history_what="UPDATE",
                history_time_offset=120,
            ),
            create_ec_historical_event(
                2,
                state=1,
                phase="ack",
                host="test_host_b",
                history_what="CHANGESTATE",
                history_time_offset=150,
            ),
            create_ec_historical_event(
                2,
                state=1,
                phase="closed",
                host="test_host_b",
                history_what="DELETE",
                history_time_offset=180,
            ),
            create_ec_historical_event(
                3,
                state=2,
                phase="open",
                host="test_host_b",
                history_what="NEW",
                history_time_offset=0,
            ),
            create_ec_historical_event(
                4,
                state=0,
                phase="ack",
                host="test_host_b",
                history_what="NEW",
                history_time_offset=0,
            ),
            create_ec_historical_event(
                5,
                state=1,
                phase="open",
                host="test_host_b",
                history_what="NEW",
                history_time_offset=0,
            ),
            create_ec_historical_event(
                6,
                state=0,
                phase="ack",
                host="test_host_b",
                history_what="NEW",
                history_time_offset=0,
            ),
        ],
    )


def test_get_ec_event_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_id = 2",
        sites=["NO_SITE"],
    )
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get(event_id="2", site_id="NO_SITE")
        assert resp.json["domainType"] == clients.HistoricalEventConsole.domain
        assert {link["method"] for link in resp.json["links"]} == {"GET"}

        extensions = resp.json["extensions"]
        assert set(extensions.keys()) == {
            "site_id",
            "host",
            "rule_id",
            "ipaddress",
            "facility",
            "priority",
            "history",
        }

        # Event 2 has 7 rows covering all states and phases
        assert len(extensions["history"]) == 7
        assert set(extensions["history"][0].keys()) == {
            "action",
            "phase",
            "state",
            "count",
            "text",
            "application",
            "service_level",
            "comment",
            "contact",
            "timestamp",
        }
        # Entries are in chronological order
        assert [entry["action"] for entry in extensions["history"]] == [
            "NEW",
            "CHANGESTATE",
            "CHANGESTATE",
            "CHANGESTATE",
            "UPDATE",
            "CHANGESTATE",
            "DELETE",
        ]
        assert [entry["phase"] for entry in extensions["history"]] == [
            "open",
            "open",
            "open",
            "open",
            "ack",
            "ack",
            "closed",
        ]
        assert [entry["state"] for entry in extensions["history"]] == [
            "unknown",
            "critical",
            "warning",
            "ok",
            "ok",
            "warning",
            "warning",
        ]


def test_get_ec_event_that_does_not_exist(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_id = 7",
        sites=["NO_SITE"],
    )
    with mock_livestatus:
        clients.HistoricalEventConsole.get(
            event_id="7", site_id="NO_SITE", expect_ok=False
        ).assert_status_code(404)


def test_get_all_ec_events(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}")
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all()
        # 11 rows in test data, but 6 unique event IDs after grouping
        assert {event["id"] for event in resp.json["value"]} == {"1", "2", "3", "4", "5", "6"}

        # host is a stable top-level extensions field
        assert {event["extensions"]["host"] for event in resp.json["value"]} == {
            "test_host",
            "test_host_b",
        }

        # application is per-history-entry; first entry of each event gives one per event_id
        assert {
            event["extensions"]["history"][0]["application"] for event in resp.json["value"]
        } == {
            "App1",
            "App2",
            "App3",
            "App4",
            "App5",
            "App6",
        }

        # Event 2 has 7 history entries covering all phases and states
        event2 = next(e for e in resp.json["value"] if e["id"] == "2")
        assert {entry["phase"] for entry in event2["extensions"]["history"]} == {
            "open",
            "ack",
            "closed",
        }
        assert {entry["state"] for entry in event2["extensions"]["history"]} == {
            "unknown",
            "critical",
            "warning",
            "ok",
        }


def test_get_all_ec_events_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_host = test_host_b"
    )
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(host="test_host_b")
        assert len(resp.json["value"]) == 5


def test_get_all_ec_events_state(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_state = 0"
    )
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(state="ok")
        assert len(resp.json["value"]) == 4


def test_get_all_ec_events_app(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_application = App2"
    )
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(application="App2")
        assert len(resp.json["value"]) == 1


def test_get_all_ec_events_phase(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_phase = open"
    )
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(phase="open")
        assert len(resp.json["value"]) == 4


def test_get_all_ec_events_by_ids(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)

    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_id = 1\nFilter: event_id = 3\nFilter: event_id = 5\nOr: 3"
    )

    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(event_ids=[1, 3, 5])
        assert len(resp.json["value"]) == 3


def test_get_all_ec_events_by_ids_none_given(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """Passing an empty list of event IDs is equivalent to leaving event_ids unspecified.

    urllib.parse.urlencode({"event_ids": []}, doseq=True) → "" (empty list produces no query string)
    URL has no event_ids key → werkzeug sees nothing → ApiOmitted

    """
    add_event_console_events_to_live_status_table(mock_livestatus)

    mock_livestatus.expect_query(f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}")

    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(event_ids=[])
        assert len(resp.json["value"]) == 6


def test_get_all_ec_events_query_expression(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        f"GET eventconsolehistory\nColumns: {EXPECTED_COLUMNS}\nFilter: event_rule_id = Rule2"
    )
    with mock_livestatus:
        resp = clients.HistoricalEventConsole.get_all(
            query='{"op": "=", "left": "event_rule_id", "right": "Rule2"}'
        )
        assert len(resp.json["value"]) == 1


def test_get_all_ec_events_invalid_json_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=False):
        clients.HistoricalEventConsole.get_all(
            query="not valid json", expect_ok=False
        ).assert_status_code(400)


def test_get_all_ec_events_query_invalid_column(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=False):
        clients.HistoricalEventConsole.get_all(
            query='{"op": "=", "left": "nonexistent_column", "right": "value"}',
            expect_ok=False,
        ).assert_status_code(400)
