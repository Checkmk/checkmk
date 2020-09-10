#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict
from .agent_based_api.v1.type_defs import AgentStringTable

from .agent_based_api.v1 import register
from .utils import docker


def _parse_docker_container_mem_plugin(string_table: AgentStringTable) -> Dict[str, Any]:
    parsed = docker.json_get_obj(string_table[1])
    # flatten nested stats
    parsed.update(parsed.pop('stats'))
    # rename for compatibility with section produced by linux agent
    for added_key, present_key in (
        ("limit_in_bytes", "hierarchical_memory_limit"),
        ("MemTotal", "limit"),
        ("usage_in_bytes", "usage"),
    ):
        parsed[added_key] = parsed.get(present_key)

    return parsed


def parse_docker_container_mem(string_table: AgentStringTable) -> Dict[str, int]:
    """
        >>> import pprint
        >>> pprint.pprint(parse_docker_container_mem([
        ...     ['@docker_version_info',
        ...      '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'],
        ...     [('{"usage": 4034560, "limit": 16690180096, "max_usage": 7208960,'
        ...       ' "stats": {"cache": 42, "hierarchical_memory_limit": 9223372036854771712}}')]
        ... ]))
        {'MemFree': 16686145578, 'MemTotal': 16690180096}
        >>> pprint.pprint(parse_docker_container_mem([
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
        {'MemFree': 67155951616, 'MemTotal': 67236446208}

    """
    version = docker.get_version(string_table)

    if version is None:
        # parsed contains memory usages in bytes
        parsed = {}
        for line in string_table:
            if line[0] == "MemTotal:" and line[2] == "kB":
                parsed["MemTotal"] = int(line[1]) * 1024
            else:
                parsed[line[0]] = int(line[1])
    else:
        parsed = _parse_docker_container_mem_plugin(string_table)

    # Calculate used memory like docker does (https://github.com/moby/moby/issues/10824)
    usage = (parsed["usage_in_bytes"] - parsed["cache"])

    # Populate a dictionary in the format check_memory() form mem.include expects.
    # The values are scaled to kB
    section = {}
    # Extract the real memory limit for the container. There is either the
    # maximum amount of memory available or a configured limit for the
    # container (cgroup).
    section["MemTotal"] = min(parsed["MemTotal"], parsed["limit_in_bytes"])
    section["MemFree"] = section["MemTotal"] - usage
    # temporarily disabled. See CMK-5224
    # section["Cached"] = parsed["cache"]

    return section


register.agent_section(
    name="docker_container_mem",
    parse_function=parse_docker_container_mem,
    parsed_section_name="mem",
)
