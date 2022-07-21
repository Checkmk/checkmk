#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import abc
from typing import Any, Mapping, Optional, Sequence, Union

import pytest

from cmk.utils.type_defs.pluginname import CheckPluginName

from cmk.base.api.agent_based import register
from cmk.base.api.agent_based.checking_classes import CheckFunction, IgnoreResults, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.gcp_assets import parse_assets
from cmk.base.plugins.agent_based.gcp_redis import (
    check_connected_clients,
    check_cpu_util,
    check_hitratio,
    check_memory_util,
    check_summary,
    discover,
    parse,
)
from cmk.base.plugins.agent_based.utils import gcp

from cmk.special_agents.agent_gcp import REDIS

from .gcp_test_util import DiscoverTester, generate_timeseries, Plugin

ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config":["{REDIS.name}"]}}'],
    [
        '{"name": "//redis.googleapis.com/projects/tribe29-check-development/locations/europe-west6/instances/red", "asset_type": "redis.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri":"https://redis.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"persistenceIamIdentity": "serviceAccount:136208174824-compute@developer.gserviceaccount.com", "currentLocationId": "europe-west6-b", "reservedIpRange": "10.33.170.64/29", "authorizedNetwork": "projects/tribe29-check-development/global/networks/default", "displayName": "red2", "host": "10.33.170.67", "port": 6379.0, "locationId": "europe-west6-b", "state": "READY", "redisVersion": "REDIS_6_X", "transitEncryptionMode": "DISABLED", "createTime": "2022-03-28T11:04:35.40073338Z", "persistenceConfig": {"persistenceMode": "DISABLED"}, "tier": "BASIC", "name": "projects/tribe29-check-development/locations/europe-west6/instances/red", "memorySizeGb": 1.0, "connectMode": "DIRECT_PEERING", "nodes": [{"id": "node-0", "zone": "europe-west6-b"}], "readReplicasMode": "READ_REPLICAS_DISABLED"}, "location": "europe-west6", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-28T11:08:19.425454Z", "org_policy": []}'
    ],
]


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_services(self) -> set[str]:
        return {
            "projects/tribe29-check-development/locations/europe-west6/instances/red",
        }

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("gcp/projectId", "backup-255820"),
            ServiceLabel("gcp/redis/tier", "BASIC"),
            ServiceLabel("gcp/redis/host", "10.33.170.67"),
            ServiceLabel("gcp/redis/version", "REDIS_6_X"),
            ServiceLabel("gcp/redis/port", "6379"),
            ServiceLabel("gcp/redis/nr_nodes", "1"),
            ServiceLabel("gcp/redis/displayname", "red2"),
            ServiceLabel("gcp/redis/connectMode", "DIRECT_PEERING"),
            ServiceLabel("gcp/location", "europe-west6-b"),
        }

    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        yield from discover(section_gcp_service_redis=None, section_gcp_assets=assets)


