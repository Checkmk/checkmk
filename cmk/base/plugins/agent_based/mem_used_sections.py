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

from .agent_based_api.v1 import register, type_defs
from .utils.memory import SectionMemUsed


def parse_aix_memory(string_table: type_defs.StringTable) -> Optional[SectionMemUsed]:
    """Parse AIX vmstat output into something compatible with the Linux output of /proc/meminfo

    AIX speaks of 4k pages while Linux of kilobytes.

        >>> import pprint
        >>> section = parse_aix_memory([
        ...   ['32702464', 'memory', 'pages'],
        ...   ['31736528', 'lruable', 'pages'],
        ...   ['858141', 'free', 'pages'],
        ...   ['4', 'memory', 'pools'],
        ...   ['6821312', 'pinned', 'pages'],
        ...   ['80.0', 'maxpin', 'percentage'],
        ...   ['3.0', 'minperm', 'percentage'],
        ...   ['90.0', 'maxperm', 'percentage'],
        ...   ['8.8', 'numperm', 'percentage'],
        ...   ['2808524', 'file', 'pages'],
        ...   ['0.0', 'compressed', 'percentage'],
        ...   ['0', 'compressed', 'pages'],
        ...   ['8.8', 'numclient', 'percentage'],
        ...   ['90.0', 'maxclient', 'percentage'],
        ...   ['2808524', 'client', 'pages'],
        ...   ['0', 'remote', 'pageouts', 'scheduled'],
        ...   ['354', 'pending', 'disk', 'I/Os', 'blocked', 'with', 'no', 'pbuf'],
        ...   ['860832', 'paging', 'space', 'I/Os', 'blocked', 'with', 'no', 'psbuf'],
        ...   ['2228', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
        ...   ['508', 'client', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
        ...   ['1372', 'external', 'pager', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
        ...   ['88.8', 'percentage', 'of', 'memory', 'used', 'for', 'computational', 'pages'],
        ...   ['allocated', '=', '8257536', 'blocks', 'used', '=', '1820821', 'blocks', 'free',
        ...    '=', '6436715', 'blocks'],
        ... ])
        >>> pprint.pprint(section)
        {'Cached': 11503714304,
         'MemFree': 3514945536,
         'MemTotal': 133949292544,
         'SwapFree': 26364784640,
         'SwapTotal': 33822867456}

    """
    k4 = 4 * 1024
    section: SectionMemUsed = {}
    for line in string_table:
        if line[0] == "allocated":  # Swap space
            section["SwapTotal"] = int(line[2]) * k4
            section["SwapFree"] = int(line[10]) * k4
        else:
            varname = " ".join(line[1:])
            if varname == "memory pages":
                section["MemTotal"] = int(line[0]) * k4
            elif varname == "free pages":
                section["MemFree"] = int(line[0]) * k4
            elif varname == "file pages":
                section["Cached"] = int(line[0]) * k4
    return section


register.agent_section(
    name="aix_memory",
    parsed_section_name="mem_used",
    parse_function=parse_aix_memory,
)


def parse_solaris_mem(string_table: type_defs.StringTable) -> Optional[SectionMemUsed]:
    """
    >>> import pprint
    >>> test = 'Memory: 512M phys mem, 353M free mem, 2000M total swap, 2000M free swap'
    >>> section = parse_solaris_mem([test.split()])
    >>> pprint.pprint(section)
    {'MemFree': 370147328,
     'MemTotal': 536870912,
     'SwapFree': 2097152000,
     'SwapTotal': 2097152000}

    """
    # The 1.2.4 agent seems to create an empty section under some circumstances
    if not string_table:
        return None

    units = {"G": 1024**3, "M": 1024**2, "K": 1024}

    values = []
    mem_tokens = " ".join(string_table[0][1:]).split(",")
    is_total_swap = False
    for token in mem_tokens:
        if "total swap" in token:
            is_total_swap = True
        raw_value = token.split()[0]
        values.append(int(raw_value[:-1]) * units[raw_value[-1]])

    # convert swap-in-use to swap-total, as expected by check_memory()
    if not is_total_swap:
        values[2] = values[2] + values[3]

    return {
        "MemTotal": values[0],
        "MemFree": values[1],
        "SwapTotal": values[2],
        "SwapFree": values[3],
    }


register.agent_section(
    name="solaris_mem",
    parsed_section_name="mem_used",
    parse_function=parse_solaris_mem,
)


def parse_statgrab_mem(string_table: type_defs.StringTable) -> Optional[SectionMemUsed]:
    """
    >>> import pprint
    >>> pprint.pprint(parse_statgrab_mem([
    ...     ['mem.cache', '0'],
    ...     ['mem.total', '4294967296'],
    ...     ['mem.free', '677666816'],
    ...     ['mem.used', '3617300480'],
    ...     ['swap.total', '8589934592'],
    ...     ['swap.free', '4976402432'],
    ...     ['swap.used', '3613532160']
    ... ]))
    {'Cached': 0,
     'MemFree': 677666816,
     'MemTotal': 4294967296,
     'SwapFree': 4976402432,
     'SwapTotal': 8589934592}

    """
    parsed: Dict[str, int] = {}
    for var, value in string_table:
        try:
            parsed.setdefault(var, int(value))
        except ValueError:
            pass

    try:
        totalmem = parsed["mem.total"]
        memused = parsed["mem.used"]
        totalswap = parsed["swap.total"]
        swapused = parsed["swap.used"]
    except KeyError:
        return None

    section: SectionMemUsed = {
        "MemTotal": totalmem,
        "MemFree": totalmem - memused,
        "SwapTotal": totalswap,
        "SwapFree": totalswap - swapused,
    }
    if "mem.cache" in parsed:
        section["Cached"] = parsed["mem.cache"]

    return section


register.agent_section(
    name="statgrab_mem",
    parsed_section_name="mem_used",
    parse_function=parse_statgrab_mem,
    supersedes=["ucd_mem"],
)


def parse_openbsd_mem(string_table: type_defs.StringTable) -> Optional[SectionMemUsed]:
    units = {"kB": 1024}

    try:
        mem_data = {k.strip(":"): int(v) * units[u] for k, v, u in string_table}
    except ValueError:
        return None

    if set(mem_data) != {"MemTotal", "MemFree", "SwapTotal", "SwapFree"}:
        return None

    return {
        "MemTotal": mem_data["MemTotal"],
        "MemFree": mem_data["MemFree"],
        "SwapTotal": mem_data["SwapTotal"],
        "SwapFree": mem_data["SwapFree"],
    }


register.agent_section(
    name="openbsd_mem",
    parsed_section_name="mem_used",
    parse_function=parse_openbsd_mem,
)
