#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.docker_container_mem import parse_docker_container_mem

# docker stats: 1007MiB / 4.347GiB
PLUGIN_OUTPUT_MEM_NO_LIMIT = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.4.4", "ApiVersion": "1.41"}',
    ],
    [
        '{"usage": 1056489472, "max_usage": 2154078208, "stats": {"active_anon": 1052303360, "active_'
        'file": 626688, "cache": 946176, "dirty": 0, "hierarchical_memory_limit": 9223372036854771712'
        ', "hierarchical_memsw_limit": 0, "inactive_anon": 0, "inactive_file": 405504, "mapped_file":'
        '540672, "pgfault": 2901789, "pgmajfault": 0, "pgpgin": 2894232, "pgpgout": 2637078, "rss": 1'
        '052303360, "rss_huge": 0, "total_active_anon": 1052303360, "total_active_file": 626688, "tot'
        'al_cache": 946176, "total_dirty": 0, "total_inactive_anon": 0, "total_inactive_file": 405504'
        ', "total_mapped_file": 540672, "total_pgfault": 2901789, "total_pgmajfault": 0, "total_pgpgi'
        'n": 2894232, "total_pgpgout": 2637078, "total_rss": 1052303360, "total_rss_huge": 0, "total_'
        'unevictable": 0, "total_writeback": 0, "unevictable": 0, "writeback": 0}, "limit": 466723225'
        "6}"
    ],
]

# docker stats: 386.1MiB / 500MiB
PLUGIN_OUTPUT_MEM_LIMIT = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.4.4", "ApiVersion": "1.41"}',
    ],
    [
        '{"usage": 404840448, "max_usage": 412770304, "stats": {"active_anon": 403460096, "active_fil'
        'e": 0, "cache": 0, "dirty": 0, "hierarchical_memory_limit": 524288000, "hierarchical_memsw_l'
        'imit": 0, "inactive_anon": 0, "inactive_file": 4096, "mapped_file": 0, "pgfault": 101904, "p'
        'gmajfault": 0, "pgpgin": 100716, "pgpgout": 2230, "rss": 403460096, "rss_huge": 0, "total_ac'
        'tive_anon": 403460096, "total_active_file": 0, "total_cache": 0, "total_dirty": 0, "total_in'
        'active_anon": 0, "total_inactive_file": 4096, "total_mapped_file": 0, "total_pgfault": 10190'
        '4, "total_pgmajfault": 0, "total_pgpgin": 100716, "total_pgpgout": 2230, "total_rss": 403460'
        '096, "total_rss_huge": 0, "total_unevictable": 0, "total_writeback": 0, "unevictable": 0, "w'
        'riteback": 0}, "limit": 524288000}'
    ],
]


def test_parse_container_mem_docker_plugin() -> None:
    """
    see if the output returned from mk_docker.py on a host with cgroup v1 can
    be parsed corretly
    """
    result = parse_docker_container_mem(PLUGIN_OUTPUT_MEM_NO_LIMIT)
    assert result == {"MemFree": 3611148288, "MemTotal": 4667232256}
    # compare to output of docker stats:
    assert round(result["MemTotal"] / 1024 / 1024 / 1.024) / 1000 == 4.347
    assert round((result["MemTotal"] - result["MemFree"]) / 1024 / 1024) == 1007


def test_parse_container_mem_docker_plugin_with_limit() -> None:
    """
    same as above, but with a 500MiB memory limit set via `-m` on `docker run`
    """
    result = parse_docker_container_mem(PLUGIN_OUTPUT_MEM_LIMIT)
    assert result == {"MemFree": 119451648, "MemTotal": 524288000}
    # compare to output of docker stats:
    assert round(result["MemTotal"] / 1024 / 1024) == 500
    assert round((result["MemTotal"] - result["MemFree"]) / 1024 / 102.4) / 10 == 386.1


