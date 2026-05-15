#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, StringTable
from cmk.plugins.mongodb.agent_based.mongodb_cluster import (
    check_mongodb_cluster_balancer,
    check_mongodb_cluster_databases,
    discover_mongodb_cluster_balancer,
    discover_mongodb_cluster_databases,
    discover_mongodb_cluster_shards,
    parse_mongodb_cluster,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"shards":{"shard03":{"host":"shard03/shard03a:27020,shard03b:27020","state":1},"shard02":{"host":"shard02/shard02a:27019,shard02b:27019","state":1},"shard01":{"host":"shard01/shard01a:27018,shard01b:27018","state":1}},"balancer":{"numBalancerRounds":26,"balancer_enabled":true,"mode":"full","inBalancerRound":false},"databases":{"unshardedDB2":{"collstats":{"collections1":{"count":3000,"storageSize":61440},"collections2":{"count":666,"storageSize":24576}},"collections":["collections1","collections2"],"primary":"shard01","partitioned":false},"shardedDB1":{"collstats":{"collections1":{"count":10000,"storageSize":307200},"collections2":{"count":10000,"storageSize":286720}},"collections":["collections1","collections2"],"primary":"shard01","partitioned":true},"jumboDB1":{"collstats":{"collections1":{"count":0,"storageSize":12288}},"collections":["collections1"],"primary":"shard01","partitioned":true},"noColDB1":{"collstats":{},"collections":[],"primary":"shard01","partitioned":false}}}'
                ]
            ],
            [
                Service(item="jumboDB1"),
                Service(item="noColDB1"),
                Service(item="shardedDB1"),
                Service(item="unshardedDB2"),
            ],
        ),
    ],
)
def test_discover_mongodb_cluster_databases_regression(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_mongodb_cluster(string_table)
    result = list(discover_mongodb_cluster_databases(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"databases":{"unshardedDB2":{"collections":["collections1","collections2"]},"shardedDB1":{"collections":["collections1","collections2"]},"jumboDB1":{"collections":["collections1"]},"noColDB1":{"collections":[]}}}'
                ]
            ],
            [
                Service(item="jumboDB1.collections1"),
                Service(item="shardedDB1.collections1"),
                Service(item="shardedDB1.collections2"),
                Service(item="unshardedDB2.collections1"),
                Service(item="unshardedDB2.collections2"),
            ],
        ),
    ],
)
def test_discover_mongodb_cluster_collections_regression(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_mongodb_cluster(string_table)
    result = list(discover_mongodb_cluster_shards(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "string_table",
    [
        [
            [
                '{"balancer":{"numBalancerRounds":26,"balancer_enabled":true,"mode":"full","inBalancerRound":false}}'
            ]
        ],
    ],
)
def test_discover_mongodb_cluster_balancer_regression(string_table: StringTable) -> None:
    parsed = parse_mongodb_cluster(string_table)
    result = list(discover_mongodb_cluster_balancer(parsed))
    assert result == [Service()]


@pytest.mark.parametrize(
    "item, params, string_table, expected_checks",
    [
        (
            "noColDB1",
            {},
            [
                [
                    '{"databases":{"noColDB1":{"collstats":{},"collections":[],"primary":"shard01","partitioned":false}}}'
                ]
            ],
            ["Partitioned: false", "Collections: 0", "Primary: shard01"],
        ),
        (
            "shardedDB1",
            {},
            [
                [
                    '{"databases":{"shardedDB1":{"collections":["collections1","collections2"],"primary":"shard01","partitioned":true}}}'
                ]
            ],
            ["Partitioned: true", "Collections: 2", "Primary: shard01"],
        ),
    ],
)
def test_check_mongodb_cluster_databases_regression(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_checks: list[str]
) -> None:
    parsed = parse_mongodb_cluster(string_table)
    result = list(check_mongodb_cluster_databases(item, params, parsed))

    assert len(result) == 3

    messages = [r.summary for r in result if isinstance(r, Result)]
    for expected_check in expected_checks:
        assert any(expected_check in msg for msg in messages), (
            f"Expected '{expected_check}' not found in {messages}"
        )


@pytest.mark.parametrize(
    "string_table, expected_collection_type",
    [
        (
            [['{"balancer":{"balancer_enabled":true}}']],
            "enabled",
        ),
        (
            [['{"balancer":{"balancer_enabled":false}}']],
            "disabled",
        ),
    ],
)
def test_check_mongodb_cluster_balancer_regression(
    string_table: StringTable, expected_collection_type: str
) -> None:
    parsed = parse_mongodb_cluster(string_table)
    result = list(check_mongodb_cluster_balancer(parsed))

    assert len(result) >= 1

    messages = [r.summary for r in result if isinstance(r, Result)]
    assert any(f"Balancer: {expected_collection_type}" in msg for msg in messages), (
        f"Expected 'Balancer: {expected_collection_type}' not found in {messages}"
    )
