# -*- encoding: utf-8
# yapf: disable
checkname = 'jolokia_metrics'

freeze_time = '2019-10-10 20:38:55'

info = [
    ['MyInstance', 'NonHeapMemoryUsage', '101078952'],
    ['MyInstance', 'NonHeapMemoryMax', '184549376'],
    ['MyInstance', 'HeapMemoryUsage', '2362781664'],
    ['MyInstance', 'HeapMemoryMax', '9544663040'],
    ['MyInstance', 'ThreadCount', '78'],
    ['MyInstance', 'DeamonThreadCount', '72'],
    ['MyInstance', 'PeakThreadCount', '191'],
    ['MyInstance', 'TotalStartedThreadCount', '941'],
    ['MyInstance', 'Uptime', '572011375'],
    [
        'MyInstance,java.lang:name=PS_MarkSweep,type=GarbageCollector',
        'CollectionCount', '66'
    ],
    [
        'MyInstance,java.lang:name=PS_Scavenge,type=GarbageCollector',
        'CollectionCount', '51203'
    ],
    [
        'MyInstance,java.lang:name=PS_MarkSweep,type=GarbageCollector',
        'CollectionTime', '115326'
    ],
    [
        'MyInstance,java.lang:name=PS_Scavenge,type=GarbageCollector',
        'CollectionTime', '5710533'
    ]
]

discovery = {
    'app_state': [],
    'off_heap': [],
    'mem': [('MyInstance', {})],
    'bea_threads': [],
    'app_sess': [],
    'writer': [],
    'uptime': [('MyInstance', None)],
    'tp': [],
    'bea_requests': [],
    'perm_gen': [],
    'bea_queue': [],
    'threads': [],
    'serv_req': [],
    'cache_hits': [],
    'in_memory': [],
    'gc':
    [('MyInstance GC PS_MarkSweep', {}), ('MyInstance GC PS_Scavenge', {})],
    'requests': [],
    'bea_sess': [],
    'on_disk': []
}

checks = {
    'mem': [
        (
            'MyInstance', {}, [
                (
                    0,
                    'Heap: 2253MB/24.8% used, Nonheap: 96MB/54.8% used, Total: 2350MB/25.3% used',
                    [
                        ('heap', 2253.324188232422, None, None, None, 9102.5),
                        (
                            'nonheap', 96.39640045166016, None, None, None,
                            176.0
                        )
                    ]
                )
            ]
        )
    ],
    'uptime': [
        (
            'MyInstance', {}, [
                (
                    0,
                    'Up since Fri Oct  4 07:45:24 2019, uptime: 6 days, 14:53:31',
                    [('uptime', 572011, None, None, None, None)]
                )
            ]
        )
    ],
    'gc': [
        (
            'MyInstance GC PS_MarkSweep', {}, [
                (
                    0, '0.00 GC Count/minute', [
                        ('CollectionCount', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, '0.00 GC ms/minute', [
                        ('CollectionTime', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'MyInstance GC PS_Scavenge', None, [
                (
                    0, '0.00 GC Count/minute', [
                        ('CollectionCount', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, '0.00 GC ms/minute', [
                        ('CollectionTime', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'MyInstance GC PS_MarkSweep', {
                'CollectionCount': (-1, 1)
            }, [
                (
                    1, '0.00 GC Count/minute (Level -1) ', [
                        ('CollectionCount', 0.0, -1, 1, None, None)
                    ]
                ),
                (
                    0, '0.00 GC ms/minute', [
                        ('CollectionTime', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'MyInstance GC PS_Scavenge', {
                'collection_time':
                (-0.0016666666666666668, 0.0033333333333333335)
            }, [
                (
                    0, '0.00 GC Count/minute', [
                        ('CollectionCount', 0.0, None, None, None, None)
                    ]
                ),
                (
                    1, '0.00 GC ms/minute(Level -1.0) ', [
                        ('CollectionTime', 0.0, -1.0, 2.0, None, None)
                    ]
                )
            ]
        ),
        (
            'MyInstance GC PS_Scavenge', {}, [
                (
                    0, '0.00 GC Count/minute', [
                        ('CollectionCount', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, '0.00 GC ms/minute', [
                        ('CollectionTime', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
