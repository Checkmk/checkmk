#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.docker_container_mem_cgroupv2 import parse_docker_container_mem_cgroupv2

# 16GB RAM
AGENT_OUTPUT_NO_LIMIT = """anon 5406720
file 87994368
kernel_stack 110592
slab 15613952
sock 94208
shmem 0
file_mapped 6893568
file_dirty 135168
file_writeback 135168
anon_thp 0
inactive_anon 0
active_anon 5406720
inactive_file 47038464
active_file 41226240
unevictable 0
slab_reclaimable 10260480
slab_unreclaimable 5353472
pgfault 173349
pgmajfault 132
workingset_refault 0
workingset_activate 0
workingset_restore 0
workingset_nodereclaim 0
pgrefill 0
pgscan 0
pgsteal 0
pgactivate 9636
pgdeactivate 0
pglazyfree 0
pglazyfreed 0
thp_fault_alloc 0
thp_collapse_alloc 0
memory.current 110198784
memory.max max
MemTotal: 16202704 kB
"""

# --memory 9000000
AGENT_OUTPUT_LIMIT = """anon 1757184
file 0
kernel_stack 110592
slab 1441792
sock 0
shmem 0
file_mapped 0
file_dirty 0
file_writeback 0
anon_thp 0
inactive_anon 0
active_anon 1892352
inactive_file 0
active_file 0
unevictable 0
slab_reclaimable 139264
slab_unreclaimable 1302528
pgfault 4818
pgmajfault 0
workingset_refault 0
workingset_activate 0
workingset_restore 0
workingset_nodereclaim 0
pgrefill 0
pgscan 0
pgsteal 0
pgactivate 0
pgdeactivate 0
pglazyfree 0
pglazyfreed 0
thp_fault_alloc 0
thp_collapse_alloc 0
memory.current 4718592
memory.max 8998912
MemTotal: 16202704 kB
"""


def test_docker_parse_container_mem_cgroupv2_no_limit():
    string_table = [line.split(" ") for line in AGENT_OUTPUT_NO_LIMIT.split("\n")]
    assert parse_docker_container_mem_cgroupv2(string_table) == {
        "MemTotal": 16202704 * 1024,
        "MemFree": 16202704 * 1024 - (110198784 - 47038464),
    }


def test_docker_parse_container_mem_cgroupv2_limit():
    string_table = [line.split(" ") for line in AGENT_OUTPUT_LIMIT.split("\n")]
    assert parse_docker_container_mem_cgroupv2(string_table) == {
        "MemTotal": 8998912,
        "MemFree": 8998912 - 4718592,
    }
