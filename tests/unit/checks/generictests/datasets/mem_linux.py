# -*- encoding: utf-8
# yapf: disable
checkname = 'mem'

info = [
    ['MemTotal:', '24707592', 'kB'], ['MemFree:', '441224', 'kB'],
    ['Buffers:', '320672', 'kB'], ['Cached:', '19981008', 'kB'],
    ['SwapCached:', '6172', 'kB'], ['Active:', '8756876', 'kB'],
    ['Inactive:', '13360444', 'kB'], ['Active(anon):', '1481236', 'kB'],
    ['Inactive(anon):', '371260', 'kB'], ['Active(file):', '7275640', 'kB'],
    ['Inactive(file):', '12989184', 'kB'], ['Unevictable:', '964808', 'kB'],
    ['Mlocked:', '964808', 'kB'], ['SwapTotal:', '16777212', 'kB'],
    ['SwapFree:', '16703328', 'kB'], ['Dirty:', '4408124', 'kB'],
    ['Writeback:', '38020', 'kB'], ['AnonPages:', '2774444', 'kB'],
    ['Mapped:', '69456', 'kB'], ['Shmem:', '33772', 'kB'],
    ['Slab:', '861028', 'kB'], ['SReclaimable:', '756236', 'kB'],
    ['SUnreclaim:', '104792', 'kB'], ['KernelStack:', '4176', 'kB'],
    ['PageTables:', '15892', 'kB'], ['NFS_Unstable:', '0', 'kB'],
    ['Bounce:', '0', 'kB'], ['WritebackTmp:', '0', 'kB'],
    ['CommitLimit:', '39014044', 'kB'], ['Committed_AS:', '3539808', 'kB'],
    ['VmallocTotal:', '34359738367', 'kB'], ['VmallocUsed:', '347904', 'kB'],
    ['VmallocChunk:', '34346795572', 'kB'], ['HardwareCorrupted:', '6', 'kB'],
    ['AnonHugePages:', '0', 'kB'], ['HugePages_Total:', '0'],
    ['HugePages_Free:', '0'], ['HugePages_Rsvd:', '0'],
    ['HugePages_Surp:', '0'], ['Hugepagesize:', '2048', 'kB'],
    ['DirectMap4k:', '268288', 'kB'], ['DirectMap2M:', '8112128', 'kB'],
    ['DirectMap1G:', '16777216', 'kB']
]

discovery = {'win': [], 'used': [], 'vmalloc': [], 'linux': [(None, {})]}

checks = {
    'linux': [
        (
            None, {
                'levels_total': ('perc_used', (120.0, 150.0)),
                'levels_shm': ('perc_used', (20.0, 30.0)),
                'levels_commitlimit': ('perc_free', (20.0, 10.0)),
                'levels_virtual': ('perc_used', (80.0, 90.0)),
                'levels_vmalloc': ('abs_free', (52428800, 31457280)),
                'levels_hardwarecorrupted': ('abs_used', (5, 10)),
                'levels_committed': ('perc_used', (100.0, 150.0)),
                'levels_pagetables': ('perc_used', (8.0, 16.0))
            }, [
                (0, 'Total virtual memory: 7.9% - 3.12 GB of 39.56 GB', []),
                (0, 'RAM: 12.96% - 3.05 GB of 23.56 GB', []),
                (0, 'Swap: 0.44% - 72.15 MB of 16.00 GB', []),
                (
                    2,
                    'Hardware Corrupted: 0.00002% - 6.00 kB of 23.56 GB RAM (warn/crit at 5.00 B/10.00 B used)',
                    []
                ),
                (
                    0, '', [
                        ('active', 8967041024, None, None, None, None),
                        ('active_anon', 1516785664, None, None, None, None),
                        ('active_file', 7450255360, None, None, None, None),
                        ('anon_huge_pages', 0, None, None, None, None),
                        ('anon_pages', 2841030656, None, None, None, None),
                        ('bounce', 0, None, None, None, None),
                        ('buffers', 328368128, None, None, None, None),
                        ('cached', 20460552192, None, None, None, None),
                        ('caches', 21569626112, None, None, None, None),
                        ('commit_limit', 39950381056, None, None, None, None),
                        ('committed_as', 3624763392, None, None, None, None),
                        ('dirty', 4513918976, None, None, None, None),
                        ('hardware_corrupted', 6144, None, None, None, None),
                        ('inactive', 13681094656, None, None, None, None),
                        ('inactive_anon', 380170240, None, None, None, None),
                        ('inactive_file', 13300924416, None, None, None, None),
                        ('kernel_stack', 4276224, None, None, None, None),
                        ('mapped', 71122944, None, None, None, None),
                        ('mem_free', 451813376, None, None, None, None),
                        ('mem_total', 25300574208, None, None, None, None),
                        ('mem_used', 3279134720, None, None, None, None),
                        ('mlocked', 987963392, None, None, None, None),
                        ('nfs_unstable', 0, None, None, None, None),
                        ('page_tables', 16273408, None, None, None, None),
                        ('pending', 4552851456, None, None, None, None),
                        ('sreclaimable', 774385664, None, None, None, None),
                        ('sunreclaim', 107307008, None, None, None, None),
                        ('shmem', 34582528, None, None, None, None),
                        ('slab', 881692672, None, None, None, None),
                        ('swap_cached', 6320128, None, None, None, None),
                        ('swap_free', 17104207872, None, None, None, None),
                        ('swap_total', 17179865088, None, None, None, None),
                        ('swap_used', 75657216, None, None, None, None),
                        ('total_total', 42480439296, None, None, None, None),
                        ('total_used', 3354791936, None, None, None, None),
                        ('unevictable', 987963392, None, None, None, None),
                        ('writeback', 38932480, None, None, None, None),
                        ('writeback_tmp', 0, None, None, None, None)
                    ]
                )
            ]
        ),
    ]
}
