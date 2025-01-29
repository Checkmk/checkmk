#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

import cmk.plugins.collection.agent_based.graylog_streams as gs
from cmk.agent_based.v2 import Metric, Result, State

STRING_TABLE_NO_STREAMS: Final = [['{"total": 5, "streams": []}']]


STRING_TABLE: Final = [
    [
        '{"total": 5, "streams": [{"remove_matches_from_default_stream": false, "is_default":'
        ' false, "index_set_id": "5da58758e2847e0602771f2a", "description": "logins",'
        ' "alert_conditions": [], "rules": [], "outputs": [], "created_at":'
        ' "2019-10-21T11:32:54.371Z", "title": "Logins", "disabled": false, "content_pack": null,'
        ' "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails": [],'
        ' "users": []}, "id": "5dad97665bc77407a731e7dc"}, {"remove_matches_from_default_stream":'
        ' false, "is_default": false, "index_set_id": "5d64cceecaba8d12890fdf47", "description":'
        ' "dfh", "alert_conditions": [], "rules": [], "outputs": [], "created_at":'
        ' "2019-10-30T19:45:31.792Z", "title": "shsdfhg", "disabled": false, "content_pack": null,'
        ' "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails": [],'
        ' "users": []}, "id": "5db9e85b9a74aa6ccbb8e1b0"}, {"remove_matches_from_default_stream":'
        ' false, "is_default": true, "index_set_id": "5d64cceecaba8d12890fdf47", "description":'
        ' "Stream containing all messages", "alert_conditions": [], "rules": [], "outputs": [],'
        ' "created_at": "2019-08-27T06:25:50.570Z", "title": "All messages", "disabled": false,'
        ' "content_pack": null, "matching_type": "AND", "creator_user_id": "local:admin",'
        ' "alert_receivers": {"emails": [], "users": []}, "id": "000000000000000000000001"},'
        ' {"remove_matches_from_default_stream": true, "is_default": false, "index_set_id":'
        ' "5da58758e2847e0602771f28", "description": "Stream containing all events created by'
        ' Graylog", "alert_conditions": [], "rules": [{"description": "", "stream_id":'
        ' "000000000000000000000002", "value": ".*", "inverted": false, "field": ".*", "type": 2,'
        ' "id": "5dad59d65bc77407a731a2fc"}], "outputs": [], "created_at":'
        ' "2019-10-15T08:46:16.321Z", "title": "All events", "disabled": false, "content_pack":'
        ' null, "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails":'
        ' [], "users": []}, "id": "000000000000000000000002"},'
        ' {"remove_matches_from_default_stream": true, "is_default": false, "index_set_id":'
        ' "5da58758e2847e0602771f2a", "description": "Stream containing all system events'
        ' created by Graylog", "alert_conditions": [], "rules": [], "outputs": [], "created_at":'
        ' "2019-10-15T08:46:16.327Z", "title": "All system events", "disabled": false,'
        ' "content_pack": null, "matching_type": "AND", "creator_user_id": "admin",'
        ' "alert_receivers": {"emails": [], "users": []}, "id": "000000000000000000000003"}]}'
    ]
]


@pytest.fixture(name="section_no_streams", scope="module")
def _get_section_no_streams() -> gs.Section:
    return gs.parse_graylog_streams(STRING_TABLE_NO_STREAMS)


@pytest.fixture(name="section", scope="module")
def _get_section() -> gs.Section:
    return gs.parse_graylog_streams(STRING_TABLE)


def test_discover_no_streams_discovers(section_no_streams: gs.Section) -> None:
    assert list(gs.discovery_graylog_streams(section_no_streams))


def test_check_no_streams(section_no_streams: gs.Section) -> None:
    assert list(gs.check_graylog_streams({}, section_no_streams)) == [
        Result(state=State.WARN, summary="Number of streams: 0"),
    ]


def test_check_streams(section: gs.Section) -> None:
    assert list(gs.check_graylog_streams({}, section)) == [
        Result(state=State.OK, summary="Number of streams: 5"),
        Metric("num_streams", 5),
        Result(state=State.OK, notice="Stream: All events"),
        Result(state=State.OK, summary="Stream: All messages (default)"),
        Result(state=State.OK, notice="Stream: All system events"),
        Result(state=State.OK, notice="Stream: Logins"),
        Result(state=State.OK, notice="Stream: shsdfhg"),
    ]
