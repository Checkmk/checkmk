#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import datetime
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest
from google.cloud import monitoring_v3

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    ServiceLabel,
    StringTable,
)
from cmk.plugins.gcp.agent_based.gcp_assets import parse_assets
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.gcp.special_agents import agent_gcp


class DiscoverTester(ABC):
    @property
    @abstractmethod
    def _assets(self) -> StringTable:
        raise NotImplementedError

    @property
    @abstractmethod
    def expected_items(self) -> set[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def expected_labels(self) -> set[ServiceLabel]:
        raise NotImplementedError

    @abstractmethod
    def discover(self, assets: gcp.AssetSection | None) -> DiscoveryResult:
        pass

    ###########
    # Fixture #
    ###########

    @pytest.fixture(name="asset_section")
    def fixture_asset_section(self) -> gcp.AssetSection:
        return parse_assets(self._assets)

    @pytest.fixture(name="services")
    def fixture_services(self, asset_section: gcp.AssetSection) -> Sequence[Service]:
        return list(self.discover(assets=asset_section))

    #######################
    # Test implementation #
    #######################

    def test_no_assets_yield_no_section(self) -> None:
        assert len(list(self.discover(assets=None))) == 0

    def test_found_some_assets(self, asset_section: gcp.AssetSection) -> None:
        assert len(asset_section._assets) != 0

    def test_discover_all_items(self, services: Sequence[Service]) -> None:
        assert {a.item for a in services} == self.expected_items

    def test_discover_all_services_labels(self, services: Sequence[Service]) -> None:
        assert set(services[0].labels) == self.expected_labels

    def test_discover_nothing_without_service_configured(self) -> None:
        string_table = [['{"config":["none"]}']]
        assert len(list(self.discover(parse_assets(string_table)))) == 0

    def test_discover_nothing_without_asset(self) -> None:
        string_table = [self._assets[0]]
        assert len(list(self.discover(parse_assets(string_table)))) == 0


def generate_labels(item: str, service_desc: agent_gcp.Service) -> tuple[Mapping, Mapping]:
    metric_labels = {}
    resource_labels = {"project": "test"}
    if "resource" in service_desc.default_groupby:
        resource_labels[service_desc.default_groupby.split(".", 1)[-1]] = item
    elif "metric" in service_desc.default_groupby:
        metric_labels[service_desc.default_groupby.split(".", 1)[-1]] = item
    else:
        raise RuntimeError("Unknown label for group by")
    return metric_labels, resource_labels


def generate_stringtable(
    item: str,
    value: float,
    service_desc: agent_gcp.Service,
    overriding_values: Mapping[str, float] | None = None,
) -> StringTable:
    if overriding_values is None:
        overriding_values = {}

    start_time = datetime.datetime(2016, 4, 6, 22, 5, 0, 42)
    end_time = datetime.datetime(2016, 4, 6, 22, 5, 1, 42)
    interval = monitoring_v3.TimeInterval(  # type: ignore[no-untyped-call,unused-ignore]
        end_time=end_time,
        start_time=start_time,
    )

    metric_labels, resource_labels = generate_labels(item, service_desc)

    results = []
    for metric in service_desc.metrics:
        metric_type = metric.name
        point = monitoring_v3.Point(  # type: ignore[no-untyped-call,unused-ignore]
            {
                "interval": interval,
                "value": {"double_value": overriding_values.get(metric_type, value)},
            }
        )
        ts = monitoring_v3.TimeSeries(  # type: ignore[no-untyped-call,unused-ignore]
            {
                "metric": {"type": metric_type, "labels": metric_labels},
                "resource": {"type": "does_not_matter_i_think", "labels": resource_labels},
                "metric_kind": 1,
                "value_type": 3,
                "points": [point],
            }
        )
        results.append(agent_gcp.Result(ts=ts, aggregation=metric.aggregation.to_obj("test")))

    return [[agent_gcp.Result.serialize(r)] for r in results]


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    results: Sequence[Result]
    function: Callable[..., CheckResult]
    percentile_metrics: Sequence[tuple[str, Sequence[int]]] = field(default_factory=list)
    pure_metrics: Sequence[str] = field(default_factory=list)
    additional_results: Sequence[Result] = field(default_factory=list)
    default_value: float = 42.0
    override_values: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        num_percentile_metrics = sum(len(percentiles) for _, percentiles in self.percentile_metrics)
        assert len(self.metrics) + num_percentile_metrics == len(self.results) + len(
            self.additional_results
        ), "expect to have the same number of metrics and results"

    def expected_results(self) -> set:
        return set(self.results) | set(self.additional_results)

    def expected_metrics(self) -> set:
        expanded_perc_metrics = {
            f"{metric}_{percentile}"
            for metric, percentiles in self.percentile_metrics
            for percentile in percentiles
        }
        return set(self.metrics) | set(self.pure_metrics) | expanded_perc_metrics

    def default_params(self) -> Mapping[str, Any]:
        params: dict[str, Any] = {metric: None for metric in self.metrics}
        for metric, percentiles in self.percentile_metrics:
            params[metric] = (percentiles[-1], None)
        return params
