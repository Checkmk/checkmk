#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    AzureResource,
    build_cosmosdb_databases,
    get_cosmosdb_containers,
    TagsImportPatternOption,
    UniqueHostnamesConfig,
)

from .lib import fake_azure_subscription

ACCOUNT_URI = "resourceGroups/rg/providers/Microsoft.DocumentDB/databaseAccounts/acc"


class _FakeApiClient:
    def __init__(self, responses: Mapping[str, Mapping[str, object]]) -> None:
        self._responses = responses

    async def get_async(self, uri_end: str, **kwargs: object) -> object:
        response = self._responses[uri_end]
        return response[str(kwargs["key"])] if "key" in kwargs else response


def _account() -> AzureResource:
    return AzureResource(
        {
            "id": f"/subscriptions/mock_subscription_id/{ACCOUNT_URI}",
            "name": "acc",
            "type": "Microsoft.DocumentDB/databaseAccounts",
            "location": "westeurope",
            "tags": {},
        },
        TagsImportPatternOption.import_all,
        fake_azure_subscription(),
        UniqueHostnamesConfig(),
    )


def _metric(database_name: str, container_name: str | None = None) -> Mapping[str, object]:
    metadata = {"databasename": database_name}
    if container_name is not None:
        metadata["collectionname"] = container_name
    return {
        "name": "TotalRequests",
        "aggregation": "count",
        "value": 3,
        "unit": "count",
        "cmk_metric_alias": "count_TotalRequestsdb",
        "metadata_mapping": metadata,
    }


@pytest.mark.asyncio
async def test_sql_account_lists_containers_of_every_database() -> None:
    api_client = _FakeApiClient(
        {
            ACCOUNT_URI: {"kind": "GlobalDocumentDB", "properties": {"capabilities": []}},
            f"{ACCOUNT_URI}/sqlDatabases": {"value": [{"name": "db1"}, {"name": "db2"}]},
            f"{ACCOUNT_URI}/sqlDatabases/db1/containers": {
                "value": [{"name": "c1"}, {"name": "c2"}]
            },
            f"{ACCOUNT_URI}/sqlDatabases/db2/containers": {"value": []},
        }
    )

    containers = await get_cosmosdb_containers(api_client, _account())  # type: ignore[arg-type]

    assert containers == {"db1": ["c1", "c2"], "db2": []}


@pytest.mark.asyncio
async def test_mongodb_account_lists_collections() -> None:
    api_client = _FakeApiClient(
        {
            ACCOUNT_URI: {"kind": "MongoDB", "properties": {"capabilities": []}},
            f"{ACCOUNT_URI}/mongodbDatabases": {"value": [{"name": "db1"}]},
            f"{ACCOUNT_URI}/mongodbDatabases/db1/collections": {"value": [{"name": "coll1"}]},
        }
    )

    containers = await get_cosmosdb_containers(api_client, _account())  # type: ignore[arg-type]

    assert containers == {"db1": ["coll1"]}


@pytest.mark.asyncio
async def test_account_of_unsupported_api_has_no_listing() -> None:
    api_client = _FakeApiClient(
        {
            ACCOUNT_URI: {
                "kind": "GlobalDocumentDB",
                "properties": {"capabilities": [{"name": "EnableCassandra"}]},
            },
        }
    )

    containers = await get_cosmosdb_containers(api_client, _account())  # type: ignore[arg-type]

    assert containers is None


def test_listed_database_becomes_resource_with_its_containers() -> None:
    (database,) = build_cosmosdb_databases(
        _account(), {"db1": ["c1", "c2"]}, [], UniqueHostnamesConfig()
    )

    assert database.name == "acc_db1"
    assert database.info["specific_info"] == {"containers": ["c1", "c2"]}
    assert database.labels["cosmosdb_account"] == "acc"
    assert database.metrics == []


def test_database_seen_only_in_metrics_is_kept_without_listing() -> None:
    (database,) = build_cosmosdb_databases(
        _account(), None, [_metric("db2")], UniqueHostnamesConfig()
    )

    assert database.name == "acc_db2"
    assert database.metrics == [_metric("db2")]


def test_database_missing_from_listing_is_dropped() -> None:
    databases = build_cosmosdb_databases(
        _account(), {"db1": []}, [_metric("WnhSAA==")], UniqueHostnamesConfig()
    )

    assert [database.name for database in databases] == ["acc_db1"]


def test_container_missing_from_listing_is_dropped() -> None:
    (database,) = build_cosmosdb_databases(
        _account(),
        {"db1": ["c1"]},
        [_metric("db1", "c1"), _metric("db1", "WnhSAPSBwPQ=")],
        UniqueHostnamesConfig(),
    )

    assert database.metrics == [_metric("db1", "c1")]


def test_metrics_aggregated_over_all_databases_create_no_database() -> None:
    databases = build_cosmosdb_databases(
        _account(), None, [_metric("<empty>")], UniqueHostnamesConfig()
    )

    assert databases == []