MK_DOCKER_CONTAINER_MEM_CGROUPV1 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "ApiVersion": "1.40", "DockerPyVersion": "2.6.1"}',
    ],
    [
        '{"stats": {"writeback": 0, "total_rss": 1073152, "active_anon": 1073152, "active_file": 2551'
        '3984, "total_writeback": 0, "hierarchical_memsw_limit": 0, "total_pgfault": 366373, "dirty":'
        '7987200, "inactive_anon": 0, "total_active_anon": 1073152, "pgpgout": 191354, "inactive_file'
        '": 76505088, "total_pgpgin": 216523, "rss_huge": 0, "total_cache": 102019072, "total_pgmajfa'
        'ult": 0, "total_dirty": 7987200, "hierarchical_memory_limit": 9223372036854771712, "unevicta'
        'ble": 0, "pgfault": 366373, "total_mapped_file": 0, "total_inactive_file": 76505088, "total_'
        'rss_huge": 0, "total_unevictable": 0, "pgmajfault": 0, "pgpgin": 216523, "total_inactive_ano'
        'n": 0, "total_active_file": 25513984, "total_pgpgout": 191354, "cache": 102019072, "mapped_f'
        'ile": 0, "rss": 1073152}, "limit": 6966779904, "usage": 114491392, "max_usage": 203640832}'
    ],
]

MK_DOCKER_CONTAINER_MEM_CGROUPV2 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.4.2", "ApiVersion": "1.41"}',
    ],
    [
        '{"usage": 155774976, "stats": {"active_anon": 0, "active_file": 49065984, "anon": 1622016, "'
        'anon_thp": 0, "file": 141791232, "file_dirty": 0, "file_mapped": 3379200, "file_writeback": '
        '405504, "inactive_anon": 1351680, "inactive_file": 92590080, "kernel_stack": 147456, "pgacti'
        'vate": 11649, "pgdeactivate": 0, "pgfault": 424644, "pglazyfree": 0, "pglazyfreed": 0, "pgma'
        'jfault": 165, "pgrefill": 0, "pgscan": 0, "pgsteal": 0, "shmem": 0, "slab": 12309152, "slab_'
        'reclaimable": 11822024, "slab_unreclaimable": 487128, "sock": 69632, "thp_collapse_alloc": 0'
        ', "thp_fault_alloc": 0, "unevictable": 0, "workingset_activate": 0, "workingset_nodereclaim"'
        ': 0, "workingset_refault": 0}, "limit": 16584396800}'
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        [
            MK_DOCKER_CONTAINER_MEM_CGROUPV1,
            [
                Result(state=State.OK, summary="RAM: 0.55% - 36.2 MiB of 6.49 GiB"),
                Metric("mem_used", 37986304.0, boundaries=(0.0, 6966779904.0)),
                Metric("mem_used_percent", 0.5452490895857071, boundaries=(0.0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    37986304.0,
                    levels=(83886080.0, 94371840.0),
                    boundaries=(0.0, 6966779904.0),
                ),
            ],
        ],
        [
            MK_DOCKER_CONTAINER_MEM_CGROUPV2,
            [
                Result(state=State.OK, summary="RAM: 0.38% - 60.3 MiB of 15.4 GiB"),
                Metric("mem_used", 63184896.0, boundaries=(0.0, 16584396800.0)),
                Metric("mem_used_percent", 0.3809900158684095, boundaries=(0.0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    63184896.0,
                    levels=(83886080.0, 94371840.0),
                    boundaries=(0.0, 16584396800.0),
                ),
            ],
        ],
    ],
)
def test_docker_container_diskstat(
    fix_register,
    string_table,
    expected_result,
) -> None:
    agent_section = fix_register.agent_sections[SectionName("docker_container_mem")]
    plugin = fix_register.check_plugins[CheckPluginName("mem_used")]
    parsed = agent_section.parse_function(string_table)
    assert (
        list(
            plugin.check_function(
                params={"levels": (80, 90)},
                section=parsed,
            )
        )
        == expected_result
    )
