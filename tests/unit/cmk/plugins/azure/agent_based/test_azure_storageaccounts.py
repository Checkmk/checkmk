#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.azure.agent_based.azure_storageaccounts import (
    check_plugin_azure_storageaccounts,
    check_plugin_azure_storageaccounts_flow,
    check_plugin_azure_storageaccounts_performance,
)
from cmk.plugins.lib.azure import parse_resources, Section

MiB = 1024**2
STRING_TABLE = [
    ["Resource"],
    [
        '{"sku": {"tier": "Standard", "name": "Standard_LRS"}, "kind": "BlobStorage", "group":'
        ' "BurningMan", "name": "st0ragetestaccount", "tags": {"monitoring": "some value"},'
        ' "provider": "Microsoft.Storage", "subscription": "2fac104f-cb9c-461d-be57-037039662426",'
        ' "type": "Microsoft.Storage/storageAccounts", "id": "/subscriptions/2fac104f-cb9c-461d'
        "-be57-037039662426/resourceGroups/BurningMan/providers/Microsoft.Storage/storageAccounts"
        '/st0ragetestaccount", "location": "westeurope"}'
    ],
    ["metrics following", "7"],
    [
        '{"name": "UsedCapacity", "timestamp": "1544591820", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 3822551.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Ingress", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 31620.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Egress", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 237007090.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Transactions", "timestamp": "1544595420", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 62.0, "unit": "count"}'
    ],
    [
        '{"name": "SuccessServerLatency", "timestamp": "1544595420", "aggregation": "average", "interval_id": "PT1H", "filter": "None", "value": 5624.0, "unit": "milli_seconds"}'
    ],
    [
        '{"name": "SuccessE2ELatency", "timestamp": "1544595420", "aggregation": "average", "interval_id": "PT1H", "filter": "None", "value": 9584.0, "unit": "milli_seconds"}'
    ],
    [
        '{"name": "Availability", "timestamp": "1544595420", "aggregation": "average", "interval_id": "PT1H", "filter": "None", "value": 6200.0, "unit": "percent"}'
    ],
    ["Resource"],
    [
        '{"sku": {"tier": "Standard", "name": "Standard_LRS"}, "kind": "Storage", "group":'
        ' "Glastonbury", "name": "glastonburydiag381", "tags": {}, "provider":'
        ' "Microsoft.Storage", "subscription": "2fac104f-cb9c-461d-be57-037039662426",'
        ' "type": "Microsoft.Storage/storageAccounts", "id": "/subscriptions/2fac104f-cb9c'
        "-461d-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Storage"
        '/storageAccounts/glastonburydiag381", "location": "westeurope"}'
    ],
    ["metrics following", "7"],
    [
        '{"name": "UsedCapacity", "timestamp": "1544598780", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 10773519964.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Ingress", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 43202937.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Egress", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 5835881.0, "unit": "bytes"}'
    ],
    [
        '{"name": "Transactions", "timestamp": "1544602380", "aggregation": "total", "interval_id": "PT1H", "filter": "None", "value": 1907.0, "unit": "count"}'
    ],
    [
        '{"name": "SuccessServerLatency", "timestamp": "1544602380", "aggregation": "average", "interval_id": "PT1H", "filter": "None", "value": 20105.0, "unit": "milli_seconds"}'
    ],
    [
        '{"name": "SuccessE2ELatency", "timestamp": "1544602380", "aggregation": "average", "interval_id": "PT1H", "filter": "None", "value": 37606.0, "unit": "milli_seconds"}'
    ],
    [
        '{"name": "Availability", "timestamp": "1544602380", "aggregation": "average", "interval_id": "PT1H", "filter": "None", "value": 190700.0, "unit": "percent"}'
    ],
]
LEVELS_USED = (2 * MiB, 4 * MiB)
LEVELS_EGRESS = (100 * MiB, 200 * MiB)
LEVELS_AVAILABILITY = (10_000, 5_000)


@pytest.fixture(scope="module")
def section_fixture() -> Section:
    return parse_resources(STRING_TABLE)


