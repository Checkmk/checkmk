#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.mongodb_cluster import (
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
                ("jumboDB1", {}),
                ("noColDB1", {}),
                ("shardedDB1", {}),
                ("unshardedDB2", {}),
            ],
        ),
    ],
)
def test_discover_mongodb_cluster_databases_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mongodb_cluster databases regression test."""
    parsed = parse_mongodb_cluster(string_table)
    result = list(discover_mongodb_cluster_databases(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
                ("jumboDB1.collections1", {}),
                ("shardedDB1.collections1", {}),
                ("shardedDB1.collections2", {}),
                ("unshardedDB2.collections1", {}),
                ("unshardedDB2.collections2", {}),
            ],
        ),
    ],
)
def test_discover_mongodb_cluster_collections_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mongodb_cluster collections regression test."""
    parsed = parse_mongodb_cluster(string_table)
    result = list(discover_mongodb_cluster_shards(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"balancer":{"numBalancerRounds":26,"balancer_enabled":true,"mode":"full","inBalancerRound":false}}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_mongodb_cluster_balancer_regression(
    string_table: StringTable, expected_discoveries: Sequence[tuple[None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mongodb_cluster balancer regression test."""
    parsed = parse_mongodb_cluster(string_table)
    result = list(discover_mongodb_cluster_balancer(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
    """Test check function for mongodb_cluster databases regression test."""
    parsed = parse_mongodb_cluster(string_table)
    result = list(check_mongodb_cluster_databases(item, params, parsed))

    # Check that we get the expected number of results
    assert len(result) == 3

    # Check that all expected messages are present
    messages = [str(msg) for _, msg, *_ in result]
    for expected_check in expected_checks:
        assert any(expected_check in msg for msg in messages), (
            f"Expected '{expected_check}' not found in {messages}"
        )


@pytest.mark.parametrize(
    "item, params, string_table, expected_collection_type",
    [
        (
            None,
            {},
            [['{"balancer":{"balancer_enabled":true}}']],
            "enabled",
        ),
        (
            None,
            {},
            [['{"balancer":{"balancer_enabled":false}}']],
            "disabled",
        ),
    ],
)
def test_check_mongodb_cluster_balancer_regression(
    item: None, params: Mapping[str, Any], string_table: StringTable, expected_collection_type: str
) -> None:
    """Test check function for mongodb_cluster balancer regression test."""
    parsed = parse_mongodb_cluster(string_table)
    result = list(check_mongodb_cluster_balancer(item, params, parsed))

    # Check that we get a result
    assert len(result) >= 1

    # Check that the balancer status is as expected
    messages = [str(msg) for _, msg, *_ in result]
    assert any(f"Balancer: {expected_collection_type}" in msg for msg in messages), (
        f"Expected 'Balancer: {expected_collection_type}' not found in {messages}"
    )
