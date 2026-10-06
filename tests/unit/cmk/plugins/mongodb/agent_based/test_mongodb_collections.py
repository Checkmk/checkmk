#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from zoneinfo import ZoneInfo

import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.mongodb.agent_based.mongodb_collections import (
    check_mongodb_collections,
    check_plugin_mongodb_collections,
    parse_mongodb_collections,
    Section,
)

_STRING_TABLE = [
    [
        '{"admin": {"collections": ["system.users", "system.version", "system.keys"], "collstats": {"system.users": {"ns": "admin.system.users", "size": 1195, "count": 4, "avgObjSize": 298, "storageSize": 36864, "capped": false, "nindexes": 2, "totalIndexSize": 73728, "indexSizes": {"_id_": 36864, "user_1_db_1": 36864}, "ok": 1.0, "indexStats": [{"name": "user_1_db_1", "key": {"user": 1, "db": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.828Z"}}}, {"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.828Z"}}}]}, "system.version": {"ns": "admin.system.version", "size": 104, "count": 2, "avgObjSize": 52, "storageSize": 16384, "capped": false, "nindexes": 1, "totalIndexSize": 16384, "indexSizes": {"_id_": 16384}, "ok": 1.0, "indexStats": [{"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.828Z"}}}]}, "system.keys": {"ns": "admin.system.keys", "size": 1360, "count": 16, "avgObjSize": 85, "storageSize": 36864, "capped": false, "nindexes": 1, "totalIndexSize": 36864, "indexSizes": {"_id_": 36864}, "ok": 1.0, "indexStats": [{"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.827Z"}}}]}}}, "config": {"collections": ["system.sessions", "transactions"], "collstats": {"system.sessions": {"ns": "config.system.sessions", "size": 6554691, "count": 66209, "avgObjSize": 99, "storageSize": 4419584, "capped": false, "nindexes": 2, "totalIndexSize": 12488704, "indexSizes": {"_id_": 12144640, "lsidTTLIndex": 344064}, "ok": 1.0, "indexStats": [{"name": "lsidTTLIndex", "key": {"lastUse": 1}, "host": "mvgenmongodb02.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:20:08.922Z"}}}, {"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb02.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:20:08.922Z"}}}]}, "transactions": {"ns": "config.transactions", "size": 0, "count": 0, "storageSize": 4096, "capped": false, "nindexes": 1, "totalIndexSize": 4096, "indexSizes": {"_id_": 4096}, "ok": 1.0, "indexStats": [{"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb02.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:20:08.922Z"}}}]}}}}'
    ]
]


def test_discover_mongodb_collections() -> None:
    section = parse_mongodb_collections(_STRING_TABLE)
    assert list(check_plugin_mongodb_collections.discovery_function(section)) == [
        Service(item="admin.system.users"),
        Service(item="admin.system.version"),
        Service(item="admin.system.keys"),
        Service(item="config.system.sessions"),
        Service(item="config.transactions"),
    ]


def test_check_mongodb_collections() -> None:
    section = parse_mongodb_collections(_STRING_TABLE)
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("UTC"))):
        assert list(
            check_plugin_mongodb_collections.check_function(
                item="config.system.sessions",
                params=check_plugin_mongodb_collections.check_default_parameters,
                section=section,
            )
        ) == [
            Result(state=State.OK, summary="Uncompressed size in memory: 6.25 MiB"),
            Metric("mongodb_collection_size", 6554691.0),
            Result(state=State.OK, summary="Allocated for document storage: 4.21 MiB"),
            Metric("mongodb_collection_storage_size", 4419584.0),
            Result(state=State.OK, summary="Total size of indexes: 11.9 MiB"),
            Metric("mongodb_collection_total_index_size", 12488704.0),
            Result(state=State.OK, summary="Number of indexes: 2"),
            Result(
                state=State.OK,
                notice=(
                    "Collection\n"
                    "- Document Count: 66209 (Number of documents in collection)\n"
                    "- Object Size: 99 B (Average object size)\n"
                    "- Collection Size: 6.25 MiB (Uncompressed size in memory)\n"
                    "- Storage Size: 4.21 MiB (Allocated for document storage)\n\n"
                    "Indexes:\n"
                    "- Total Index Size: 11.9 MiB (Total size of all indexes)\n"
                    "- Number of Indexes: 2\n"
                    "-- Index 'lsidTTLIndex' used 0 times since 2022-08-01 01:20:08\n"
                    "-- Index '_id_' used 0 times since 2022-08-01 01:20:08"
                ),
            ),
        ]


def _collection_section(stats: dict[str, object]) -> Section:
    return {"shop": {"collstats": {"orders": stats}}}


def test_empty_string_table_parses_to_empty_section() -> None:
    assert parse_mongodb_collections([]) == {}


def test_size_levels_are_given_in_mib_and_index_levels_in_kib() -> None:
    section = _collection_section(
        {"size": 3 * 1024**2, "storageSize": 1024**2, "totalIndexSize": 3 * 1024}
    )

    results = list(
        check_mongodb_collections(
            "shop.orders", {"levels_size": (2, 4), "levels_totalIndexSize": (1, 2)}, section
        )
    )

    assert [r for r in results if isinstance(r, Result) and r.state is not State.OK] == [
        Result(
            state=State.WARN,
            summary="Uncompressed size in memory: 3.00 MiB (warn/crit at 2.00 MiB/4.00 MiB)",
        ),
        Result(
            state=State.CRIT,
            summary="Total size of indexes: 3.00 KiB (warn/crit at 1.00 KiB/2.00 KiB)",
        ),
    ]


def test_missing_size_key_stops_the_check() -> None:
    section = _collection_section({"size": 100, "totalIndexSize": 10})

    assert list(check_mongodb_collections("shop.orders", {}, section)) == [
        Result(state=State.OK, summary="Uncompressed size in memory: 100 B"),
        Metric("mongodb_collection_size", 100),
    ]


def test_non_numeric_sizes_are_skipped() -> None:
    section = _collection_section({"size": "n/a", "storageSize": "n/a", "totalIndexSize": "n/a"})

    results = list(check_mongodb_collections("shop.orders", {}, section))

    assert not [r for r in results if isinstance(r, Metric)]


def test_details_of_sharded_collection_show_distribution_and_unknown_values() -> None:
    section = _collection_section(
        {
            "size": 100,
            "storageSize": 200,
            "totalIndexSize": 10,
            "sharded": True,
            "shardsCount": 3,
            "avgObjSize": "garbage",
        }
    )

    (details,) = [
        r
        for r in check_mongodb_collections("shop.orders", {}, section)
        if isinstance(r, Result) and not r.summary
    ]

    assert details.details.splitlines() == [
        "Collection",
        "- Sharded: True (Data distributed in cluster)",
        "- Shards: 3 (Number of shards)",
        "- Chunks: n/a (Total number of chunks)",
        "- Document Count: n/a (Number of documents in collection)",
        "- Object Size: n/a (Average object size)",
        "- Collection Size: 100 B (Uncompressed size in memory)",
        "- Storage Size: 200 B (Allocated for document storage)",
        "",
        "Indexes:",
        "- Total Index Size: 10 B (Total size of all indexes)",
        "- Number of Indexes: n/a",
    ]


def test_item_without_collection_name_yields_nothing() -> None:
    assert not list(check_mongodb_collections("shop", {}, _collection_section({"size": 1})))
