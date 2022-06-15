#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'jolokia_jvm_memory'


info = [
    ['MyInstance', 'java.lang:type=Memory', (
        '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224, "committed": 123207680},'
        ' "HeapMemoryUsage": {"max": 536870912, "init": 67108864, "used": 78331216, "committed": 122683392},'
        ' "ObjectPendingFinalizationCount": 0, "ObjectName": {"objectName": "java.lang:type=Memory"},'
        ' "Verbose": false}'
    )],
    ['MyInstance', 'java.lang:name=*,type=MemoryPool', (
        '{"java.lang:name=Metaspace,type=MemoryPool": {'
            '"UsageThresholdCount": 0, '
            '"CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", '
            '"Name": "Metaspace", '
            '"ObjectName": {"objectName": "java.lang:name=Metaspace,type=MemoryPool"}, '
            '"UsageThreshold": 0, '
            '"CollectionUsageThresholdSupported": false, '
            '"UsageThresholdSupported": true, '
            '"MemoryManagerNames": ["Metaspace Manager"], '
            '"CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", '
            '"Valid": true, '
            '"Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, '
            '"PeakUsage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}, '
            '"Type": "NON_HEAP", '
            '"CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", '
            '"CollectionUsage": null, '
            '"UsageThresholdExceeded": false},'
        ' "java.lang:name=Code Cache,type=MemoryPool": {'
            '"UsageThresholdCount": 0, '
            '"CollectionUsageThreshold": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", '
            '"Name": "Code Cache", '
            '"ObjectName": {"objectName": "java.lang:name=Code Cache,type=MemoryPool"}, '
            '"UsageThreshold": 0, '
            '"CollectionUsageThresholdSupported": false, '
            '"UsageThresholdSupported": true, '
            '"MemoryManagerNames": ["CodeCacheManager"], '
            '"CollectionUsageThresholdCount": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", '
            '"Valid": true, '
            '"Usage": {"max": 536870912, "init": 33554432, "used": 370254912, "committed": 373489664}, '
            '"PeakUsage": {"max": 536870912, "init": 33554432, "used": 370304384, "committed": 373489664}, '
            '"Type": "NON_HEAP", '
            '"CollectionUsageThresholdExceeded": "ERROR: java.lang.UnsupportedOperationException: <...errmsg>", '
            '"CollectionUsage": null, '
            '"UsageThresholdExceeded": false}}'
    )],
]


discovery = {
    '': [
        ('MyInstance', {}),
    ],
    'pools': [
        (u'MyInstance Memory Pool Code Cache', {}),
        (u'MyInstance Memory Pool Metaspace', {}),
    ],
}


checks = {
    '': [
        ('MyInstance', {}, [
            (0, 'Heap: 74.7 MiB', [
                ('mem_heap', 78331216, None, None, None, 536870912),
            ]),
            (0, '14.59%', []),
            (0, 'Nonheap: 105 MiB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', []),
            (0, 'Total: 180 MiB', []),
            (0, '14.31%', []),
        ]),
        ('MyInstance', {'perc_total': (13., 15.)}, [
            (0, 'Heap: 74.7 MiB', [
                ('mem_heap', 78331216, None, None, None, 536870912),
            ]),
            (0, '14.59%', []),
            (0, 'Nonheap: 105 MiB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', []),
            (0, 'Total: 180 MiB', []),
            (1, '14.31% (warn/crit at 13.00%/15.00%)', []),
        ]),
        ('MyInstance', {'abs_heap': (450, 460)}, [
            (2, 'Heap: 74.7 MiB (warn/crit at 450 B/460 B)', [
                ('mem_heap', 78331216, 450.0, 460.0, None, 536870912),
            ]),
            (0, '14.59%', []),
            (0, 'Nonheap: 105 MiB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', []),
            (0, 'Total: 180 MiB', []),
            (0, '14.31%', []),
        ]),
        ('MyInstance', {'perc_total': (12., 30.)}, [
            (0, 'Heap: 74.7 MiB', [
                ('mem_heap', 78331216, None, None, None, 536870912),
            ]),
            (0, '14.59%', [
            ]),
            (0, 'Nonheap: 105 MiB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', [
            ]),
            (0, 'Total: 180 MiB', []),
            (1, '14.31% (warn/crit at 12.00%/30.00%)', []),
        ]),
    ],
    'pools': [
        ('MyInstance Memory Pool Metaspace', {'abs_used': (400*1024*1024, 500*1024*1024)}, [
            (1, 'Used: 442 MiB (warn/crit at 400 MiB/500 MiB)', [
                ('mem_used', 463555784, 419430400.0, 524288000.0, None, None)]),
            (0, 'Initially: 0 B', []),
            (0, 'Committed: 501 MiB', []),
        ]),
        ('MyInstance Memory Pool Metaspace', {'perc_used': (1, 2)}, [
            (0, 'Used: 442 MiB', [('mem_used', 463555784, None, None, None, None)]),
            (0, 'Initially: 0 B', []),
            (0, 'Committed: 501 MiB', []),
        ]),
        ('MyInstance Memory Pool Code Cache', {'abs_used': (200*1024*1024, 300*1024*1024)}, [
            (2, 'Used: 353 MiB (warn/crit at 200 MiB/300 MiB)', [
                ('mem_used', 370254912, 209715200.0, 314572800.0, None, 536870912.0)]),
            (0, '68.97%', []),
            (0, 'Initially: 32.0 MiB', []),
            (0, 'Committed: 356 MiB', []),
        ]),
        ('MyInstance Memory Pool Code Cache', {'perc_used': (60, 70)}, [
            (0, 'Used: 353 MiB', [
                ('mem_used', 370254912, None, None, None, 536870912.0)]),
            (1, '68.97% (warn/crit at 60.00%/70.00%)', []),
            (0, 'Initially: 32.0 MiB', []),
            (0, 'Committed: 356 MiB', []),
        ]),
    ],
}
