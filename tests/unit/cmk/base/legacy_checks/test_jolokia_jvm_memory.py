#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.jolokia_jvm_memory import (
    check_jolokia_jvm_memory,
    discover_jolokia_jvm_memory,
    parse_jolokia_jvm_memory,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "MyInstance",
                    "java.lang:type=Memory",
                    '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224, "committed": 123207680}, "HeapMemoryUsage": {"max": 536870912, "init": 67108864, "used": 78331216, "committed": 122683392}, "ObjectPendingFinalizationCount": 0, "ObjectName": {"objectName": "java.lang:type=Memory"}, "Verbose": false}',
                ],
                [
                    "MyInstance",
                    "java.lang:name=*,type=MemoryPool",
                    '{"java.lang:name=Metaspace,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Metaspace", "ObjectName": {"objectName": "java.lang:name=Metaspace,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["Metaspace Manager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "PeakUsage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}, "java.lang:name=Code Cache,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Code Cache", "ObjectName": {"objectName": "java.lang:name=Code Cache,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["CodeCacheManager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": 536870912, "init": 33554432, "used": 370254912, "committed": 373489664}, "PeakUsage": {"max": 536870912, "init": 33554432, "used": 370304384, "committed": 373489664}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}}',
                ],
            ],
            [("MyInstance", {})],
        ),
    ],
)
def test_discover_jolokia_jvm_memory(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for jolokia_jvm_memory check."""
    parsed = parse_jolokia_jvm_memory(string_table)
    result = list(discover_jolokia_jvm_memory(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "MyInstance",
            {},
            [
                [
                    "MyInstance",
                    "java.lang:type=Memory",
                    '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224, "committed": 123207680}, "HeapMemoryUsage": {"max": 536870912, "init": 67108864, "used": 78331216, "committed": 122683392}, "ObjectPendingFinalizationCount": 0, "ObjectName": {"objectName": "java.lang:type=Memory"}, "Verbose": false}',
                ],
                [
                    "MyInstance",
                    "java.lang:name=*,type=MemoryPool",
                    '{"java.lang:name=Metaspace,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Metaspace", "ObjectName": {"objectName": "java.lang:name=Metaspace,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["Metaspace Manager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "PeakUsage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}, "java.lang:name=Code Cache,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Code Cache", "ObjectName": {"objectName": "java.lang:name=Code Cache,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["CodeCacheManager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": 536870912, "init": 33554432, "used": 370254912, "committed": 373489664}, "PeakUsage": {"max": 536870912, "init": 33554432, "used": 370304384, "committed": 373489664}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}}',
                ],
            ],
            [
                (0, "Heap: 74.7 MiB", [("mem_heap", 78331216, None, None, None, 536870912)]),
                (0, "14.59%", []),
                (0, "Nonheap: 105 MiB", [("mem_nonheap", 110167224, None, None, None, 780140544)]),
                (0, "14.12%", []),
                (0, "Total: 180 MiB", []),
                (0, "14.31%", []),
            ],
        ),
        (
            "MyInstance",
            {"perc_total": (13.0, 15.0)},
            [
                [
                    "MyInstance",
                    "java.lang:type=Memory",
                    '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224, "committed": 123207680}, "HeapMemoryUsage": {"max": 536870912, "init": 67108864, "used": 78331216, "committed": 122683392}, "ObjectPendingFinalizationCount": 0, "ObjectName": {"objectName": "java.lang:type=Memory"}, "Verbose": false}',
                ],
                [
                    "MyInstance",
                    "java.lang:name=*,type=MemoryPool",
                    '{"java.lang:name=Metaspace,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Metaspace", "ObjectName": {"objectName": "java.lang:name=Metaspace,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["Metaspace Manager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "PeakUsage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}, "java.lang:name=Code Cache,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Code Cache", "ObjectName": {"objectName": "java.lang:name=Code Cache,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["CodeCacheManager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": 536870912, "init": 33554432, "used": 370254912, "committed": 373489664}, "PeakUsage": {"max": 536870912, "init": 33554432, "used": 370304384, "committed": 373489664}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}}',
                ],
            ],
            [
                (0, "Heap: 74.7 MiB", [("mem_heap", 78331216, None, None, None, 536870912)]),
                (0, "14.59%", []),
                (0, "Nonheap: 105 MiB", [("mem_nonheap", 110167224, None, None, None, 780140544)]),
                (0, "14.12%", []),
                (0, "Total: 180 MiB", []),
                (1, "14.31% (warn/crit at 13.00%/15.00%)", []),
            ],
        ),
        (
            "MyInstance",
            {"abs_heap": (450, 460)},
            [
                [
                    "MyInstance",
                    "java.lang:type=Memory",
                    '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224, "committed": 123207680}, "HeapMemoryUsage": {"max": 536870912, "init": 67108864, "used": 78331216, "committed": 122683392}, "ObjectPendingFinalizationCount": 0, "ObjectName": {"objectName": "java.lang:type=Memory"}, "Verbose": false}',
                ],
                [
                    "MyInstance",
                    "java.lang:name=*,type=MemoryPool",
                    '{"java.lang:name=Metaspace,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Metaspace", "ObjectName": {"objectName": "java.lang:name=Metaspace,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["Metaspace Manager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "PeakUsage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}, "java.lang:name=Code Cache,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Code Cache", "ObjectName": {"objectName": "java.lang:name=Code Cache,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["CodeCacheManager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": 536870912, "init": 33554432, "used": 370254912, "committed": 373489664}, "PeakUsage": {"max": 536870912, "init": 33554432, "used": 370304384, "committed": 373489664}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}}',
                ],
            ],
            [
                (
                    2,
                    "Heap: 74.7 MiB (warn/crit at 450 B/460 B)",
                    [("mem_heap", 78331216, 450.0, 460.0, None, 536870912)],
                ),
                (0, "14.59%", []),
                (0, "Nonheap: 105 MiB", [("mem_nonheap", 110167224, None, None, None, 780140544)]),
                (0, "14.12%", []),
                (0, "Total: 180 MiB", []),
                (0, "14.31%", []),
            ],
        ),
        (
            "MyInstance",
            {"perc_total": (12.0, 30.0)},
            [
                [
                    "MyInstance",
                    "java.lang:type=Memory",
                    '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224, "committed": 123207680}, "HeapMemoryUsage": {"max": 536870912, "init": 67108864, "used": 78331216, "committed": 122683392}, "ObjectPendingFinalizationCount": 0, "ObjectName": {"objectName": "java.lang:type=Memory"}, "Verbose": false}',
                ],
                [
                    "MyInstance",
                    "java.lang:name=*,type=MemoryPool",
                    '{"java.lang:name=Metaspace,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Metaspace", "ObjectName": {"objectName": "java.lang:name=Metaspace,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["Metaspace Manager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "PeakUsage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}, "java.lang:name=Code Cache,type=MemoryPool": {"UsageThresholdCount": 0, "CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Name": "Code Cache", "ObjectName": {"objectName": "java.lang:name=Code Cache,type=MemoryPool"}, "UsageThreshold": 0, "CollectionUsageThresholdSupported": false, "UsageThresholdSupported": true, "MemoryManagerNames": ["CodeCacheManager"], "CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "Valid": true, "Usage": {"max": 536870912, "init": 33554432, "used": 370254912, "committed": 373489664}, "PeakUsage": {"max": 536870912, "init": 33554432, "used": 370304384, "committed": 373489664}, "Type": "NON_HEAP", "CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", "CollectionUsage": null, "UsageThresholdExceeded": false}}',
                ],
            ],
            [
                (0, "Heap: 74.7 MiB", [("mem_heap", 78331216, None, None, None, 536870912)]),
                (0, "14.59%", []),
                (0, "Nonheap: 105 MiB", [("mem_nonheap", 110167224, None, None, None, 780140544)]),
                (0, "14.12%", []),
                (0, "Total: 180 MiB", []),
                (1, "14.31% (warn/crit at 12.00%/30.00%)", []),
            ],
        ),
    ],
)
def test_check_jolokia_jvm_memory(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for jolokia_jvm_memory check."""
    parsed = parse_jolokia_jvm_memory(string_table)
    result = list(check_jolokia_jvm_memory(item, params, parsed))
    assert result == expected_results
