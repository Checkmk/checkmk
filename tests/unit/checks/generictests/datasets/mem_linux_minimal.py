#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'mem'

parsed = {
    'MemTotal': 8588865536,
    'MemFree': 6501437440,
    'Buffers': 837836800,
    'Cached': 85278720,
    'SwapCached': 4096,
    'SwapTotal': 1342177280,
    'SwapFree': 1137807360,
    'Dirty': 659456,
    'Committed_AS': 2824531968,
    'VmallocTotal': 35184372087808,
    'VmallocUsed': 3072,
    'VmallocChunk': 2048,
    'PageTables': 7856128,
    'Writeback': 5
}

discovery = {'win': [], 'used': [], 'vmalloc': [], 'linux': [(None, {})]}

checks = {
    'linux': [
        (
            None, {
                'levels_commitlimit': ('perc_free', (20.0, 10.0)),
                'levels_virtual': ('perc_used', (80.0, 90.0)),
                'levels_committed': ('perc_used', (100.0, 150.0)),
                'levels_pagetables': ('perc_used', (8.0, 16.0)),
                'levels_total': ('perc_used', (120.0, 150.0)),
                'levels_shm': ('perc_used', (20.0, 30.0)),
                'levels_vmalloc': ('abs_free', (52428800, 31457280)),
                'levels_hardwarecorrupted': ('abs_used', (1, 1))
            }, [
                (0, 'Total virtual memory: 13.78% - 1.27 GiB of 9.25 GiB', []),
                (
                    2,
                    'Largest Free VMalloc Chunk: 0% free - 2.00 KiB of 32.0 TiB VMalloc Area (warn/crit below 50.0 MiB/30.0 MiB free)',
                    []
                ),
                (
                    0, '\nRAM: 13.56% - 1.08 GiB of 8.00 GiB', [
                        ('mem_used', 1164308480, None, None, 0, 8588865536),
                        (
                            'mem_used_percent', 13.556021748388446, None, None,
                            0.0, None
                        )
                    ]
                ),
                (
                    0, '\nSwap: 15.23% - 195 MiB of 1.25 GiB', [
                        ('swap_used', 204369920, None, None, 0, 1342177280)
                    ]
                ),
                (
                    0,
                    '\nCommitted: 28.44% - 2.63 GiB of 9.25 GiB virtual memory',
                    [
                        (
                            'mem_lnx_committed_as', 2824531968, 9931042816.0,
                            14896564224.0, 0, 9931042816
                        )
                    ]
                ),
                (
                    0, '\nPage tables: 0.09% - 7.49 MiB of 8.00 GiB RAM', [
                        (
                            'mem_lnx_page_tables', 7856128, 687109242.88,
                            1374218485.76, 0, 8588865536
                        )
                    ]
                ),
                (0, '\nDisk Writeback: 0.008% - 644 KiB of 8.00 GiB RAM', []),
                (
                    0, '', [
                        ('buffers', 837836800, None, None, None, None),
                        ('cached', 85278720, None, None, None, None),
                        ('caches', 923119616, None, None, None, None),
                        ('dirty', 659456, None, None, None, None),
                        ('mem_free', 6501437440, None, None, None, None),
                        ('mem_total', 8588865536, None, None, None, None),
                        ('pending', 659461, None, None, None, None),
                        ('swap_cached', 4096, None, None, None, None),
                        ('swap_free', 1137807360, None, None, None, None),
                        ('swap_total', 1342177280, None, None, None, None),
                        ('total_total', 9931042816, None, None, None, None),
                        ('total_used', 1368678400, None, None, None, None),
                        ('writeback', 5, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            None, {
                'levels_virtual': ('perc_used', (80.0, 90.0)),
                'levels_shm': ('perc_used', (20.0, 30.0)),
                'levels_pagetables': ('perc_used', (8.0, 16.0)),
                'levels_committed': ('perc_used', (100.0, 150.0)),
                'levels_commitlimit': ('perc_free', (20.0, 10.0)),
                'levels_vmalloc': ('abs_free', (52428800, 31457280)),
                'levels_hardwarecorrupted': ('abs_used', (1, 1))
            }, [
                (0, 'Total virtual memory: 13.78% - 1.27 GiB of 9.25 GiB', []),
                (
                    2,
                    'Largest Free VMalloc Chunk: 0% free - 2.00 KiB of 32.0 TiB VMalloc Area (warn/crit below 50.0 MiB/30.0 MiB free)',
                    []
                ),
                (
                    0, '\nRAM: 13.56% - 1.08 GiB of 8.00 GiB', [
                        ('mem_used', 1164308480, None, None, 0, 8588865536),
                        (
                            'mem_used_percent', 13.556021748388446, None, None,
                            0.0, None
                        )
                    ]
                ),
                (
                    0, '\nSwap: 15.23% - 195 MiB of 1.25 GiB', [
                        ('swap_used', 204369920, None, None, 0, 1342177280)
                    ]
                ),
                (
                    0,
                    '\nCommitted: 28.44% - 2.63 GiB of 9.25 GiB virtual memory',
                    [
                        (
                            'mem_lnx_committed_as', 2824531968, 9931042816.0,
                            14896564224.0, 0, 9931042816
                        )
                    ]
                ),
                (
                    0, '\nPage tables: 0.09% - 7.49 MiB of 8.00 GiB RAM', [
                        (
                            'mem_lnx_page_tables', 7856128, 687109242.88,
                            1374218485.76, 0, 8588865536
                        )
                    ]
                ),
                (0, '\nDisk Writeback: 0.008% - 644 KiB of 8.00 GiB RAM', []),
                (
                    0, '', [
                        ('buffers', 837836800, None, None, None, None),
                        ('cached', 85278720, None, None, None, None),
                        ('caches', 923119616, None, None, None, None),
                        ('dirty', 659456, None, None, None, None),
                        ('mem_free', 6501437440, None, None, None, None),
                        ('mem_total', 8588865536, None, None, None, None),
                        ('pending', 659461, None, None, None, None),
                        ('swap_cached', 4096, None, None, None, None),
                        ('swap_free', 1137807360, None, None, None, None),
                        ('swap_total', 1342177280, None, None, None, None),
                        ('total_total', 9931042816, None, None, None, None),
                        ('total_used', 1368678400, None, None, None, None),
                        ('writeback', 5, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
