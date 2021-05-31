#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.special_agents import agent_datadog
from cmk.special_agents.agent_datadog import (
    _to_syslog_message,
    DatadogAPI,
    EventsQuerier,
    MonitorsQuerier,
    parse_arguments,
)


def test_parse_arguments() -> None:
    parse_arguments([
        'testhost',
        '12345',
        'powerg',
        'api.datadoghq.eu',
        '--monitor_tags',
        't1',
        't2',
        '--monitor_monitor_tags',
        'mt1',
        'mt2',
        '--event_tags',
        't3',
        't4',
        '--event_tags_show',
        '.*',
        '--event_syslog_facility',
        '1',
        '--event_syslog_priority',
        '1',
        '--event_service_level',
        '0',
        '--event_add_text',
        '--sections',
        'monitors',
        'events',
    ])


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
                'name': 'monitor1',
            },
            {
                'name': 'monitor2',
            },
            {
                'name': 'monitor3',
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

        assert list(MonitorsQuerier(datadog_api).query_monitors(
            [],
            [],
        )) == monitors_data


class TestEventsQuerier:
    @pytest.fixture(name="events_querier")
    def fixture_events_querier(
        self,
        datadog_api: DatadogAPI,
    ) -> EventsQuerier:
        return EventsQuerier(
            datadog_api,
            "host_name",
        )

    @pytest.fixture(name="now")
    def fixture_now(self) -> int:
        return 1601310544

    @pytest.fixture(name="time.time")
    def fixture_time(
        self,
        monkeypatch: MonkeyPatch,
        now: int,
    ) -> None:
        monkeypatch.setattr(
            agent_datadog.time,
            "time",
            lambda: now,
        )

    @pytest.mark.usefixtures("time.time")
    def test_events_query_time_range_no_previous_timestamp(
        self,
        events_querier: EventsQuerier,
        now: int,
    ) -> None:
        assert events_querier._events_query_time_range() == (
            now - 3600,
            now,
        )

    @pytest.mark.usefixtures("time.time")
    def test_events_query_time_range_too_old_previous_timestamp(
        self,
        events_querier: EventsQuerier,
        now: int,
    ) -> None:
        events_querier._store_events_timestamp(now - 7200)
        assert events_querier._events_query_time_range() == (
            now - 3600,
            now,
        )

    @pytest.mark.usefixtures("time.time")
    def test_events_query_time_range_ok_previous_timestamp(
        self,
        events_querier: EventsQuerier,
        now: int,
    ) -> None:
        last_timestamp = now - 120
        events_querier._store_events_timestamp(last_timestamp)
        assert events_querier._events_query_time_range() == (
            last_timestamp,
            now,
        )

    @pytest.mark.usefixtures("time.time")
    def test_query_events(
        self,
        monkeypatch: MonkeyPatch,
        events_querier: EventsQuerier,
        now: int,
    ) -> None:
        # note: this data is of course incomplete, but sufficient for this test
        events_data = [
            {
                'title': 'event1',
            },
            {
                'title': 'event2',
            },
            {
                'title': 'event3',
            },
        ]

        def patch_get_request_json_decoded(_api_endpoint, params):
            if params["page"] == 0:
                return {"events": events_data}
            if params["page"] == 1:
                return {"events": []}
            raise RuntimeError

        monkeypatch.setattr(
            events_querier._datadog_api,
            "get_request_json_decoded",
            patch_get_request_json_decoded,
        )

        assert list(events_querier.query_events([])) == events_data
        assert events_querier._read_last_events_timestamp() == now


def test_to_syslog_message() -> None:
    assert repr(
        _to_syslog_message(
            {
                'date_happened': 1618216122,
                'alert_type': 'info',
                'is_aggregate': False,
                'title': 'something bad happened',
                'url': '/event/event?id=5938350476538858876',
                'text': 'Abandon ship\n, abandon ship!',
                'tags': [
                    'ship:enterprise',
                    'location:alpha_quadrant',
                    'priority_one',
                ],
                'comments': [],
                'device_name': None,
                'priority': 'normal',
                'source': 'main bridge',
                'host': 'starbase 3',
                'resource': '/api/v1/events/5938350476538858876',
                'id': 5938350476538858876,
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
    ) == '<9>1 2021-04-12T08:28:42+00:00 - - - - [Checkmk@18662 host="starbase 3" application="main bridge"] something bad happened, Tags: ship:enterprise, priority_one, Text: Abandon ship ~ , abandon ship!'
