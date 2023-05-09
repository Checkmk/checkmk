#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

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
                Result(state=State.OK, summary="RAM: 0.18% - 11.9 MiB of 6.49 GiB"),
                Metric("mem_used", 12472320.0, boundaries=(0.0, 6966779904.0)),
                Metric("mem_used_percent", 0.1790256068350742, boundaries=(0.0, 100.0)),
                Metric(
                    "mem_lnx_total_used",
                    12472320.0,
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
@pytest.mark.usefixtures("config_load_all_checks")
def test_docker_container_diskstat(
    string_table,
    expected_result,
) -> None:
    agent_section = agent_based_register.get_section_plugin(SectionName("docker_container_mem"))
    plugin = agent_based_register.get_check_plugin(CheckPluginName("mem_used"))
    assert plugin
    parsed = agent_section.parse_function(string_table)
    assert (list(plugin.check_function(
        params={"levels": (80, 90)},
        section=parsed,
    )) == expected_result)
