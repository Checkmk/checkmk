#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.postgres.agent_based.postgres_conn_time import (
    check_postgres_conn_time,
    discover_postgres_conn_time,
    parse_postgres_conn_time,
)


def test_instances_are_upper_cased_and_first_value_wins() -> None:
    assert parse_postgres_conn_time([["0.1"], ["[[[foobar]]]"], ["0.063"], ["0.5"]]) == {
        "": 0.1,
        "FOOBAR": 0.063,
    }


def test_every_instance_is_discovered() -> None:
    assert list(discover_postgres_conn_time({"FOO": 0.1, "BAR": 0.063})) == [
        Service(item="FOO"),
        Service(item="BAR"),
    ]


def test_connection_time_is_reported() -> None:
    assert list(check_postgres_conn_time("FOOBAR", {"FOOBAR": 0.063})) == [
        Result(state=State.OK, summary="0.063 seconds"),
        Metric("connection_time", 0.063),
    ]


def test_missing_instance_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_postgres_conn_time("FOOBAR", {}))
