#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    FixedLevelsT,
    IgnoreResultsError,
    Metric,
    Result,
    ServiceLabel,
    State,
)
from cmk.plugins.azure_deprecated.agent_based import azure_sites
from cmk.plugins.azure_deprecated.agent_based.lib import parse_resources, Resource

STRING_TABLE = [
    ["Resource"],
    [
        '{"kind": "functionapp", "group": "cldazspo-solutions-rg", "name": "spo-solutions-fa1", "tags": {"OpLevel": "Operation", "OpHours": "7x24", "CostCenter": "0000252980", "ITProduct": "C89 Collaboration Platform"}, "provider": "Microsoft.Web", "subscription": "e95edb66-81e8-4acd-9ae8-68623f1bf7e6", "type": "Microsoft.Web/sites", "id": "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazspo-solutions-rg/providers/Microsoft.Web/sites/spo-solutions-fa1", "identity": {"tenant_id": "e7b94e3c-1ad5-477d-be83-17106c6c8301", "principal_id": "15c0b993-4efa-4cc1-9880-d68c0f59ed42", "type": "SystemAssigned"}, "location": "westeurope"}'
    ],
    ["metrics following", "3"],
    [
        '{"name": "Http5xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    ["Resource"],
    [
        '{"kind": "app", "group": "cldazpaaswebapp06-rg", "name": "zcldazwamonseas-as", "tags": {"OpLevel": "Operation", "OpHours": "7x24", "CostCenter": "0000252980", "ITProduct": "CUV130_MS_IIS (Internet Information Server) Standard"}, "provider": "Microsoft.Web", "subscription": "e95edb66-81e8-4acd-9ae8-68623f1bf7e6", "type": "Microsoft.Web/sites", "id": "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as", "location": "southeastasia"}'
    ],
    ["metrics following", "3"],
    [
        '{"name": "CpuTime", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "seconds"}'
    ],
    [
        '{"name": "AverageResponseTime", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "seconds"}'
    ],
    [
        '{"name": "Http5xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
]

_PARAMS: Mapping[str, FixedLevelsT[float]] = {
    "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
    "avg_response_time_levels": ("fixed", (1.0, 10.0)),
    "error_rate_levels": ("fixed", (0.01, 0.04)),
}


@pytest.fixture(name="section")
def _section() -> Mapping[str, Resource]:
    return parse_resources(STRING_TABLE)


def test_parse_azure_sites(section: Mapping[str, Resource]) -> None:
    assert set(section) == {"spo-solutions-fa1", "zcldazwamonseas-as"}
    assert section["spo-solutions-fa1"].location == "westeurope"
    assert "total_Http5xx" in section["spo-solutions-fa1"].metrics
    assert "total_CpuTime" in section["zcldazwamonseas-as"].metrics
    assert "total_AverageResponseTime" in section["zcldazwamonseas-as"].metrics


def test_discover_azure_sites(section: Mapping[str, Resource]) -> None:
    services = list(azure_sites.discover_azure_sites(section))

    assert [s.item for s in services] == ["spo-solutions-fa1", "zcldazwamonseas-as"]
    assert services[0].labels == [
        ServiceLabel("cmk/azure/tag/OpLevel", "Operation"),
        ServiceLabel("cmk/azure/tag/OpHours", "7x24"),
        ServiceLabel("cmk/azure/tag/CostCenter", "0000252980"),
        ServiceLabel("cmk/azure/tag/ITProduct", "C89 Collaboration Platform"),
    ]


def test_check_azure_sites_error_rate_only(
    section: Mapping[str, Resource], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        azure_sites,
        "get_value_store",
        lambda: {
            "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazspo-solutions-rg/providers/Microsoft.Web/sites/spo-solutions-fa1.total_Http5xx": (
                1536073020.0,
                0.0,
            )
        },
    )

    results = list(azure_sites.check_azure_sites("spo-solutions-fa1", _PARAMS, section))

    assert results == [
        Result(state=State.OK, summary="Rate of server errors: 0.0"),
        Metric("error_rate", 0.0, levels=(0.01, 0.04), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Location: westeurope"),
        Result(state=State.OK, summary="CostCenter: 0000252980"),
        Result(state=State.OK, summary="ITProduct: C89 Collaboration Platform"),
        Result(state=State.OK, summary="OpHours: 7x24"),
        Result(state=State.OK, summary="OpLevel: Operation"),
    ]


def test_check_azure_sites_all_metrics(
    section: Mapping[str, Resource], monkeypatch: pytest.MonkeyPatch
) -> None:
    base = "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as"
    monkeypatch.setattr(
        azure_sites,
        "get_value_store",
        lambda: {
            f"{base}.total_CpuTime": (1536073020.0, 0.0),
            f"{base}.total_Http5xx": (1536073020.0, 0.0),
        },
    )

    results = list(azure_sites.check_azure_sites("zcldazwamonseas-as", _PARAMS, section))

    assert results == [
        Result(state=State.OK, summary="CPU time: 0%"),
        Metric("cpu_time_percent", 0.0, levels=(85.0, 95.0), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Average response time: 0.00 s"),
        Metric("avg_response_time", 0.0, levels=(1.0, 10.0), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Rate of server errors: 0.0"),
        Metric("error_rate", 0.0, levels=(0.01, 0.04), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Location: southeastasia"),
        Result(state=State.OK, summary="CostCenter: 0000252980"),
        Result(
            state=State.OK,
            summary="ITProduct: CUV130_MS_IIS (Internet Information Server) Standard",
        ),
        Result(state=State.OK, summary="OpHours: 7x24"),
        Result(state=State.OK, summary="OpLevel: Operation"),
    ]


def test_check_azure_sites_missing_item(section: Mapping[str, Resource]) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(azure_sites.check_azure_sites("non-existent-site", _PARAMS, section))
