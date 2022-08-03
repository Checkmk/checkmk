#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from tests.testlib import on_time

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

_STRING_TABLE = [
    [
        '{"admin": {"collections": ["system.users", "system.version", "system.keys"], "collstats": {"system.users": {"ns": "admin.system.users", "size": 1195, "count": 4, "avgObjSize": 298, "storageSize": 36864, "capped": false, "nindexes": 2, "totalIndexSize": 73728, "indexSizes": {"_id_": 36864, "user_1_db_1": 36864}, "ok": 1.0, "indexStats": [{"name": "user_1_db_1", "key": {"user": 1, "db": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.828Z"}}}, {"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.828Z"}}}]}, "system.version": {"ns": "admin.system.version", "size": 104, "count": 2, "avgObjSize": 52, "storageSize": 16384, "capped": false, "nindexes": 1, "totalIndexSize": 16384, "indexSizes": {"_id_": 16384}, "ok": 1.0, "indexStats": [{"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.828Z"}}}]}, "system.keys": {"ns": "admin.system.keys", "size": 1360, "count": 16, "avgObjSize": 85, "storageSize": 36864, "capped": false, "nindexes": 1, "totalIndexSize": 36864, "indexSizes": {"_id_": 36864}, "ok": 1.0, "indexStats": [{"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb03.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:30:07.827Z"}}}]}}}, "config": {"collections": ["system.sessions", "transactions"], "collstats": {"system.sessions": {"ns": "config.system.sessions", "size": 6554691, "count": 66209, "avgObjSize": 99, "storageSize": 4419584, "capped": false, "nindexes": 2, "totalIndexSize": 12488704, "indexSizes": {"_id_": 12144640, "lsidTTLIndex": 344064}, "ok": 1.0, "indexStats": [{"name": "lsidTTLIndex", "key": {"lastUse": 1}, "host": "mvgenmongodb02.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:20:08.922Z"}}}, {"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb02.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:20:08.922Z"}}}]}, "transactions": {"ns": "config.transactions", "size": 0, "count": 0, "storageSize": 4096, "capped": false, "nindexes": 1, "totalIndexSize": 4096, "indexSizes": {"_id_": 4096}, "ok": 1.0, "indexStats": [{"name": "_id_", "key": {"_id": 1}, "host": "mvgenmongodb02.pgsm.hu:27017", "accesses": {"ops": 0, "since": {"$date": "2022-08-01T01:20:08.922Z"}}}]}}}}'
    ]
]


@pytest.fixture(name="check_plugin", scope="module")
def check_plugin_fixutre(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("mongodb_collections")]


@pytest.fixture(name="section", scope="module")
def section_fixture(fix_register: FixRegister) -> Mapping[str, Any]:
    return fix_register.agent_sections[SectionName("mongodb_collections")].parse_function(
        _STRING_TABLE
    )


def test_discover_mongodb_collections(
    check_plugin: CheckPlugin,
    section: Mapping[str, Any],
) -> None:
    assert list(check_plugin.discovery_function(section)) == [
        Service(item="admin.system.users"),
        Service(item="admin.system.version"),
        Service(item="admin.system.keys"),
        Service(item="config.system.sessions"),
        Service(item="config.transactions"),
    ]


def test_check_mongodb_collections(
    check_plugin: CheckPlugin,
    section: Mapping[str, Any],
) -> None:
    with on_time(1659514516, "UTC"):
        assert list(
            check_plugin.check_function(
                item="config.system.sessions",
                params=check_plugin.check_default_parameters,
                section=section,
            )
        ) == [
            Result(state=State.OK, summary="Uncompressed size in memory: 6.25 MB"),
            Metric("mongodb_collection_size", 6554691.0),
            Result(state=State.OK, summary="Allocated for document storage: 4.21 MB"),
            Metric("mongodb_collection_storage_size", 4419584.0),
            Result(state=State.OK, summary="Total size of indexes: 11.91 MB"),
            Metric("mongodb_collection_total_index_size", 12488704.0),
            Result(state=State.OK, summary="Number of indexes: 2"),
            Result(
                state=State.OK,
                summary="10 additional details available",
                details="Collection\n- Document Count: 66209 (Number of documents in collection)\n- Object Size: 99.00 B (Average object size)\n- Collection Size: 6.25 MB (Uncompressed size in memory)\n- Storage Size: 4.21 MB (Allocated for document storage)\nIndexes:\n- Total Index Size: 11.91 MB (Total size of all indexes)\n- Number of Indexes: 2\n-- Index 'lsidTTLIndex' used 0 times since 1970-01-20 04:55:16\n-- Index '_id_' used 0 times since 1970-01-20 04:55:16",
            ),
        ]
