#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping

import pytest

from cmk.agent_based.v1 import get_value_store
from cmk.base.legacy_checks.azure_sites import check_azure_sites, discover_azure_sites
from cmk.plugins.lib.azure import parse_resources, Resource


@pytest.fixture(name="string_table")
def string_table() -> list[list[str]]:
    """String table representing Azure sites with metrics following Pattern 5r - Azure Sites Monitoring"""
    return [
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


@pytest.fixture(name="parsed_data")
def parsed_data(string_table: list[list[str]]) -> Mapping[str, Resource]:
    """Parsed Azure sites data using actual parse function"""
    return parse_resources(string_table)


def test_discovery_azure_sites(parsed_data: Mapping[str, Resource]) -> None:
    """Test discovery function finds both sites with correct service labels"""
    services = list(discover_azure_sites(parsed_data))

    assert len(services) == 2

    # Check first service
    assert services[0].item == "spo-solutions-fa1"
    assert services[0].labels is not None
    service_labels_dict = {label.name: label.value for label in services[0].labels}
    assert service_labels_dict["cmk/azure/tag/CostCenter"] == "0000252980"
    assert service_labels_dict["cmk/azure/tag/ITProduct"] == "C89 Collaboration Platform"
    assert service_labels_dict["cmk/azure/tag/OpHours"] == "7x24"
    assert service_labels_dict["cmk/azure/tag/OpLevel"] == "Operation"

    # Check second service
    assert services[1].item == "zcldazwamonseas-as"
    assert services[1].labels is not None
    service_labels_dict = {label.name: label.value for label in services[1].labels}
    assert service_labels_dict["cmk/azure/tag/CostCenter"] == "0000252980"
    assert (
        service_labels_dict["cmk/azure/tag/ITProduct"]
        == "CUV130_MS_IIS (Internet Information Server) Standard"
    )


@pytest.mark.usefixtures("initialised_item_state")
def test_check_azure_sites_spo_solutions_fa1(parsed_data: Mapping[str, Resource]) -> None:
    """Test check function for spo-solutions-fa1 with error rate metric only"""
    params = {
        "cpu_time_percent_levels": (85.0, 95.0),
        "avg_response_time_levels": (1.0, 10.0),
        "error_rate_levels": (0.01, 0.04),
    }

    # Pre-populate value store to avoid GetRateError
    value_store = get_value_store()
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazspo-solutions-rg/providers/Microsoft.Web/sites/spo-solutions-fa1.total_Http5xx"
    ] = (1536073020.0, 0.0)

    results = list(check_azure_sites("spo-solutions-fa1", params, parsed_data))

    assert len(results) == 6

    # Check error rate metric result
    result = results[0]
    assert len(result) == 3  # (state, summary, metrics)
    state, summary, metrics = result
    assert state == 0  # OK
    assert "Rate of server errors: 0.0" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("error_rate", 0.0, 0.01, 0.04, 0, None)

    # Check resource attributes (tags and location)
    expected_messages = [
        "Location: westeurope",
        "CostCenter: 0000252980",
        "ITProduct: C89 Collaboration Platform",
        "OpHours: 7x24",
        "OpLevel: Operation",
    ]

    for i, expected_msg in enumerate(expected_messages, 1):
        result = results[i]
        assert len(result) == 2  # (state, summary) - no metrics for attributes
        state, summary = result
        assert state == 0  # OK
        assert expected_msg in summary


@pytest.mark.usefixtures("initialised_item_state")
def test_check_azure_sites_zcldazwamonseas_as(parsed_data: Mapping[str, Resource]) -> None:
    """Test check function for zcldazwamonseas-as with all three metrics"""
    params = {
        "cpu_time_percent_levels": (85.0, 95.0),
        "avg_response_time_levels": (1.0, 10.0),
        "error_rate_levels": (0.01, 0.04),
    }

    # Pre-populate value store to avoid GetRateError
    value_store = get_value_store()
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as.total_CpuTime"
    ] = (1536073020.0, 0.0)
    value_store[
        "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as.total_Http5xx"
    ] = (1536073020.0, 0.0)

    results = list(check_azure_sites("zcldazwamonseas-as", params, parsed_data))

    assert len(results) == 8

    # Check CPU time metric result
    result = results[0]
    assert len(result) == 3  # (state, summary, metrics)
    state, summary, metrics = result
    assert state == 0  # OK
    assert "CPU time: 0%" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("cpu_time_percent", 0.0, 85.0, 95.0, 0, None)

    # Check average response time metric result
    result = results[1]
    assert len(result) == 3  # (state, summary, metrics)
    state, summary, metrics = result
    assert state == 0  # OK
    assert "Average response time: 0.00 s" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("avg_response_time", 0.0, 1.0, 10.0, 0, None)

    # Check error rate metric result
    result = results[2]
    assert len(result) == 3  # (state, summary, metrics)
    state, summary, metrics = result
    assert state == 0  # OK
    assert "Rate of server errors: 0.0" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("error_rate", 0.0, 0.01, 0.04, 0, None)

    # Check resource attributes (tags and location)
    expected_messages = [
        "Location: southeastasia",
        "CostCenter: 0000252980",
        "ITProduct: CUV130_MS_IIS (Internet Information Server) Standard",
        "OpHours: 7x24",
        "OpLevel: Operation",
    ]

    for i, expected_msg in enumerate(expected_messages, 3):
        result = results[i]
        assert len(result) == 2  # (state, summary) - no metrics for attributes
        state, summary = result
        assert state == 0  # OK
        assert expected_msg in summary


def test_check_azure_sites_missing_item(parsed_data: Mapping[str, Resource]) -> None:
    """Test check function behavior for non-existent site"""
    params = {
        "cpu_time_percent_levels": (85.0, 95.0),
        "avg_response_time_levels": (1.0, 10.0),
        "error_rate_levels": (0.01, 0.04),
    }

    # Missing items should raise IgnoreResultsError
    from cmk.agent_based.v1._checking_classes import IgnoreResultsError

    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_azure_sites("non-existent-site", params, parsed_data))


def test_parsed_data_structure(parsed_data: Mapping[str, Resource]) -> None:
    """Test that parsed data has the expected structure and content"""
    assert len(parsed_data) == 2
    assert "spo-solutions-fa1" in parsed_data
    assert "zcldazwamonseas-as" in parsed_data

    # Check first resource
    resource1 = parsed_data["spo-solutions-fa1"]
    assert resource1.name == "spo-solutions-fa1"
    assert resource1.location == "westeurope"
    assert resource1.kind == "functionapp"
    assert resource1.group == "cldazspo-solutions-rg"
    assert "OpLevel" in resource1.tags
    assert "total_Http5xx" in resource1.metrics

    # Check second resource
    resource2 = parsed_data["zcldazwamonseas-as"]
    assert resource2.name == "zcldazwamonseas-as"
    assert resource2.location == "southeastasia"
    assert resource2.kind == "app"
    assert resource2.group == "cldazpaaswebapp06-rg"
    assert "total_CpuTime" in resource2.metrics
    assert "total_AverageResponseTime" in resource2.metrics
    assert "total_Http5xx" in resource2.metrics
