#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.docker_container_mem import parse_docker_container_mem
from cmk.base.plugins.agent_based.docker_container_mem_cgroupv2 import (
    parse_docker_container_mem_cgroupv2,  # yapf: disable
)

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

PLUGIN_OUTPUT_CGROUPV2 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"usage": 30220288, "stats": {"active_anon": 69632, "active_file": 11534336, "anon": 0, "ano'
        'n_thp": 0, "file": 14868480, "file_dirty": 270336, "file_mapped": 1622016, "file_writeback":'
        '270336, "inactive_anon": 270336, "inactive_file": 2895872, "kernel_stack": 36864, "pgactivat'
        'e": 69234, "pgdeactivate": 3472, "pgfault": 91221240, "pglazyfree": 4554, "pglazyfreed": 0, '
        '"pgmajfault": 66, "pgrefill": 4188, "pgscan": 1057, "pgsteal": 1059, "shmem": 0, "slab": 165'
        '31456, "slab_reclaimable": 3469312, "slab_unreclaimable": 13062144, "sock": 0, "thp_collapse'
        '_alloc": 0, "thp_fault_alloc": 0, "unevictable": 0, "workingset_activate": 231, "workingset_'
        'nodereclaim": 0, "workingset_refault": 231}, "limit": 16591540224}'
    ],
]

PLUGIN_OUTPUT_CGROUPV2_LIMIT = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"usage": 3112960, "stats": {"active_anon": 0, "active_file": 0, "anon": 0, "anon_thp": 0, "'
        'file": 946176, "file_dirty": 0, "file_mapped": 405504, "file_writeback": 0, "inactive_anon":'
        '0, "inactive_file": 946176, "kernel_stack": 110592, "pgactivate": 0, "pgdeactivate": 0, "pgf'
        'ault": 6237, "pglazyfree": 0, "pglazyfreed": 0, "pgmajfault": 0, "pgrefill": 0, "pgscan": 0,'
        '"pgsteal": 0, "shmem": 0, "slab": 1060864, "slab_reclaimable": 135168, "slab_unreclaimable":'
        '925696, "sock": 0, "thp_collapse_alloc": 0, "thp_fault_alloc": 0, "unevictable": 0, "working'
        'set_activate": 0, "workingset_nodereclaim": 0, "workingset_refault": 33}, "limit": 57671680}'
    ],
]


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


def test_docker_parse_container_mem_docker_plugin_cgroupv2():
    """
    data fetched with mk_docker.py may look different depending on the cgroup
    version used on the host.
    """
    result = parse_docker_container_mem(PLUGIN_OUTPUT_CGROUPV2)
    assert result == {"MemFree": 16564215808, "MemTotal": 16591540224}
    # make sure docker stats result is the same:
    assert round((result["MemTotal"] - result["MemFree"]) / 1024 / 10.24) / 100 == 26.06


def test_docker_parse_container_mem_docker_plugin_cgroupv2_with_limit():
    result = parse_docker_container_mem(PLUGIN_OUTPUT_CGROUPV2_LIMIT)
    assert result == {"MemFree": 55504896, "MemTotal": 57671680}
    # make sure docker stats result is the same:
    assert (result["MemTotal"]) / 1024 / 1024 == 55
    assert round((result["MemTotal"] - result["MemFree"]) / 1024 / 10.24) / 100 == 2.07
