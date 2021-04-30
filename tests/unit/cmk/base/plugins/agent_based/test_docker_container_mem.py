#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
        '6}'
    ]
]

# docker stats: 386.1MiB / 500MiB
PLUGIN_OUTPUT_MEM_LIMIT = [
    [
        '@docker_version_info',
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.4.4", "ApiVersion": "1.41"}'
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
    ]
]


def test_parse_container_mem_docker_plugin():
    """
    see if the output returned from mk_docker.py on a host with cgroup v1 can
    be parsed corretly
    """
    result = parse_docker_container_mem(PLUGIN_OUTPUT_MEM_NO_LIMIT)
    assert result == {'MemFree': 3611148288, 'MemTotal': 4667232256}
    # compare to output of docker stats:
    assert round(result['MemTotal'] / 1024 / 1024 / 1.024) / 1000 == 4.347
    assert round((result['MemTotal'] - result['MemFree']) / 1024 / 1024) == 1007


def test_parse_container_mem_docker_plugin_with_limit():
    """
    same as above, but with a 500MiB memory limit set via `-m` on `docker run`
    """
    result = parse_docker_container_mem(PLUGIN_OUTPUT_MEM_LIMIT)
    assert result == {'MemFree': 119451648, 'MemTotal': 524288000}
    # compare to output of docker stats:
    assert round(result['MemTotal'] / 1024 / 1024) == 500
    assert round((result['MemTotal'] - result['MemFree']) / 1024 / 102.4) / 10 == 386.1
