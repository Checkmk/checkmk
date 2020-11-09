#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'mem'

parsed = {
    'MemTotal': 25300574208,
    'MemFree': 451813376,
    'Buffers': 328368128,
    'Cached': 20460552192,
    'SwapCached': 6320128,
    'Active': 8967041024,
    'Inactive': 13681094656,
    'Active(anon)': 1516785664,
    'Inactive(anon)': 380170240,
    'Active(file)': 7450255360,
    'Inactive(file)': 13300924416,
    'Unevictable': 987963392,
    'Mlocked': 987963392,
    'SwapTotal': 17179865088,
    'SwapFree': 17104207872,
    'Dirty': 4513918976,
    'Writeback': 38932480,
    'AnonPages': 2841030656,
    'Mapped': 71122944,
    'Shmem': 34582528,
    'Slab': 881692672,
    'SReclaimable': 774385664,
    'SUnreclaim': 107307008,
    'KernelStack': 4276224,
    'PageTables': 16273408,
    'NFS_Unstable': 0,
    'Bounce': 0,
    'WritebackTmp': 0,
    'CommitLimit': 39950381056,
    'Committed_AS': 3624763392,
    'VmallocTotal': 35184372087808,
    'VmallocUsed': 356253696,
    'VmallocChunk': 0,
    'HardwareCorrupted': 6144,
    'AnonHugePages': 0,
    'HugePages_Total': 0,
    'HugePages_Free': 0,
    'HugePages_Rsvd': 0,
    'HugePages_Surp': 0,
    'Hugepagesize': 2097152,
    'DirectMap4k': 274726912,
    'DirectMap2M': 8306819072,
    'DirectMap1G': 17179869184
}

discovery = {'linux': [(None, {})], 'win': [], 'vmalloc': []}

checks = {
    'linux': [
        (
            None, {
                'levels_virtual': ('perc_used', (80.0, 90.0)),
                'levels_total': ('perc_used', (120.0, 150.0)),
                'levels_shm': ('perc_used', (20.0, 30.0)),
                'levels_pagetables': ('perc_used', (8.0, 16.0)),
                'levels_committed': ('perc_used', (100.0, 150.0)),
                'levels_commitlimit': ('perc_free', (20.0, 10.0)),
                'levels_vmalloc': ('abs_free', (52428800, 31457280)),
                'levels_hardwarecorrupted': ('abs_used', (1, 1))
            }, [
                (0, 'Total virtual memory: 7.9% - 3.12 GB of 39.56 GB', []),
                (
                    2,
                    'Hardware Corrupted: 0.00002% - 6.00 kB of 23.56 GB RAM (warn/crit at 1 B/1 B used)',
                    []
                ),
                (0, '\nRAM: 12.96% - 3.05 GB of 23.56 GB', []),
                (0, '\nSwap: 0.44% - 72.15 MB of 16.00 GB', []),
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
                        (
                            'mem_used_percent', 12.960712642494665, None, None,
                            None, None
                        ), ('mlocked', 987963392, None, None, None, None),
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
        )
    ]
}
