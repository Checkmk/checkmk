# -*- encoding: utf-8
# yapf: disable


checkname = 'jolokia_metrics'


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
    ['MyInstance,java.lang:name=PS_MarkSweep,type=GarbageCollector', 'CollectionCount', '0'],
]


discovery = {
    'app_sess': [],
    'app_state': [],
    'bea_queue': [],
    'bea_requests': [],
    'bea_sess': [],
    'bea_threads': [],
    'cache_hits': [],
    'gc': [('MyInstance GC PS_MarkSweep', {})],
    'in_memory': [],
    'mem': [('MyInstance', {})],
    'off_heap': [],
    'on_disk': [],
    'perm_gen': [],
    'requests': [],
    'serv_req': [],
    'threads': [],
    'tp': [],
    'uptime': [('MyInstance', None)],
    'writer': []}


checks = {  # this is just a test for mem.
    'mem': [
        ('MyInstance', {}, [
            (0, 'Heap: 2253MB/24.8% used, Nonheap: 96MB/54.8% used, Total: 2350MB/25.3% used', [
                ('heap', 2253.324188232422, None, None, None, 9102.5),
                ('nonheap', 96.39640045166016, None, None, None, 176.0),
            ]),
        ]),
    ],
}
