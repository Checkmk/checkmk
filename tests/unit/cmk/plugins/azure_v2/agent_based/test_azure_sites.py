#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    DiscoveryResult,
    FixedLevelsT,
    get_value_store,
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.azure_sites import check_azure_sites, discover_azure_sites
from cmk.plugins.azure_v2.agent_based.lib import parse_resource

STRING_TABLE_1 = [
    ["Resource"],
    [
        '{"kind": "functionapp", "group": "cldazspo-solutions-rg", "name": "spo-solutions-fa1", "tags": {"OpLevel": "Operation", "OpHours": "7x24", "CostCenter": "0000252980", "ITProduct": "C89 Collaboration Platform"}, "provider": "Microsoft.Web", "subscription": "e95edb66-81e8-4acd-9ae8-68623f1bf7e6", "type": "Microsoft.Web/sites", "id": "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazspo-solutions-rg/providers/Microsoft.Web/sites/spo-solutions-fa1", "identity": {"tenant_id": "e7b94e3c-1ad5-477d-be83-17106c6c8301", "principal_id": "15c0b993-4efa-4cc1-9880-d68c0f59ed42", "type": "SystemAssigned"}, "location": "westeurope"}'
    ],
    ["metrics following", "24"],
    [
        '{"name": "TotalAppDomainsUnloaded", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Gen0Collections", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Gen1Collections", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Gen2Collections", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "BytesReceived", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "BytesSent", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Http5xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "MemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "AverageMemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "FunctionExecutionUnits", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "FunctionExecutionCount", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "AppConnections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Handles", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Threads", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "PrivateBytes", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "IoReadBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'
    ],
    [
        '{"name": "IoWriteBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'
    ],
    [
        '{"name": "IoOtherBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'
    ],
    [
        '{"name": "IoReadOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'
    ],
    [
        '{"name": "IoWriteOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'
    ],
    [
        '{"name": "IoOtherOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'
    ],
    [
        '{"name": "RequestsInApplicationQueue", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "CurrentAssemblies", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "TotalAppDomains", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
]
STRING_TABLE_2 = [
    ["Resource"],
    [
        '{"kind": "app", "group": "cldazpaaswebapp06-rg", "name": "zcldazwamonseas-as", "tags": {"OpLevel": "Operation", "OpHours": "7x24", "CostCenter": "0000252980", "ITProduct": "CUV130_MS_IIS (Internet Information Server) Standard"}, "provider": "Microsoft.Web", "subscription": "e95edb66-81e8-4acd-9ae8-68623f1bf7e6", "type": "Microsoft.Web/sites", "id": "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as", "location": "southeastasia"}'
    ],
    ["metrics following", "17"],
    [
        '{"name": "CpuTime", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "seconds"}'
    ],
    [
        '{"name": "Requests", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "BytesReceived", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "BytesSent", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Http101", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http2xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http3xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http401", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http403", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http404", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http406", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http4xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Http5xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "MemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "AverageMemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
    [
        '{"name": "AverageResponseTime", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "seconds"}'
    ],
    [
        '{"name": "AppConnections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Handles", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "Threads", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'
    ],
    [
        '{"name": "PrivateBytes", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'
    ],
]


@pytest.mark.parametrize(
    ("string_table", "expected_result"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                Service(
                    labels=[
                        ServiceLabel("cmk/azure/tag/OpLevel", "Operation"),
                        ServiceLabel("cmk/azure/tag/OpHours", "7x24"),
                        ServiceLabel("cmk/azure/tag/CostCenter", "0000252980"),
                        ServiceLabel("cmk/azure/tag/ITProduct", "C89 Collaboration Platform"),
                    ]
                )
            ],
            id="Resource 1",
        ),
        pytest.param(
            STRING_TABLE_2,
            [
                Service(
                    labels=[
                        ServiceLabel("cmk/azure/tag/OpLevel", "Operation"),
                        ServiceLabel("cmk/azure/tag/OpHours", "7x24"),
                        ServiceLabel("cmk/azure/tag/CostCenter", "0000252980"),
                        ServiceLabel(
                            "cmk/azure/tag/ITProduct",
                            "CUV130_MS_IIS (Internet Information Server) Standard",
                        ),
                    ]
                )
            ],
            id="Resource 2",
        ),
    ],
)
def test_discovery_azure_sites(string_table: StringTable, expected_result: DiscoveryResult) -> None:
    section = parse_resource(string_table)
    assert section
    services = list(discover_azure_sites(section))
    assert services == expected_result


@pytest.mark.usefixtures("initialised_item_state")
def test_check_azure_sites_resource_1() -> None:
    section = parse_resource(STRING_TABLE_1)
    assert section
    params: Mapping[str, FixedLevelsT[float]] = {
        "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
        "avg_response_time_levels": ("fixed", (1.0, 10.0)),
        "error_rate_levels": ("fixed", (0.01, 0.04)),
    }

    # Pre-populate value store to avoid GetRateError
    value_store = get_value_store()
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazspo-solutions-rg/providers/Microsoft.Web/sites/spo-solutions-fa1.total_Http5xx"
    ] = (1536073020.0, 0.0)
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as.total_CpuTime"
    ] = (1536073020.0, 0.0)

    results = list(check_azure_sites(params, section))

    assert results == [
        Result(state=State.OK, summary="Rate of server errors: 0%"),
        Metric("error_rate", 0.0, levels=(0.01, 0.04)),
        Result(state=State.OK, summary="Location: westeurope"),
        Result(state=State.OK, summary="CostCenter: 0000252980"),
        Result(state=State.OK, summary="ITProduct: C89 Collaboration Platform"),
        Result(state=State.OK, summary="OpHours: 7x24"),
        Result(state=State.OK, summary="OpLevel: Operation"),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_azure_sites_resource_2() -> None:
    section = parse_resource(STRING_TABLE_2)
    assert section
    params: Mapping[str, FixedLevelsT[float]] = {
        "cpu_time_percent_levels": ("fixed", (85.0, 95.0)),
        "avg_response_time_levels": ("fixed", (1.0, 10.0)),
        "error_rate_levels": ("fixed", (0.01, 0.04)),
    }

    # Pre-populate value store to avoid GetRateError
    value_store = get_value_store()
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as.total_Http5xx"
    ] = (1536073020.0, 0.0)
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as.total_CpuTime"
    ] = (1536073020.0, 0.0)

    results = list(check_azure_sites(params, section))

    assert results == [
        Result(state=State.OK, summary="CPU time: 0%"),
        Metric("cpu_time_percent", 0.0, levels=(85.0, 95.0)),
        Result(state=State.OK, summary="Average response time: 0 seconds"),
        Metric("avg_response_time", 0.0, levels=(1.0, 10.0)),
        Result(state=State.OK, summary="Rate of server errors: 0%"),
        Metric("error_rate", 0.0, levels=(0.01, 0.04)),
        Result(state=State.OK, summary="Location: southeastasia"),
        Result(state=State.OK, summary="CostCenter: 0000252980"),
        Result(
            state=State.OK,
            summary="ITProduct: CUV130_MS_IIS (Internet Information Server) Standard",
        ),
        Result(state=State.OK, summary="OpHours: 7x24"),
        Result(state=State.OK, summary="OpLevel: Operation"),
    ]
