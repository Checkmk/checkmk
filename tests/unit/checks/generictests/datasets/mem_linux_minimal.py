# -*- encoding: utf-8
# yapf: disable


checkname = 'mem'


info = [['MemTotal:', '8387564', 'kB'],
        ['MemFree:', '6349060', 'kB'],
        ['Buffers:', '818200', 'kB'],
        ['Cached:', '83280', 'kB'],
        ['SwapCached:', '4', 'kB'],
        ['SwapTotal:', '1310720', 'kB'],
        ['SwapFree:', '1111140', 'kB'],
        ['Dirty:', '644', 'kB'],
        ['Committed_AS:', '2758332', 'kB'],
        ['VmallocTotal:', '34359738367', 'kB'],
        ['VmallocUsed:', '3', 'kB'],
        ['VmallocChunk:', '2', 'kB'],
        ['PageTables:', '7672', 'kB'],
        ['Writeback:', '5', 'kb']]


discovery = {'linux': [(None, {})], 'used': [], 'vmalloc': [], 'win': []}


checks = {'linux': [(None,
                     {'levels_commitlimit': ('perc_free', (20.0, 10.0)),
                      'levels_committed': ('perc_used', (100.0, 150.0)),
                      'levels_hardwarecorrupted': ('abs_used', (1, 1)),
                      'levels_pagetables': ('perc_used', (8.0, 16.0)),
                      'levels_shm': ('perc_used', (20.0, 30.0)),
                      'levels_total': ('perc_used', (120.0, 150.0)),
                      'levels_virtual': ('perc_used', (80.0, 90.0)),
                      'levels_vmalloc': ('abs_free', (52428800, 31457280))},
                     [(0, 'RAM used: 1.08 GB of 8.00 GB', []),
                      (0, 'Swap used: 194.90 MB of 1.25 GB', []),
                      (0,
                       'Total virtual memory used: 1.27 GB of 9.25 GB (13.8%)',
                       []),
                      (2,
                       'Largest Free VMalloc Chunk: 2.00 kB (warn/crit below 50.00 MB/30.00 MB)',
                       []),
                      (0,
                       '',
                       [('buffers', 837836800, None, None, None, None),
                        ('cached', 85278720, None, None, None, None),
                        ('caches', 923119616, None, None, None, None),
                        ('committed_as', 2824531968, None, None, None, None),
                        ('dirty', 659456, None, None, None, None),
                        ('mem_free', 6501437440, None, None, None, None),
                        ('mem_total', 8588865536, None, None, None, None),
                        ('mem_used', 1164308480, None, None, None, None),
                        ('page_tables', 7856128, None, None, None, None),
                        ('pending', 659461, None, None, None, None),
                        ('swap_cached', 4096, None, None, None, None),
                        ('swap_free', 1137807360, None, None, None, None),
                        ('swap_total', 1342177280, None, None, None, None),
                        ('swap_used', 204369920, None, None, None, None),
                        ('total_total', 9931042816, None, None, None, None),
                        ('total_used', 1368678400, None, None, None, None),
                        ('writeback', 5, None, None, None, None)])])]}