PLUGINS = [
    pytest.param(
        Plugin(
            function=check_cpu_util,
            metrics=["util"],
            results=[Result(state=State.OK, summary="Utilization: 42.00%")],
        ),
        id="cpu",
    ),
    pytest.param(
        Plugin(
            function=check_memory_util,
            metrics=["memory_util", "system_memory_util"],
            results=[
                Result(state=State.OK, summary="Memory utilization: 42.00%"),
                Result(state=State.OK, summary="System memory utilization: 42.00%"),
            ],
        ),
        id="memory",
    ),
    pytest.param(
        Plugin(
            function=check_connected_clients,
            metrics=["clients_connected"],
            results=[
                Result(state=State.OK, summary="Connected Clients: 0.42"),
            ],
        ),
        id="connected_clients",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        [f'{{"project":"backup-255820", "config":["{REDIS.name}"]}}'],
        [
            f'{{"name": "//redis.googleapis.com/projects/tribe29-check-development/locations/europe-west6/instances/red", "asset_type": "redis.googleapis.com/Instance", "resource": {{"version": "v1", "discovery_document_uri":"https://redis.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {{"persistenceIamIdentity": "serviceAccount:136208174824-compute@developer.gserviceaccount.com", "currentLocationId": "europe-west6-b", "reservedIpRange": "10.33.170.64/29", "authorizedNetwork": "projects/tribe29-check-development/global/networks/default", "displayName": "red2", "host": "10.33.170.67", "port": 6379.0, "locationId": "europe-west6-b", "state": "READY", "redisVersion": "REDIS_6_X", "transitEncryptionMode": "DISABLED", "createTime": "2022-03-28T11:04:35.40073338Z", "persistenceConfig": {{"persistenceMode": "DISABLED"}}, "tier": "BASIC", "name": "{item}", "memorySizeGb": 1.0, "connectMode": "DIRECT_PEERING", "nodes": [{{"id": "node-0", "zone": "europe-west6-b"}}], "readReplicasMode": "READ_REPLICAS_DISABLED"}}, "location": "europe-west6", "resource_url": ""}}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-28T11:08:19.425454Z", "org_policy": []}}'
        ],
    ]
    section = parse(generate_timeseries(item, 0.42, REDIS))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_redis=section,
        section_gcp_assets=parse_assets(asset_table),
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin: Plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == set(plugin.results)


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin: Plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == set(plugin.metrics)


class ABCTestRedisChecks(abc.ABC):
    ITEM = "redis1"
    METRIC_NAME = "hitratio"

    @abc.abstractmethod
    def _section_kwargs(self, section: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def _section(self, hitratio: float, item: str) -> Any:
        raise NotImplementedError

    def _parametrize(self, hitratio: float, params: Mapping[str, Any]) -> Mapping[str, Any]:
        kwargs: dict[str, Any] = {}
        kwargs["item"] = self.ITEM
        kwargs["params"] = params
        for k, v in self._section_kwargs(self._section(hitratio, self.ITEM)).items():
            kwargs[k] = v
        return kwargs

    def run(
        self, hitratio: float, params: Mapping[str, Any], check: CheckFunction
    ) -> Sequence[Union[IgnoreResults, Result, Metric]]:
        kwargs = self._parametrize(hitratio, params=params)
        return list(check(**kwargs))

    def test_expected_number_of_results_and_metrics(self, check: CheckFunction) -> None:
        params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
        results = self.run(50, params, check)
        assert len(results) == 2

    @pytest.mark.parametrize(
        "state, hitratio, summary_ext",
        [
            pytest.param(State.OK, 0.5, "", id="ok"),
            pytest.param(State.WARN, 0.85, " (warn/crit at 80.00%/90.00%)", id="warning upper"),
            pytest.param(State.CRIT, 0.95, " (warn/crit at 80.00%/90.00%)", id="critical upper"),
            pytest.param(State.WARN, 0.35, " (warn/crit below 40.00%/30.00%)", id="warning lower"),
            pytest.param(State.CRIT, 0.25, " (warn/crit below 40.00%/30.00%)", id="critial lower"),
        ],
    )
    def test_yield_levels(
        self, state: State, hitratio: float, check: CheckFunction, summary_ext: str
    ) -> None:
        levels_upper = (80, 90)
        levels_lower = (40, 30)
        params = {"levels_upper_hitratio": levels_upper, "levels_lower_hitratio": levels_lower}
        results = [el for el in self.run(hitratio, params, check) if isinstance(el, Result)]
        summary = f"Hitratio: {(hitratio*100):.2f}%{summary_ext}"
        assert results[0] == Result(state=state, summary=summary)

    @pytest.mark.parametrize("hitratio", [0, 1, 0.5])
    def test_yield_no_levels(self, hitratio: float, check: CheckFunction) -> None:
        params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
        results = [el for el in self.run(hitratio, params, check) if isinstance(el, Result)]
        assert results[0].state == State.OK

    @pytest.mark.parametrize("hitratio", [0, 1, 0.5])
    def test_metric(self, hitratio: float, check: CheckFunction) -> None:
        params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
        metrics = [el for el in self.run(hitratio, params, check) if isinstance(el, Metric)]
        assert metrics[0] == Metric(self.METRIC_NAME, hitratio * 100)


class TestRedisGCP(ABCTestRedisChecks):
    @staticmethod
    @pytest.fixture(scope="class")
    def check() -> CheckFunction:
        return check_hitratio

    def _section_kwargs(self, section: gcp.Section) -> dict[str, gcp.Section | gcp.AssetSection]:
        asset_table = [
            [f'{{"project":"backup-255820", "config":["{REDIS.name}"]}}'],
            [
                f'{{"name": "//redis.googleapis.com/projects/tribe29-check-development/locations/europe-west6/instances/red", "asset_type": "redis.googleapis.com/Instance", "resource": {{"version": "v1", "discovery_document_uri":"https://redis.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {{"persistenceIamIdentity": "serviceAccount:136208174824-compute@developer.gserviceaccount.com", "currentLocationId": "europe-west6-b", "reservedIpRange": "10.33.170.64/29", "authorizedNetwork": "projects/tribe29-check-development/global/networks/default", "displayName": "red2", "host": "10.33.170.67", "port": 6379.0, "locationId": "europe-west6-b", "state": "READY", "redisVersion": "REDIS_6_X", "transitEncryptionMode": "DISABLED", "createTime": "2022-03-28T11:04:35.40073338Z", "persistenceConfig": {{"persistenceMode": "DISABLED"}}, "tier": "BASIC", "name": "{self.ITEM}", "memorySizeGb": 1.0, "connectMode": "DIRECT_PEERING", "nodes": [{{"id": "node-0", "zone": "europe-west6-b"}}], "readReplicasMode": "READ_REPLICAS_DISABLED"}}, "location": "europe-west6", "resource_url": ""}}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-28T11:08:19.425454Z", "org_policy": []}}'
            ],
        ]
        assets = parse_assets(asset_table)
        return {
            "section_gcp_service_redis": section,
            "section_gcp_assets": assets,
        }

    def _section(self, hitratio: float, item: str) -> gcp.Section:
        return parse(generate_timeseries(item, hitratio, REDIS))


def test_hitratio_return_when_section_is_empty() -> None:
    results = list(check_hitratio("item", {}, None, None))
    assert len(results) == 0


def test_hitratio_no_results_if_item_not_found() -> None:
    params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
    section = parse(generate_timeseries("item", 42, REDIS))
    results = check_hitratio(
        item="I do not exist",
        params=params,
        section_gcp_service_redis=section,
        section_gcp_assets=parse_assets(ASSET_TABLE),
    )
    assert len(list(results)) == 0


def test_check_summary() -> None:
    assets = parse_assets(ASSET_TABLE)
    results = set(check_summary(section=assets))
    assert results == {Result(state=State.OK, summary="1 Instance", details="Found 1 instance")}


def test_check_summary_asset_not_included() -> None:
    assets = parse_assets(ASSET_TABLE[:1])
    results = list(check_summary(section=assets))
    assert results == [Result(state=State.OK, summary="0 Instances", details="Found 0 instances")]


def test_summary_service_name() -> None:
    plugin = register.get_check_plugin(CheckPluginName("gcp_redis_summary"))
    assert plugin is not None
    assert plugin.service_name == "Redis - summary"


def test_service_name() -> None:
    plugin = register.get_check_plugin(CheckPluginName("gcp_redis_hitratio"))
    assert plugin is not None
    assert plugin.service_name == "Redis - %s - hitratio"
