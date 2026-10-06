#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.mongodb.agent_based.mongodb_cluster import (
    check_mongodb_cluster_balancer,
    check_mongodb_cluster_databases,
    check_mongodb_cluster_shards,
    discover_mongodb_cluster_balancer,
    discover_mongodb_cluster_databases,
    discover_mongodb_cluster_shards,
    parse_mongodb_cluster,
    Section,
)

_RAW_SECTION = {
    "databases": {
        "shop": {
            "partitioned": True,
            "primary": "shard01",
            "collections": ["orders", "users"],
            "collstats": {
                "orders": {
                    "sharded": True,
                    "noBalance": True,
                    "nchunks": 4,
                    "count": 1000,
                    "size": 4096,
                    "storageSize": 8192,
                    "shards": {
                        "shard01": {
                            "numberOfChunks": 2,
                            "numberOfJumbos": 2,
                            "size": 3072,
                            "count": 750,
                        },
                        "shard02": {
                            "numberOfChunks": 2,
                            "numberOfJumbos": 1,
                            "size": 1024,
                            "count": 250,
                        },
                    },
                },
                "users": {
                    "sharded": False,
                    "count": 10,
                    "size": 100,
                    "storageSize": 200,
                    "shards": {"shard01": {"numberOfChunks": 1, "size": 100, "count": 10}},
                },
            },
        },
        "empty": {"partitioned": False, "primary": "shard02", "collections": []},
    },
    "shards": {
        "shard01": {"host": "rs1/host1:27018"},
        "shard02": {"host": "rs2/host2:27018"},
    },
    "settings": {"chunkSize": 64 * 1024**2},
    "balancer": {"balancer_enabled": True},
}

SECTION = parse_mongodb_cluster([[json.dumps(_RAW_SECTION)]])


def _notice_lines(results: Iterable[object]) -> list[str]:
    (notice,) = [r for r in results if isinstance(r, Result) and not r.summary]
    return notice.details.splitlines()


def test_empty_string_table_parses_to_empty_section() -> None:
    assert parse_mongodb_cluster([]) == {}


def test_every_database_is_discovered() -> None:
    assert list(discover_mongodb_cluster_databases(SECTION)) == [
        Service(item="shop"),
        Service(item="empty"),
    ]


def test_partitioned_database_with_collections_is_ok() -> None:
    assert list(check_mongodb_cluster_databases("shop", {}, SECTION)) == [
        Result(state=State.OK, summary="Partitioned: true"),
        Result(state=State.OK, summary="Collections: 2"),
        Result(state=State.OK, summary="Primary: shard01"),
    ]


def test_database_without_collections_is_warn() -> None:
    assert list(check_mongodb_cluster_databases("empty", {}, SECTION)) == [
        Result(state=State.OK, summary="Partitioned: false"),
        Result(state=State.WARN, summary="Collections: 0"),
        Result(state=State.OK, summary="Primary: shard02"),
    ]


def test_every_collection_is_discovered_with_its_namespace() -> None:
    assert list(discover_mongodb_cluster_shards(SECTION)) == [
        Service(item="shop.orders"),
        Service(item="shop.users"),
    ]


def test_sharded_collection_reports_balancer_and_jumbo_chunks() -> None:
    results = list(
        check_mongodb_cluster_shards("shop.orders", {"levels_number_jumbo": (1, 2)}, SECTION)
    )

    assert [r for r in results if isinstance(r, Result) and r.summary] == [
        Result(state=State.OK, summary="Collection: sharded"),
        Result(state=State.OK, summary="Chunks: balanced"),
        Result(state=State.WARN, summary="Balancer: disabled"),
        Result(
            state=State.CRIT,
            summary="Jumbo: [shard01 (2 jumbo chunks), shard02 (1 jumbo chunk)]",
        ),
    ]


