#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import datetime
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import pytest
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.types import TimeSeries

from cmk.base.api.agent_based.checking_classes import Result, Service, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.gcp_assets import parse_assets
from cmk.base.plugins.agent_based.utils import gcp

from cmk.special_agents import agent_gcp


class DiscoverTester(ABC):
    @property
    @abstractmethod
    def _assets(self) -> StringTable:
        raise NotImplementedError

    @property
    @abstractmethod
    def expected_services(self) -> set[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def expected_labels(self) -> set[ServiceLabel]:
        raise NotImplementedError

    @abstractmethod
    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
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

    def test_discover_project_label(self, services: Sequence[Service]) -> None:
        for asset in services:
            assert ServiceLabel("gcp/projectId", "backup-255820") in asset.labels

    def test_discover_all_services(self, services: Sequence[Service]) -> None:
        assert {a.item for a in services} == self.expected_services

    def test_discover_all_services_labels(self, services: Sequence[Service]) -> None:
        assert set(services[0].labels) == self.expected_labels

    def test_discover_nothing_without_service_configured(self) -> None:
        string_table = [
            ['{"project":"backup-255820", "config":["none"]}'],
        ]
        assert len(list(self.discover(parse_assets(string_table)))) == 0


def generate_timeseries(item: str, value: float, service_desc: agent_gcp.Service) -> StringTable:
    start_time = datetime.datetime(2016, 4, 6, 22, 5, 0, 42)
    end_time = datetime.datetime(2016, 4, 6, 22, 5, 1, 42)
    interval = monitoring_v3.TimeInterval(end_time=end_time, start_time=start_time)
    point = monitoring_v3.Point({"interval": interval, "value": {"double_value": value}})

    time_series = []
    for metric in service_desc.metrics:
        metric_type = metric.name
        resource_labels = {"project": "test", service_desc.default_groupby.split(".", 1)[-1]: item}
        ts = monitoring_v3.TimeSeries(
            {
                "metric": {"type": metric_type, "labels": {}},
                "resource": {"type": "does_not_matter_i_think", "labels": resource_labels},
                "metric_kind": 1,
                "value_type": 3,
                "points": [point],
            }
        )
        time_series.append(ts)

    return [[json.dumps(TimeSeries.to_dict(ts))] for ts in time_series]


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    results: Sequence[Result]
    function: Callable[..., CheckResult]

    def __post_init__(self) -> None:
        assert len(self.metrics) == len(
            self.results
        ), "expect to have the same number of metrics and results"
