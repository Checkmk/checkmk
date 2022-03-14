#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

import pytest
from pytest import MonkeyPatch

from cmk.special_agents import agent_datadog
from cmk.special_agents.agent_datadog import (
    _to_syslog_message,
    DatadogAPI,
    DatadogAPIResponse,
    EventsQuerier,
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
            "--sections",
            "monitors",
            "events",
        ]
    )


@pytest.fixture(name="datadog_api")
def fixture_datadog_api() -> DatadogAPI:
    return DatadogAPI(
        "api_host",
        "api_key",
        "app_key",
    )


class TestMonitorsQuerier:
    def test_query_monitors(
        self,
        monkeypatch: MonkeyPatch,
        datadog_api: DatadogAPI,
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

        def patch_get_request_json_decoded(_api_endpoint, params):
            if params["page"] == 0:
                return monitors_data
            if params["page"] == 1:
                return []
            raise RuntimeError

        monkeypatch.setattr(
            datadog_api,
            "get_request_json_decoded",
            patch_get_request_json_decoded,
        )

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
    @pytest.fixture(name="events_querier")
    def fixture_events_querier(
        self,
        datadog_api: DatadogAPI,
    ) -> EventsQuerier:
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
        monkeypatch.setattr(
            agent_datadog.time,
            "time",
            lambda: now,
        )
        assert events_querier._events_query_time_range() == (
            now - events_querier._max_age,
            now,
        )

    @pytest.fixture(name="events")
    def fixture_events(self) -> Sequence[DatadogAPIResponse]:
        # note: this data is of course incomplete, but sufficient for this test
        return [
            {
                "title": "event1",
                "id": 1,
            },
            {
                "title": "event2",
                "id": 2,
            },
            {
                "title": "event3",
                "id": 3,
            },
        ]

    @pytest.fixture(name="patch_get_request")
    def fixture_patch_get_request(
        self,
        monkeypatch: MonkeyPatch,
        events_querier: EventsQuerier,
        events: Sequence[DatadogAPIResponse],
    ) -> None:
        def patch_get_request_json_decoded(_api_endpoint, params):
            if params["page"] == 0:
                return {"events": events}
            if params["page"] == 1:
                return {"events": []}
            raise RuntimeError

        monkeypatch.setattr(
            events_querier._datadog_api,
            "get_request_json_decoded",
            patch_get_request_json_decoded,
        )

    @pytest.mark.usefixtures("patch_get_request")
    def test_query_events_no_previous_ids(
        self,
        events_querier: EventsQuerier,
        events: Sequence[DatadogAPIResponse],
    ) -> None:
        assert list(events_querier.query_events([])) == events
        assert events_querier._read_last_event_ids() == frozenset({1, 2, 3})

    @pytest.mark.usefixtures("patch_get_request")
    def test_query_events_with_previous_ids(
        self,
        events_querier: EventsQuerier,
        events: Sequence[DatadogAPIResponse],
    ) -> None:
        events_querier._store_last_event_ids([1, 2, 5])
        assert list(events_querier.query_events([])) == events[-1:]
        assert events_querier._read_last_event_ids() == frozenset({1, 2, 3})


def test_to_syslog_message() -> None:
    assert (
        repr(
            _to_syslog_message(
                {
                    "date_happened": 1618216122,
                    "alert_type": "info",
                    "is_aggregate": False,
                    "title": "something bad happened",
                    "url": "/event/event?id=5938350476538858876",
                    "text": "Abandon ship\n, abandon ship!",
                    "tags": [
                        "ship:enterprise",
                        "location:alpha_quadrant",
                        "priority_one",
                    ],
                    "comments": [],
                    "device_name": None,
                    "priority": "normal",
                    "source": "main bridge",
                    "host": "starbase 3",
                    "resource": "/api/v1/events/5938350476538858876",
                    "id": 5938350476538858876,
                },
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
