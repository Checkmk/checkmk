#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import docker, memory


def _parse_docker_container_mem_plugin(string_table: StringTable) -> docker.MemorySection:
    """
    parse output of mk_docker.py which corresponds to the docker api
    """
    parsed = docker.parse(string_table).data

    # we could get data from a host with cgroup v2, or cgroup v1.
    stats = parsed.get("stats", {})

    try:
        memory_limit = parsed["limit"]
        container_memory_usage = parsed["usage"]
        if "hierarchical_memory_limit" in stats and "total_inactive_file" in stats:
            # cgroup v1
            container_memory_limit = stats["hierarchical_memory_limit"]
            container_memory_total_inactive_file = stats["total_inactive_file"]
            memory_limit = min(memory_limit, container_memory_limit)
        else:
            # we assume cgroup v2
            container_memory_total_inactive_file = stats["inactive_file"]
    except KeyError:
        # `docker stats <CONTAINER>` will show 0/0 so we are compliant.
        return docker.MemorySection(0, 0, 0)

    return docker.MemorySection(
        mem_total=memory_limit,
        mem_usage=container_memory_usage,
        mem_cache=container_memory_total_inactive_file,
    )


def parse_docker_container_mem(string_table: StringTable) -> memory.SectionMemUsed:
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
        # this is the output of a checkmk agent run inside a docker container
        # it has to handle only cgroupv1 as cgroupv2 is sent with another section name
        parsed = docker.parse_container_memory(string_table)
    else:
        # this is the output of mk_docker.py
        # it has to handle both cgroupv1 and cgroupv2
        parsed = _parse_docker_container_mem_plugin(string_table)
    return parsed.to_mem_used()


register.agent_section(
    name="docker_container_mem",
    parse_function=parse_docker_container_mem,
    parsed_section_name="mem_used",
)
