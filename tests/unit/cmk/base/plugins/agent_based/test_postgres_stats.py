#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Any, Dict

from cmk.base.plugins.agent_based import postgres_stats
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResults, Result, Service, State

NOW = 1489840000

SECTION = {
    "adwebconnect": [
        {
            "atime": "1488881726",
            "sname": "public",
            "tname": "serveraktion",
            "vtime": "1488881726",
        },
        {
            "atime": "-1",
            "sname": "pg_catalog",
            "tname": "pg_statistic",
            "vtime": "1488882719",
        },
        {
            "atime": "1489001316",
            "sname": "public",
            "tname": "auftrag",
            "vtime": "1489001316",
        },
        {
            "atime": "-1",
            "sname": "public",
            "tname": "anrede",
            "vtime": "-1",
        },
        {
            "atime": "",
            "sname": "public",
            "tname": "auftrag_mediadaten",
            "vtime": "-1",
        },
    ],
    "postgres": [
        {
            "atime": "-1",
            "sname": "pg_catalog",
            "tname": "pg_statistic",
            "vtime": "-1",
        },
    ],
}


def test_discovery():
    assert list(postgres_stats.discover_postgres_stats(SECTION)) == [
        Service(item="VACUUM adwebconnect"),
        Service(item="ANALYZE adwebconnect"),
        Service(item="VACUUM postgres"),
        Service(item="ANALYZE postgres"),
    ]


def test_check_postgres_stats_no_data():
    assert list(
        postgres_stats._check_postgres_stats(
            item="ANALYZE this",
            params={},
            section=SECTION,
            value_store={},
            now=NOW,
        )
    ) == [IgnoreResults("Login into database failed")]


def test_check_postgres_stats_empty_data():
    item = "ANALYZE this"
    assert list(
        postgres_stats._check_postgres_stats(
            item=item,
            params={},
            section={"this": []},
            value_store={},
            now=NOW,
        )
    ) == list(postgres_stats._check_never_checked("", [], {}, {}, NOW))


def test_check_postgres_stats_oldest_table():
    item = "ANALYZE adwebconnect"
    assert list(
        postgres_stats._check_postgres_stats(
            item=item,
            params={},
            section=SECTION,
            value_store={},
            now=NOW,
        )
    ) == [
        Result(state=State.OK, summary="Table: serveraktion"),
        Result(state=State.OK, summary="Not analyzed for: 11 days 2 hours"),
    ] + list(
        postgres_stats._check_never_checked(
            "analyzed", ["anrede", "auftrag_mediadaten"], {}, {}, NOW
        )
    )


def _test_never_checked_nothing():
    value_store: Dict[str, Any] = {}
    assert list(postgres_stats._check_never_checked("", [], {}, value_store, NOW)) == [
        Result(state=State.OK, summary="No never checked tables"),
    ]

    assert value_store["item"] == NOW


def _test_never_checked_tables_never_seen():
    value_store: Dict[str, Any] = {}
    assert list(
        postgres_stats._check_never_checked(
            "loved",
            list("ABCDE"),
            {},
            value_store,
            NOW,
        )
    ) == [
        Result(
            state=State.OK,
            summary="5 tables were never loved: A / B / C (first 3 shown)",
            details="5 tables were never loved: A / B / C / D / E",
        ),
    ]

    assert value_store["item"] == NOW


def _test_never_checked_tables_warn():
    value_store: Dict[str, Any] = {"item": NOW - 24.23 * 3600}
    assert list(
        postgres_stats._check_never_checked(
            "loved",
            list("AB"),
            {"never_analyze_vacuum": (10, 25 * 3600)},
            value_store,
            NOW,
        )
    ) == [
        Result(state=State.OK, summary="2 tables were never loved: A / B"),
        Result(
            state=State.WARN,
            summary="Never loved tables for: 1 day 23 minutes",
        ),
    ]

    assert value_store == {"item": NOW - 24.23 * 3600}
