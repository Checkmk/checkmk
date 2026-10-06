#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.postgres.agent_based.postgres_bloat import (
    check_postgres_bloat,
    discover_postgres_bloat,
)
from cmk.plugins.postgres.lib import parse_dbs

SECTION = parse_dbs(
    [
        ["[[[foobar]]]"],
        ["[databases_start]"],
        ["postgres"],
        ["testdb"],
        ["[databases_end]"],
        [
            "db",
            "schemaname",
            "tablename",
            "tups",
            "pages",
            "otta",
            "tbloat",
            "wastedpages",
            "wastedbytes",
            "wastedsize",
            "iname",
            "itups",
            "ipages",
            "iotta",
            "ibloat",
            "wastedipages",
            "wastedibytes",
            "wastedisize",
            "totalwastedbytes",
        ],
        [
            "postgres",
            "pg_catalog",
            "pg_amop",
            "403",
            "4",
            "3",
            "1.3",
            "1",
            "8192",
            "8192",
            "pg_amop_oid_index",
            "403",
            "4",
            "2",
            "2.0",
            "2",
            "16384",
            "16384",
            "24576",
        ],
        [
            "postgres",
            "pg_catalog",
            "pg_amproc",
            "291",
            "3",
            "2",
            "1.5",
            "1",
            "4096",
            "4096",
            "pg_amproc_fam_proc_index",
            "291",
            "4",
            "2",
            "1.0",
            "2",
            "32768",
            "32768",
            "36864",
        ],
    ]
)


def test_instance_name_prefixes_database_item() -> None:
    assert set(SECTION) == {"FOOBAR/postgres", "FOOBAR/testdb"}


def test_only_databases_with_data_are_discovered() -> None:
    assert list(discover_postgres_bloat(SECTION)) == [Service(item="FOOBAR/postgres")]


def test_without_violations_maxima_and_totals_are_reported() -> None:
    assert list(
        check_postgres_bloat(
            "FOOBAR/postgres",
            {"table_bloat_perc": (180.0, 200.0), "index_bloat_perc": (180.0, 200.0)},
            SECTION,
        )
    ) == [
        Result(state=State.OK, summary="Maximum table bloat at pg_amproc: 1.50%"),
        Result(state=State.OK, summary="Maximum wasted tablespace at pg_amop: 8.00 KiB"),
        Result(state=State.OK, summary="Maximum index bloat at pg_amop: 2.00%"),
        Result(state=State.OK, summary="Maximum wasted indexspace at pg_amproc: 32.0 KiB"),
        Result(state=State.OK, summary="Summary of top 2 wasted tablespace: 12.0 KiB"),
        Metric("tablespace_wasted", 12288),
        Result(state=State.OK, summary="Summary of top 2 wasted indexspace: 48.0 KiB"),
        Metric("indexspace_wasted", 49152),
    ]


def test_violated_levels_are_reported_per_table_followed_by_levels() -> None:
    results = list(
        check_postgres_bloat(
            "FOOBAR/postgres",
            {"index_bloat_perc": (1.5, 2.0), "table_bloat_abs": (4096, 8192)},
            SECTION,
        )
    )

    assert results[:4] == [
        Result(state=State.CRIT, summary="pg_amop wasted table bytes: 8.00 KiB (too high)"),
        Result(state=State.CRIT, summary="pg_amop index bloat: 2.0% (too high)"),
        Result(state=State.WARN, summary="pg_amproc wasted table bytes: 4.00 KiB (too high)"),
        Result(
            state=State.OK,
            summary="Levels: Table Abs (4.00 KiB/8.00 KiB) Index Perc (2%/2%)",
        ),
    ]


def test_warn_levels_on_table_bloat_and_wasted_index_bytes() -> None:
    results = list(
        check_postgres_bloat(
            "FOOBAR/postgres",
            {"table_bloat_perc": (1.4, 5.0), "index_bloat_abs": (20000, 40000)},
            SECTION,
        )
    )

    assert results[:3] == [
        Result(state=State.WARN, summary="pg_amproc table bloat: 1.5% (too high)"),
        Result(state=State.WARN, summary="pg_amproc wasted index bytes: 32.0 KiB (too high)"),
        Result(
            state=State.OK,
            summary="Levels: Table Perc (1%/5%) Index Abs (19.5 KiB/39.1 KiB)",
        ),
    ]


def test_database_without_data_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_postgres_bloat("FOOBAR/testdb", {}, SECTION))
