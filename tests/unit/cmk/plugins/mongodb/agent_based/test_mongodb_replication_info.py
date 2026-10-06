#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.mongodb.agent_based.mongodb_replication_info import (
    check_mongodb_replication_info,
    discover_mongodb_replication_info,
    parse_mongodb_replication_info,
)

SECTION = parse_mongodb_replication_info(
    [
        [
            (
                '{"tFirst": 1566891670, "tLast": 1566895270, "now": 1568796109,'
                ' "usedBytes": 9765922, "logSizeBytes": 16830742272}'
            )
        ]
    ]
)


def test_empty_section_is_not_discovered() -> None:
    assert not list(discover_mongodb_replication_info(parse_mongodb_replication_info([])))


def test_single_service_is_discovered() -> None:
    assert list(discover_mongodb_replication_info(SECTION)) == [Service()]


def test_oplog_usage_and_time_window_are_reported() -> None:
    results = list(check_mongodb_replication_info(SECTION))

    assert results[:2] + results[3:] == [
        Result(state=State.OK, summary="Oplog size: 9.31 MiB of 15.7 GiB used"),
        Result(
            state=State.OK,
            summary="Time difference: 1 hour 0 minutes between the first and last operation on oplog",
        ),
        Metric("mongodb_replication_info_log_size", 16830742272),
        Metric("mongodb_replication_info_used", 9765922),
        Metric("mongodb_replication_info_time_diff", 3600),
    ]


def test_details_list_oplog_figures() -> None:
    details = list(check_mongodb_replication_info(SECTION))[2]

    assert isinstance(details, Result)
    assert {
        "Operations log (oplog):",
        "- Total amount of space allocated: 15.7 GiB",
        "- Total amount of space currently used: 9.31 MiB",
        "- Difference between the first and last operation: 1 hour 0 minutes",
    } <= set(details.details.splitlines())


def test_missing_values_are_rendered_as_not_available() -> None:
    results = list(check_mongodb_replication_info({"tFirst": None, "tLast": None}))

    assert results[:2] + results[3:] == [
        Result(state=State.OK, summary="Oplog size: n/a of n/a used"),
        Result(state=State.OK, summary="Time difference: n/a"),
        Metric("mongodb_replication_info_log_size", 0),
        Metric("mongodb_replication_info_used", 0),
        Metric("mongodb_replication_info_time_diff", 0),
    ]
