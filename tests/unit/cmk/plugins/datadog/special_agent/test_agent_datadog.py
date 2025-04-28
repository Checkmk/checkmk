#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
import json
import time
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import requests
import time_machine
from pytest import MonkeyPatch

from cmk.plugins.datadog.special_agent.agent_datadog import (
    _event_to_syslog_message,
    _log_to_syslog_message,
    DatadogAPI,
    Event,
    EventsQuerier,
    Log,
    LogAttributes,
    LogMessageElement,
    LogsQuerier,
    MonitorsQuerier,
    parse_arguments,
)


def test_parse_arguments() -> None:
    parse_arguments(
        [
            "testhost",
            "12345",
            "powerg",
            "api.datadoghq.eu",
            "--monitor_tags",
            "t1",
            "t2",
            "--monitor_monitor_tags",
            "mt1",
            "mt2",
            "--event_max_age",
            "90",
            "--event_tags",
            "t3",
            "t4",
            "--event_tags_show",
            ".*",
            "--event_syslog_facility",
            "1",
            "--event_syslog_priority",
            "1",
            "--event_service_level",
            "0",
            "--event_add_text",
            "--log_max_age",
            "90",
            "--log_indexes",
            "check",
            "MK",
            "--log_query",
            "test",
            "--log_text",
            "name:key",
            "foo:bar",
            "other:foo.bar",
            "--log_syslog_facility",
            "1",
            "--log_service_level",
            "0",
            "--sections",
            "monitors",
            "events",
            "logs",
        ]
    )


class MockDatadogAPI:
    def __init__(self, page_to_data: Mapping[object, object]) -> None:
        self.page_to_data = page_to_data
        self._returned_too_many_requests = False

    def get_request(
        self,
        api_endpoint: str,
        params: Mapping[str, str | int],
        version: str = "v1",
    ) -> requests.Response:
        if (resp := self.page_to_data.get(params["page"])) is None:
            raise RuntimeError
        return self._response(HTTPStatus.OK, json_data=resp)

    def post_request(
        self,
        api_endpoint: str,
        body: Mapping[str, Any],
        version: str = "v1",
    ) -> requests.Response:
        if (resp := self.page_to_data.get(body["page"].get("cursor"))) is None:
            raise RuntimeError
        if self._returned_too_many_requests:
            return self._response(HTTPStatus.OK, json_data=resp)
        self._returned_too_many_requests = True
        return self._response(HTTPStatus.TOO_MANY_REQUESTS)

    @staticmethod
    def _response(status_code: HTTPStatus, json_data: object = None) -> requests.Response:
        response = requests.Response()
        response.status_code = int(status_code)
        if json_data is not None:
            response._content = json.dumps(json_data).encode()
        return response


class TestMonitorsQuerier:
    def test_query_monitors(
        self,
    ) -> None:
        # note: this data is of course incomplete, but sufficient for this test
        monitors_data = [
            {
                "name": "monitor1",
            },
            {
                "name": "monitor2",
            },
            {
                "name": "monitor3",
            },
        ]

        datadog_api = MockDatadogAPI(page_to_data={0: monitors_data, 1: []})

        assert (
            list(
                MonitorsQuerier(datadog_api).query_monitors(
                    [],
                    [],
                )
            )
            == monitors_data
        )


class TestEventsQuerier:
    @pytest.fixture(name="events")
    def fixture_events(self) -> list[Event]:
        return [
            Event(
                id=1,
                tags=[],
                text="text",
                date_happened=123456,
                host="host",
                title="event1",
                source="source",
            ),
            Event(
                id=2,
                tags=[],
                text="text",
                date_happened=123456,
                host="host",
                title="event2",
                source="source",
            ),
            Event(
                id=3,
                tags=[],
                text="text",
                date_happened=123456,
                host="host",
                title="event3",
                source="source",
            ),
        ]

    @pytest.fixture(name="datadog_api")
    def fixture_datadog_api(
        self,
        events: Sequence[Event],
    ) -> MockDatadogAPI:
        return MockDatadogAPI(
            page_to_data={
                0: {"events": [event.model_dump() for event in events]},
                1: {"events": []},
            }
        )

    @pytest.fixture(name="events_querier")
    def fixture_events_querier(self, datadog_api: MockDatadogAPI) -> EventsQuerier:
        return EventsQuerier(
            datadog_api,
            "host_name",
            300,
        )

    def test_events_query_time_range(
        self,
        monkeypatch: MonkeyPatch,
        events_querier: EventsQuerier,
    ) -> None:
        now = 1601310544
        monkeypatch.setattr(time, "time", lambda: now)
        assert events_querier._events_query_time_range() == (
            now - events_querier.max_age,
            now,
        )

    def test_query_events_no_previous_ids(
        self,
        events_querier: EventsQuerier,
        events: Sequence[Event],
    ) -> None:
        assert list(events_querier.query_events([])) == events
        assert events_querier.id_store.read() == frozenset({1, 2, 3})

    def test_query_events_with_previous_ids(
        self,
        events_querier: EventsQuerier,
        events: Sequence[Event],
    ) -> None:
        events_querier.id_store.write([1, 2, 5])
        assert list(events_querier.query_events([])) == events[-1:]
        assert events_querier.id_store.read() == frozenset({1, 2, 3})


