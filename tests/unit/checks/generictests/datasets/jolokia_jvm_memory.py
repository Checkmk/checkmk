# -*- encoding: utf-8
# yapf: disable


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
            (0, 'Heap: 74.70 MB', [
                ('mem_heap', 78331216, None, None, None, 536870912),
            ]),
            (0, '14.59%', []),
            (0, 'Nonheap: 105.06 MB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', []),
            (0, 'Total: 179.77 MB', []),
            (0, '14.31%', []),
        ]),
        ('MyInstance', {'perc_total': (13., 15.)}, [
            (0, 'Heap: 74.70 MB', [
                ('mem_heap', 78331216, None, None, None, 536870912),
            ]),
            (0, '14.59%', []),
            (0, 'Nonheap: 105.06 MB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', []),
            (0, 'Total: 179.77 MB', []),
            (1, '14.31% (warn/crit at 13.0%/15.0%)', []),
        ]),
        ('MyInstance', {'abs_heap': (450, 460)}, [
            (2, 'Heap: 74.70 MB (warn/crit at 450.00 B/460.00 B)', [
                ('mem_heap', 78331216, 450.0, 460.0, None, 536870912),
            ]),
            (0, '14.59%', []),
            (0, 'Nonheap: 105.06 MB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', []),
            (0, 'Total: 179.77 MB', []),
            (0, '14.31%', []),
        ]),
        ('MyInstance', {'perc_total': (12., 30.)}, [
            (0, 'Heap: 74.70 MB', [
                ('mem_heap', 78331216, None, None, None, 536870912),
            ]),
            (0, '14.59%', [
            ]),
            (0, 'Nonheap: 105.06 MB', [
                ('mem_nonheap', 110167224, None, None, None, 780140544),
            ]),
            (0, '14.12%', [
            ]),
            (0, 'Total: 179.77 MB', []),
            (1, '14.31% (warn/crit at 12.0%/30.0%)', []),
        ]),
    ],
    'pools': [
        ('MyInstance Memory Pool Metaspace', {'abs_used': (400*1024*1024, 500*1024*1024)}, [
            (1, 'Used: 442.08 MB (warn/crit at 400.00 MB/500.00 MB)', [
                ('mem_used', 463555784, 419430400.0, 524288000.0, None, None)]),
            (0, 'Initially: 0.00 B', []),
            (0, 'Committed: 500.88 MB', []),
        ]),
        ('MyInstance Memory Pool Metaspace', {'perc_used': (1, 2)}, [
            (0, 'Used: 442.08 MB', [('mem_used', 463555784, None, None, None, None)]),
            (0, 'Initially: 0.00 B', []),
            (0, 'Committed: 500.88 MB', []),
        ]),
        ('MyInstance Memory Pool Code Cache', {'abs_used': (200*1024*1024, 300*1024*1024)}, [
            (2, 'Used: 353.10 MB (warn/crit at 200.00 MB/300.00 MB)', [
                ('mem_used', 370254912, 209715200.0, 314572800.0, None, 536870912.0)]),
            (0, '68.97%', []),
            (0, 'Initially: 32.00 MB', []),
            (0, 'Committed: 356.19 MB', []),
        ]),
        ('MyInstance Memory Pool Code Cache', {'perc_used': (60, 70)}, [
            (0, 'Used: 353.10 MB', [
                ('mem_used', 370254912, None, None, None, 536870912.0)]),
            (1, '68.97% (warn/crit at 60.0%/70.0%)', []),
            (0, 'Initially: 32.00 MB', []),
            (0, 'Committed: 356.19 MB', []),
        ]),
    ],
}
