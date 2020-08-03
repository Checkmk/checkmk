#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
    BEWARE: half of the information and blob entries about /proc/meminfo
    in the internet is unprecise or even totally wrong!

    <<<mem>>>
    MemTotal:       24707592 kB
    MemFree:          441224 kB
    Buffers:          320672 kB
    Cached:         19981008 kB
    SwapCached:         6172 kB
    Active:          8756876 kB
    Inactive:       13360444 kB
    Active(anon):    1481236 kB
    Inactive(anon):   371260 kB
    Active(file):    7275640 kB
    Inactive(file): 12989184 kB
    Unevictable:      964808 kB
    Mlocked:          964808 kB
    SwapTotal:      16777212 kB
    SwapFree:       16703328 kB
    Dirty:           4408124 kB
    Writeback:         38020 kB
    AnonPages:       2774444 kB
    Mapped:            69456 kB
    Shmem:             33772 kB
    Slab:             861028 kB
    SReclaimable:     756236 kB
    SUnreclaim:       104792 kB
    KernelStack:        4176 kB
    PageTables:        15892 kB
    NFS_Unstable:          0 kB
    Bounce:                0 kB
    WritebackTmp:          0 kB
    CommitLimit:    39014044 kB
    Committed_AS:    3539808 kB
    VmallocTotal:   34359738367 kB
    VmallocUsed:      347904 kB
    VmallocChunk:   34346795572 kB
    HardwareCorrupted:     0 kB
    AnonHugePages:         0 kB
    HugePages_Total:       0
    HugePages_Free:        0
    HugePages_Rsvd:        0
    HugePages_Surp:        0
    Hugepagesize:       2048 kB
    DirectMap4k:      268288 kB
    DirectMap2M:     8112128 kB
    DirectMap1G:    16777216 kB

    This is from an earlier kernel (CentOS 5.5). Some entries
    are missing here:
    <<<mem>>>
    MemTotal:       377176 kB
    MemFree:         60112 kB
    Buffers:         93864 kB
    Cached:         116364 kB
    SwapCached:          0 kB
    Active:         169140 kB
    Inactive:        84144 kB
    HighTotal:           0 kB
    HighFree:            0 kB
    LowTotal:       377176 kB
    LowFree:         60112 kB
    SwapTotal:     2064376 kB
    SwapFree:      2062756 kB
    Dirty:             172 kB
    Writeback:           0 kB
    AnonPages:       43080 kB
    Mapped:           8352 kB
    Slab:            45892 kB
    PageTables:       3208 kB
    NFS_Unstable:        0 kB
    Bounce:              0 kB
    CommitLimit:   2252964 kB
    Committed_AS:   125968 kB
    VmallocTotal: 34359738367 kB
    VmallocUsed:     18112 kB
    VmallocChunk: 34359719415 kB
    HugePages_Total:     0
    HugePages_Free:      0
    HugePages_Rsvd:      0
    Hugepagesize:     2048 kB

    Yet earlier kernel (SLES 9):
    <<<mem>>>
    MemTotal: 6224268 kB
    MemFree: 2913660 kB
    Buffers: 84712 kB
    Cached: 1779052 kB
    SwapCached: 0 kB
    Active: 1931528 kB
    Inactive: 1276156 kB
    HighTotal: 5373824 kB
    HighFree: 2233984 kB
    LowTotal: 850444 kB
    LowFree: 679676 kB
    SwapTotal: 1052280 kB
    SwapFree: 1052280 kB
    Dirty: 55680 kB
    Writeback: 0 kB
    Mapped: 1469268 kB
    Slab: 71724 kB
    Committed_AS: 2758332 kB
    PageTables: 7672 kB
    VmallocTotal: 112632 kB
    VmallocUsed: 9324 kB
    VmallocChunk: 103180 kB
    HugePages_Total: 0
    HugePages_Free: 0
    Hugepagesize: 2048 kB

"""
from typing import Dict, Optional
from .agent_based_api.v0 import register, type_defs


def parse_proc_meminfo_bytes(string_table: type_defs.AgentStringTable) -> Optional[Dict[str, int]]:
    """Parse /proc/meminfo into the canonical form: into bytes

        >>> import pprint
        >>> section = parse_proc_meminfo_bytes([
        ...     ['MemTotal:', '377176', 'kB'],
        ...     ['MemFree:', '60112', 'kB'],
        ...     ['Buffers:', '93864', 'kB'],
        ...     ['Cached:', '116364', 'kB'],
        ...     ['SwapCached:', '0', 'kB'],
        ... ])
        >>> pprint.pprint(section)
        {'Buffers': 96116736,
         'Cached': 119156736,
         'MemFree': 61554688,
         'MemTotal': 386228224,
         'SwapCached': 0}

    """

    section = {}
    for line in string_table:
        value = int(line[1])
        if len(line) > 2 and line[2] == 'kB':
            value *= 1024
        section[line[0][:-1]] = value
    return section or None


register.agent_section(
    name="mem",
    parse_function=parse_proc_meminfo_bytes,
)