@pytest.mark.usefixtures("section_fixture")
@pytest.mark.parametrize(
    ["item", "params", "results_expected"],
    [
        pytest.param(
            "glastonburydiag381",
            {},
            [
                Result(state=State.OK, summary="Used capacity: 10.0 GiB"),
                Metric(name="used_space", value=10773519964),
            ],
            id="No params",
        ),
        pytest.param(
            "st0ragetestaccount",
            {"used_capacity_levels": ("fixed", LEVELS_USED)},
            [
                Result(
                    state=State.WARN,
                    summary="Used capacity: 3.65 MiB (warn/crit at 2.00 MiB/4.00 MiB)",
                ),
                Metric("used_space", 3822551, levels=LEVELS_USED),
            ],
            id="Params defined",
        ),
    ],
)
def test_check_azure_storageaccounts(
    item: str,
    params: Mapping[str, object],
    results_expected: list[object],
    section_fixture: Section,
) -> None:
    actual = list(check_plugin_azure_storageaccounts.check_function(item, params, section_fixture))
    assert actual == results_expected


@pytest.mark.usefixtures("section_fixture")
@pytest.mark.parametrize(
    ["item", "params", "results_expected"],
    [
        pytest.param(
            "glastonburydiag381",
            {},
            [
                Result(state=State.OK, summary="Ingress: 41.2 MiB"),
                Metric(name="ingress", value=43202937),
                Result(state=State.OK, summary="Egress: 5.57 MiB"),
                Metric(name="egress", value=5835881),
                Result(state=State.OK, summary="Transactions: 1907"),
                Metric(name="transactions", value=1907),
            ],
            id="No params",
        ),
        pytest.param(
            "st0ragetestaccount",
            {"egress_levels": ("fixed", LEVELS_EGRESS)},
            [
                Result(state=State.OK, summary="Ingress: 30.9 KiB"),
                Metric(name="ingress", value=31620),
                Result(state=State.CRIT, summary="Egress: 226 MiB (warn/crit at 100 MiB/200 MiB)"),
                Metric(name="egress", value=237007090, levels=LEVELS_EGRESS),
                Result(state=State.OK, summary="Transactions: 62"),
                Metric(name="transactions", value=62.0),
            ],
            id="Params defined",
        ),
    ],
)
def test_check_azure_storageaccounts_flow(
    item: str,
    params: Mapping[str, object],
    results_expected: list[object],
    section_fixture: Section,
) -> None:
    actual = list(
        check_plugin_azure_storageaccounts_flow.check_function(item, params, section_fixture)
    )
    assert actual == results_expected


@pytest.mark.usefixtures("section_fixture")
@pytest.mark.parametrize(
    ["item", "params", "results_expected"],
    [
        pytest.param(
            "glastonburydiag381",
            {},
            [
                Result(state=State.OK, summary="Success server latency: 20105 ms"),
                Metric(name="server_latency", value=20105),
                Result(state=State.OK, summary="End-to-end server latency: 37606 ms"),
                Metric(name="e2e_latency", value=37606),
                Result(state=State.OK, summary="Availability: 190700.00%"),
                Metric(name="availability", value=190700.0),
            ],
            id="no params",
        ),
        pytest.param(
            "st0ragetestaccount",
            {"availability_levels": ("fixed", LEVELS_AVAILABILITY)},
            [
                Result(state=State.OK, summary="Success server latency: 5624 ms"),
                Metric(name="server_latency", value=5624),
                Result(state=State.OK, summary="End-to-end server latency: 9584 ms"),
                Metric(name="e2e_latency", value=9584),
                Result(
                    state=State.WARN,
                    summary="Availability: 6200.00% (warn/crit below 10000.00%/5000.00%)",
                ),
                Metric(name="availability", value=6200.0),  # FYI: This should contain levels!
            ],
            id="params defined",
        ),
    ],
)
def test_check_plugin_azure_storageaccounts_performance(
    item: str,
    params: Mapping[str, object],
    results_expected: list[object],
    section_fixture: Section,
) -> None:
    actual = list(
        check_plugin_azure_storageaccounts_performance.check_function(item, params, section_fixture)
    )
    assert actual == results_expected
