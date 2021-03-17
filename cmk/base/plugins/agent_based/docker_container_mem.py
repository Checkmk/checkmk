#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils import docker


def _parse_docker_container_mem_plugin(string_table: StringTable) -> docker.MemorySection:
    """
    parse output of mk_docker.py which corresponds to the docker api
    """
    parsed = docker.parse(string_table).data

    try:
        host_memory_total = parsed['limit']
        container_memory_limit = parsed['stats']['hierarchical_memory_limit']
        container_memory_total_inactive_file = parsed['stats']['total_inactive_file']
        container_memory_usage = parsed['usage']
    except KeyError:
        # `docker stats <CONTAINER>` will show 0/0 so we are compliant.
        return docker.MemorySection(0, 0, 0)

    mem_total = min(host_memory_total, container_memory_limit)

    return docker.MemorySection(
        mem_total=mem_total,
        mem_usage=container_memory_usage,
        mem_cache=container_memory_total_inactive_file,
    )


def parse_docker_container_mem(string_table: StringTable) -> Dict[str, int]:
    """
        >>> import pprint
        >>> pprint.pprint(parse_docker_container_mem([
        ...     ['@docker_version_info',
        ...      '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'],
        ...     [('{"usage": 4034560, "limit": 16690180096, "max_usage": 7208960,'
        ...       ' "stats": {"cache": 42, "total_inactive_file": 111, '
        ...       '"hierarchical_memory_limit": 9223372036854771712}}')]
        ... ]))
        {'MemFree': 16686145647, 'MemTotal': 16690180096}
        >>> pprint.pprint(parse_docker_container_mem([
        ...     # this format is used for agent running inside docker container
        ...     ['cache', '41316352'], ['rss', '79687680'], ['rss_huge', '8388608'],
        ...     ['mapped_file', '5976064'], ['swap', '0'], ['pgpgin', '7294455'],
        ...     ['pgpgout', '7267468'], ['pgfault', '39514980'], ['pgmajfault', '111'],
        ...     ['inactive_anon', '0'], ['active_anon', '79642624'],
        ...     ['inactive_file', '28147712'], ['active_file', '13168640'],
        ...     ['unevictable', '0'], ['hierarchical_memory_limit', '9223372036854771712'],
        ...     ['hierarchical_memsw_limit', '9223372036854771712'],
        ...     ['total_cache', '41316352'], ['total_rss', '79687680'],
        ...     ['total_rss_huge', '8388608'], ['total_mapped_file', '5976064'],
        ...     ['total_swap', '0'], ['total_pgpgin', '7294455'],
        ...     ['total_pgpgout', '7267468'], ['total_pgfault', '39514980'],
        ...     ['total_pgmajfault', '111'], ['total_inactive_anon', '0'],
        ...     ['total_active_anon', '79642624'], ['total_inactive_file', '28147712'],
        ...     ['total_active_file', '13168640'], ['total_unevictable', '0'],
        ...     ['usage_in_bytes', '121810944'], ['limit_in_bytes', '9223372036854771712'],
        ...     ['MemTotal:', '65660592', 'kB']
        ... ]))
        {'MemFree': 67142782976, 'MemTotal': 67236446208}

    Some containers don't have any memory info:
        >>> parse_docker_container_mem([
        ...     ['@docker_version_info',
        ...      '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'],
        ...     ['{}'],
        ... ])
        {'MemTotal': 0, 'MemFree': 0}

    """
    version = docker.get_version(string_table)

    if version is None:
        parsed = docker.parse_container_memory(string_table)
    else:
        parsed = _parse_docker_container_mem_plugin(string_table)

    container_memory_usage = parsed.mem_usage - parsed.mem_cache

    if container_memory_usage < 0:
        # all container runtimes seem to do it this way:
        # https://github.com/google/cadvisor/blob/c6ad44633aa0cee60a28430ddec632dca53becac/container/libcontainer/handler.go#L823
        # https://github.com/containerd/cri/blob/bc08a19f3a44bda9fd141e6ee4b8c6b369e17e6b/pkg/server/container_stats_list_linux.go#L123
        # https://github.com/docker/cli/blob/70a00157f161b109be77cd4f30ce0662bfe8cc32/cli/command/container/stats_helpers.go#L245
        container_memory_usage = 0

    return {
        "MemTotal": parsed.mem_total,
        "MemFree": parsed.mem_total - container_memory_usage,
    }


register.agent_section(
    name="docker_container_mem",
    parse_function=parse_docker_container_mem,
    parsed_section_name="mem_used",
)
