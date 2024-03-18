#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs


import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    ServiceLabel,
    State,
    StringTable,
)
from cmk.plugins.gcp.agent_based.gcp_assets import parse_assets
from cmk.plugins.gcp.agent_based.gcp_http_lb import (
    check_latencies,
    check_requests,
    check_summary,
    discover,
    parse,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.gcp.special_agents.agent_gcp import HTTP_LOADBALANCER

from .gcp_test_util import DiscoverTester, generate_stringtable, Plugin

ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config":["{HTTP_LOADBALANCER.name}"]}}'],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-load-balancer-test/global/urlMaps/http-lb", "asset_type": "compute.googleapis.com/UrlMap", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "UrlMap", "parent": "//cloudresourcemanager.googleapis.com/projects/1085633905945", "data": {"selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/urlMaps/http-lb", "creationTimestamp": "2022-08-24T01:24:13.799-07:00", "fingerprint": "lWKVO4QpW1o=", "name": "http-lb", "hostRules": [{"pathMatcher": "path-matcher-2", "hosts": ["*"]}], "id": "5820867100963004098", "defaultService": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/backendBuckets/cats", "pathMatchers": [{"name": "path-matcher-2", "defaultService": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/backendBuckets/cats", "pathRules": [{"paths": ["/love-to-fetch/*"], "service": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/backendBuckets/dogs"}]}]}, "location": "global", "resource_url": ""}, "ancestors": ["projects/1085633905945", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-24T08:24:30.849036Z", "org_policy": []}'
    ],
]


class TestHTTPLoadBalancerDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_items(self) -> set[str]:
        return {
            "http-lb",
        }

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return set()

    def discover(self, assets: gcp.AssetSection | None) -> DiscoveryResult:
        yield from discover(section_gcp_service_http_lb=None, section_gcp_assets=assets)


PLUGINS = [
    pytest.param(
        Plugin(
            function=check_requests,
            metrics=["requests"],
            results=[Result(state=State.OK, summary="Requests: 42.0")],
        ),
        id="requets",
    ),
    pytest.param(
        Plugin(
            function=check_latencies,
            metrics=[],
            percentile_metrics=[("latencies", [50, 95, 99])],
            results=[
                Result(state=State.OK, summary="Latency (50th percentile): 42 milliseconds"),
                Result(state=State.OK, summary="Latency (95th percentile): 42 milliseconds"),
                Result(state=State.OK, summary="Latency (99th percentile): 42 milliseconds"),
            ],
        ),
        id="latencies",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        [f'{{"project":"backup-255820", "config":["{HTTP_LOADBALANCER.name}"]}}'],
        [
            f'{{"name": "//compute.googleapis.com/projects/checkmk-load-balancer-test/global/urlMaps/{item}", "asset_type": "compute.googleapis.com/UrlMap", "resource": {{"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "UrlMap", "parent": "//cloudresourcemanager.googleapis.com/projects/1085633905945", "data": {{"selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/urlMaps/{item}", "creationTimestamp": "2022-08-24T01:24:13.799-07:00", "fingerprint": "lWKVO4QpW1o=", "name": "{item}", "hostRules": [{{"pathMatcher": "path-matcher-2", "hosts": ["*"]}}], "id": "5820867100963004098", "defaultService": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/backendBuckets/cats", "pathMatchers": [{{"name": "path-matcher-2", "defaultService": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/backendBuckets/cats", "pathRules": [{{"paths": ["/love-to-fetch/*"], "service": "https://www.googleapis.com/compute/v1/projects/checkmk-load-balancer-test/global/backendBuckets/dogs"}}]}}]}}, "location": "global", "resource_url": ""}}, "ancestors": ["projects/1085633905945", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-24T08:24:30.849036Z", "org_policy": []}}'
        ],
    ]
    section = parse(generate_stringtable(item, 42.0, HTTP_LOADBALANCER))
    yield from plugin.function(
        item=item,
        params=plugin.default_params(),
        section_gcp_service_http_lb=section,
        section_gcp_assets=parse_assets(asset_table),
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin: Plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == set(plugin.results)


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin: Plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == plugin.expected_metrics()


def test_check_summary() -> None:
    assets = parse_assets(ASSET_TABLE)
    results = set(check_summary(section=assets))
    assert results == {
        Result(state=State.OK, summary="1 load balancer", details="Found 1 load balancer")
    }