def test_jumbo_chunks_below_crit_are_warn() -> None:
    results = list(
        check_mongodb_cluster_shards("shop.orders", {"levels_number_jumbo": (2, 5)}, SECTION)
    )

    assert Result(state=State.WARN, summary="Jumbo: [shard01 (2 jumbo chunks)]") in results


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no levels"),
        pytest.param({"levels_number_jumbo": (5, 10)}, id="below levels"),
    ],
)
def test_jumbo_chunks_without_violated_levels_are_ok(params: dict[str, tuple[int, int]]) -> None:
    assert Result(state=State.OK, summary="Jumbo: 0") in list(
        check_mongodb_cluster_shards("shop.orders", params, SECTION)
    )


def test_sharded_collection_reports_size_document_chunk_and_jumbo_metrics() -> None:
    results = list(
        check_mongodb_cluster_shards("shop.orders", {"levels_number_jumbo": (1, 2)}, SECTION)
    )

    assert [r for r in results if isinstance(r, Metric)] == [
        Metric("mongodb_collection_size", 4096),
        Metric("mongodb_collection_storage_size", 8192),
        Metric("mongodb_document_count", 1000),
        Metric("mongodb_chunk_count", 4),
        Metric("mongodb_jumbo_chunk_count", 3, levels=(1, 2)),
    ]


def test_sharded_collection_details_show_per_shard_distribution() -> None:
    lines = _notice_lines(
        list(check_mongodb_cluster_shards("shop.orders", {"levels_number_jumbo": (1, 2)}, SECTION))
    )

    assert lines == [
        "",
        "Collection",
        "- Shards: 2",
        "- Chunks: 4 (Default chunk size: 64.0 MiB)",
        "- Docs: 1000",
        "- Size: 4.00 KiB",
        "- Storage: 8.00 KiB",
        "- Balancer: disabled",
        "",
        "Shard shard01 (primary)",
        "- Chunks: 2",
        "- Jumbos: 2",
        "- Docs: 750 (75.00%)",
        "--- per chunk: ≈ 375",
        "- Size: 3.00 KiB (75.00%)",
        "--- per chunk: ≈ 1.50 KiB",
        "- Host: rs1/host1:27018",
        "",
        "Shard shard02",
        "- Chunks: 2",
        "- Jumbos: 1",
        "- Docs: 250 (25.00%)",
        "--- per chunk: ≈ 125",
        "- Size: 1.00 KiB (25.00%)",
        "--- per chunk: ≈ 512 B",
        "- Host: rs2/host2:27018",
    ]


def test_unsharded_collection_only_reports_its_state() -> None:
    results = list(
        check_mongodb_cluster_shards("shop.users", {"levels_number_jumbo": (1, 2)}, SECTION)
    )

    assert [r for r in results if isinstance(r, Result) and r.summary] == [
        Result(state=State.OK, summary="Collection: unsharded"),
    ]


def test_unsharded_collection_details_omit_distribution_estimates() -> None:
    lines = _notice_lines(
        list(check_mongodb_cluster_shards("shop.users", {"levels_number_jumbo": (1, 2)}, SECTION))
    )

    assert lines == [
        "",
        "Collection",
        "- Shards: 1",
        "- Docs: 10",
        "- Size: 100 B",
        "- Storage: 200 B",
        "",
        "Shard shard01 (primary)",
        "- Chunks: 1",
        "- Jumbos: 0",
        "- Docs: 10",
        "- Size: 100 B",
        "- Host: rs1/host1:27018",
    ]


def test_section_without_databases_yields_nothing() -> None:
    assert not list(check_mongodb_cluster_shards("shop.orders", {}, {"balancer": {}}))


def test_balancer_is_discovered_for_non_empty_section() -> None:
    assert list(discover_mongodb_cluster_balancer(SECTION)) == [Service()]


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            {"balancer": {"balancer_enabled": True}},
            [Result(state=State.OK, summary="Balancer: enabled")],
            id="enabled",
        ),
        pytest.param(
            {"balancer": {"balancer_enabled": False}},
            [Result(state=State.CRIT, summary="Balancer: disabled")],
            id="disabled",
        ),
        pytest.param({"databases": {}}, [], id="no balancer info"),
    ],
)
def test_balancer_state_follows_enabled_flag(section: Section, expected: list[Result]) -> None:
    assert list(check_mongodb_cluster_balancer(section)) == expected
