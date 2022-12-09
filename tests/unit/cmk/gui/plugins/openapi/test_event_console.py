#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from functools import partial
from time import time
from typing import Any, Callable

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

DOMAIN_TYPE = "event_console"


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


@pytest.fixture(name="object_base_url")
def object_url(base: str) -> str:
    return f"{base}/objects/{DOMAIN_TYPE}/"


@pytest.fixture(name="collection_base_url")
def collection_url(base: str) -> str:
    return f"{base}/domain-types/{DOMAIN_TYPE}/collections/"


@pytest.fixture(name="get_event")
def partial_get(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="get_events")
def partial_list(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="delete")
def partial_delete_with_filters(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        url=f"{base}/domain-types/{DOMAIN_TYPE}/actions/delete/invoke",
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="change_multiple_event_states")
def partial_change_multiple_event_states(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        url=f"{base}/domain-types/{DOMAIN_TYPE}/actions/change_state/invoke",
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="update_and_acknowledge_multiple_events")
def partial_update_and_acknowledge_multiple_events(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        url=f"{base}/domain-types/{DOMAIN_TYPE}/actions/update_and_acknowledge/invoke",
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="change_state_or_update_and_acknowledge")
def partial_change_state_or_update_and_acknowledge(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


def test_get_all_ec_events(
    mock_livestatus: MockLiveStatusConnection, get_events: Callable, collection_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text"
    )
    with mock_livestatus:
        resp = get_events(collection_base_url + "all")
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert len(resp.json["value"]) == 6
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
    mock_livestatus: MockLiveStatusConnection, get_events: Callable, collection_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host_b"
    )
    with mock_livestatus:
        get_events(collection_base_url + "all?host=test_host_b")


def test_get_all_ec_events_state(
    mock_livestatus: MockLiveStatusConnection, get_events: Callable, collection_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 0"
    )
    with mock_livestatus:
        get_events(collection_base_url + "all?state=ok")


def test_get_all_ec_events_app(
    mock_livestatus: MockLiveStatusConnection, get_events: Callable, collection_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_application = App2"
    )
    with mock_livestatus:
        get_events(collection_base_url + "all?application=App2")


def test_get_all_ec_events_query(
    mock_livestatus: MockLiveStatusConnection, get_events: Callable, collection_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host"
    )
    with mock_livestatus:
        get_events(
            collection_base_url
            + 'all?query={"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}'
        )


def test_get_ec_event_by_id(
    mock_livestatus: MockLiveStatusConnection, get_event: Callable, object_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 2"
    )
    with mock_livestatus:
        resp = get_event(url=object_base_url + "2")
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert {link["method"] for link in resp.json["links"]} == {"GET", "DELETE"}
        assert set((resp.json["extensions"]).keys()) == {
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


def test_get_ec_event_by_str_id(get_event: Callable, object_base_url: str) -> None:
    get_event(url=object_base_url + "non_int_str", status=404)


def test_get_ec_event_that_doesnt_exist_by_id(
    mock_livestatus: MockLiveStatusConnection, get_event: Callable, object_base_url: str
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 20"
    )
    with mock_livestatus:
        get_event(url=object_base_url + "20", status=404)


def test_delete_event_by_id(mock_livestatus: MockLiveStatusConnection, delete: Callable) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 1"
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;1;test123-...", match_type="ellipsis")
    with mock_livestatus:
        delete(params=json.dumps({"filter_type": "by_id", "event_id": 1}))


def test_delete_event_by_query(mock_livestatus: MockLiveStatusConnection, delete: Callable) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host"
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;1;test123-...", match_type="ellipsis")
    with mock_livestatus:
        delete(
            params=json.dumps(
                {
                    "filter_type": "query",
                    "query": '{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
                }
            )
        )


def test_delete_event_by_params_all(
    mock_livestatus: MockLiveStatusConnection, delete: Callable
) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_host = heute\nAnd: 2"
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;5;test123-...", match_type="ellipsis")
    with mock_livestatus:
        delete(
            params=json.dumps(
                {
                    "filter_type": "params",
                    "filters": {
                        "state": "warning",
                        "host": "heute",
                        "application": "App5",
                    },
                }
            )
        )


def test_delete_event_by_phase(mock_livestatus: MockLiveStatusConnection, delete: Callable) -> None:
    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_phase = ack"
    )
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;2,4,6;test123-...", match_type="ellipsis")

    with mock_livestatus:
        delete(
            params=json.dumps(
                {
                    "filter_type": "params",
                    "filters": {
                        "phase": "ack",
                    },
                }
            )
        )


def test_delete_event_no_params(delete: Callable) -> None:
    delete(params=json.dumps({"filter_type": "params"}), status=400)