def test_event_to_syslog_message() -> None:
    assert (
        repr(
            _event_to_syslog_message(
                Event(
                    id=5938350476538858876,
                    tags=[
                        "ship:enterprise",
                        "location:alpha_quadrant",
                        "priority_one",
                    ],
                    text="Abandon ship\n, abandon ship!",
                    date_happened=1618216122,
                    host="starbase 3",
                    title="something bad happened",
                    source="main bridge",
                ),
                [
                    "ship:.*",
                    "^priority_one$",
                ],
                1,
                1,
                0,
                True,
            )
        )
        == '<9>1 2021-04-12T08:28:42+00:00 - - - - [Checkmk@18662 host="starbase 3" application="main bridge"] something bad happened, Tags: ship:enterprise, priority_one, Text: Abandon ship ~ , abandon ship!'
    )


class TestLogsQuerier:
    @pytest.fixture(name="logs")
    def fixture_logs(self) -> Sequence[Log]:
        return [
            Log(
                attributes=LogAttributes(
                    attributes={},
                    host="host",
                    message="msg",
                    service="app",
                    status="emergency",
                    tags=[],
                    timestamp="2022-09-07T11:01:54.812Z",
                ),
                id="1",
            ),
            Log(
                attributes=LogAttributes(
                    attributes={},
                    host="host",
                    message="msg",
                    service="app",
                    status="emergency",
                    tags=[],
                    timestamp="2022-09-07T11:01:54.812Z",
                ),
                id="2",
            ),
            Log(
                attributes=LogAttributes(
                    attributes={},
                    host="host",
                    message="msg",
                    service="app",
                    status="emergency",
                    tags=[],
                    timestamp="2022-09-07T11:01:54.812Z",
                ),
                id="3",
            ),
            Log(
                attributes=LogAttributes(
                    attributes={},
                    host="host",
                    message="msg",
                    service="app",
                    status="emergency",
                    tags=[],
                    timestamp="2022-09-07T11:01:54.812Z",
                ),
                id="4",
            ),
        ]

    @pytest.fixture(name="datadog_api")
    def fixture_datadog_api(
        self,
        logs: Sequence[Log],
    ) -> MockDatadogAPI:
        return MockDatadogAPI(
            page_to_data={
                None: {
                    "data": [log.model_dump() for log in logs[:3]],
                    "meta": {"page": {"after": "next"}},
                },
                "next": {
                    "data": [log.model_dump() for log in logs[3:]],
                },
            }
        )

    @pytest.fixture(name="logs_querier")
    def fixture_logs_querier(
        self,
        datadog_api: DatadogAPI,
    ) -> LogsQuerier:
        return LogsQuerier(
            datadog_api,
            500,
            query="test",
            indexes=["test"],
            hostname="pytest",
            cooldown_too_many_requests=0,
        )

    def test_logs_query_time_range(
        self,
        logs_querier: LogsQuerier,
    ) -> None:
        now = 1601310544
        with time_machine.travel(datetime.datetime.fromtimestamp(now, tz=ZoneInfo("UTC"))):
            start, end = logs_querier._query_time_range()
            assert start.timestamp() == now - logs_querier.max_age
            assert end.timestamp() == now

    def test_query_logs_no_previous_ids(
        self,
        logs_querier: LogsQuerier,
        logs: Sequence[Log],
    ) -> None:
        assert list(logs_querier.query_logs()) == logs
        assert logs_querier.id_store.read() == frozenset({"1", "2", "3", "4"})

    def test_query_logs_with_previous_ids(
        self,
        logs_querier: LogsQuerier,
        logs: Sequence[Log],
    ) -> None:
        logs_querier.id_store.write(["1", "2", "5"])
        assert list(logs_querier.query_logs()) == logs[-2:]
        assert logs_querier.id_store.read() == frozenset({"1", "2", "3", "4"})


@pytest.mark.parametrize(
    ["raw_translator", "message_text"],
    [
        pytest.param([], "", id="default"),
        pytest.param(["S:service", "H:host"], " S=app, H=cmk", id="multiple keys"),
        pytest.param(["KEY:foobar"], "", id="none existing key"),
        pytest.param(["N:attributes.test.baz"], " N=fun", id="nested key"),
        pytest.param(["Number:attributes.number"], " Number=42", id="numerical"),
        pytest.param(
            ["object:attributes.object"],
            " object=[1, 2, 3, cmk: [4, 5, 6], Checkmk]",
            id="composite object",
        ),
    ],
)
def test_log_to_syslog_message(raw_translator: Sequence[str], message_text: str) -> None:
    translator = list(LogMessageElement.from_arg(el) for el in raw_translator)
    message = repr(
        _log_to_syslog_message(
            Log(
                id="hello",
                attributes=LogAttributes(
                    attributes={
                        "test": {"baz": "fun"},
                        "number": 42,
                        "object": [1, 2, 3, {"cmk": [4, 5, 6]}, "Checkmk"],
                    },
                    host="cmk",
                    service="app",
                    status="error",
                    tags=["hello"],
                    timestamp="2022-09-07T11:01:54.812Z",
                    message="msg",
                ),
            ),
            facility=0,
            service_level=0,
            translator=translator,
        )
    )
    assert (
        message
        == f"<3>1 2022-09-07T11:01:54.812000+00:00 cmk app - - [Checkmk@18662]{message_text}"
    )