def test_change_existing_event_state_by_id(
    mock_livestatus: MockLiveStatusConnection,
    object_base_url: str,
    change_state_or_update_and_acknowledge: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 1"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;1;test123-...;1", match_type="ellipsis"
    )

    with mock_livestatus:
        change_state_or_update_and_acknowledge(
            url=object_base_url + "1/actions/change_state/invoke",
            params=json.dumps({"new_state": "warning"}),
        )


def test_change_non_existing_event_state_by_id(
    mock_livestatus: MockLiveStatusConnection,
    object_base_url: str,
    change_state_or_update_and_acknowledge: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 7"
    )

    with mock_livestatus:
        change_state_or_update_and_acknowledge(
            status=404,
            url=object_base_url + "7/actions/change_state/invoke",
            params=json.dumps({"new_state": "warning"}),
        )


def test_change_existing_event_states_query_filter(
    mock_livestatus: MockLiveStatusConnection,
    change_multiple_event_states: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;1;test123-...;3", match_type="ellipsis"
    )

    with mock_livestatus:
        change_multiple_event_states(
            params=json.dumps(
                {
                    "filter_type": "query",
                    "query": '{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
                    "new_state": "unknown",
                }
            ),
        )


def test_change_existing_event_states_params_filter(
    mock_livestatus: MockLiveStatusConnection,
    change_multiple_event_states: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_phase = open\nAnd: 2\nFilter: event_host = heute\nAnd: 2"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CHANGESTATE;5;test123-...;3", match_type="ellipsis"
    )

    with mock_livestatus:
        change_multiple_event_states(
            params=json.dumps(
                {
                    "filter_type": "params",
                    "new_state": "unknown",
                    "filters": {
                        "state": "warning",
                        "host": "heute",
                        "application": "App5",
                        "phase": "open",
                    },
                }
            ),
        )


def test_change_existing_event_states_no_filters(
    change_multiple_event_states: Callable,
) -> None:
    change_multiple_event_states(
        params=json.dumps(
            {
                "filter_type": "params",
                "new_state": "unknown",
            }
        ),
        status=400,
    )


def test_update_and_acknowledge_by_id(
    mock_livestatus: MockLiveStatusConnection,
    object_base_url: str,
    change_state_or_update_and_acknowledge: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 1"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;1;test123-...;1;comment_changed;tribe29", match_type="ellipsis"
    )

    with mock_livestatus:
        change_state_or_update_and_acknowledge(
            url=object_base_url + "1/actions/update_and_acknowledge/invoke",
            params=json.dumps(
                {
                    "change_comment": "comment_changed",
                    "change_contact": "tribe29",
                }
            ),
        )


def test_update_and_acknowledge_non_existing_event_by_id(
    mock_livestatus: MockLiveStatusConnection,
    object_base_url: str,
    change_state_or_update_and_acknowledge: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_id = 7"
    )

    with mock_livestatus:
        change_state_or_update_and_acknowledge(
            status=404,
            url=object_base_url + "7/actions/update_and_acknowledge/invoke",
            params=json.dumps(
                {
                    "change_contact": "testcontact",
                    "change_comment": "testcomment",
                }
            ),
        )


def test_update_and_acknowledge_query_filter(
    mock_livestatus: MockLiveStatusConnection,
    update_and_acknowledge_multiple_events: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_host = test_host\nFilter: event_phase = open\nAnd: 2"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;1;test123-...;1;testcomment;testcontact", match_type="ellipsis"
    )

    with mock_livestatus:
        update_and_acknowledge_multiple_events(
            params=json.dumps(
                {
                    "filter_type": "query",
                    "query": '{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
                    "change_contact": "testcontact",
                    "change_comment": "testcomment",
                },
            ),
        )


def test_update_and_acknowledge_params_filter(
    mock_livestatus: MockLiveStatusConnection,
    update_and_acknowledge_multiple_events: Callable,
) -> None:

    add_event_console_events_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET eventconsoleevents\nColumns: event_id event_state event_sl event_host event_rule_id event_application event_comment event_contact event_ipaddress event_facility event_priority event_last event_first event_count event_phase event_text\nFilter: event_state = 1\nFilter: event_application = App5\nAnd: 2\nFilter: event_phase = open\nAnd: 2\nFilter: event_host = heute\nAnd: 2"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_UPDATE;5;test123-...;1;testcomment;testcontact", match_type="ellipsis"
    )

    with mock_livestatus:
        update_and_acknowledge_multiple_events(
            params=json.dumps(
                {
                    "filter_type": "params",
                    "filters": {
                        "state": "warning",
                        "host": "heute",
                        "application": "App5",
                    },
                    "change_contact": "testcontact",
                    "change_comment": "testcomment",
                },
            ),
        )


def test_update_and_acknowledge_no_filters(
    update_and_acknowledge_multiple_events: Callable,
) -> None:

    update_and_acknowledge_multiple_events(
        params=json.dumps(
            {
                "filter_type": "params",
                "change_contact": "testcontact",
                "change_comment": "testcomment",
            }
        ),
        status=400,
    )
