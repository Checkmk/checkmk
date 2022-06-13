#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Any, Dict, Iterable, List, NamedTuple, Optional

from ..agent_based_api.v1.type_defs import StringTable
from .memory import SectionMemUsed

INVENTORY_BASE_PATH = ["software", "applications", "docker"]


class AgentOutputMalformatted(Exception):
    DEFAULT_MESSAGE = (
        "Did not find expected '@docker_version_info' at "
        "beginning of agent section. "
        "Agents <= 1.5.0 are no longer supported."
    )

    def __init__(self) -> None:
        super().__init__(AgentOutputMalformatted.DEFAULT_MESSAGE)


class DockerParseResult(NamedTuple):
    data: Dict[str, Any]
    version: Dict[str, Any]


class DockerParseMultilineResult(NamedTuple):
    data: Iterable[Dict[str, Any]]
    version: Dict[str, Any]


def _cleanup_oci_error_message(string_table: StringTable) -> StringTable:
    """
    If mk_docker.py can not execute the agent inside the docker container, a error
    message is appended to the agent output. The expected output would be the
    agent's output which includes section headers, the error message does not
    include a section header so the output is appended to the privous section.
    Here we try to remove this error message, without changing any other data.
    """
    if (
        string_table
        and string_table[-1]
        and len(string_table[-1]) == 1
        and string_table[-1][0].startswith("OCI runtime exec failed: exec failed:")
    ):
        return string_table[:-1]
    return string_table[:]


def parse_multiline(string_table: StringTable) -> DockerParseMultilineResult:
    """
    expected layout of string_table:

    [
        ["@docker_version_info", "{... json: version info (may be empty) ...}"],
        ["{... json: data ...}"],
        ["{... json: data ...}"],
        ... more json data ...
    ]

    returns generator of parsed json data and version info
    """
    version = ensure_valid_docker_header(string_table)
    string_table = _cleanup_oci_error_message(string_table)

    def generator() -> Iterable[Dict[str, Any]]:
        for line in string_table[1:]:
            if len(line) != 1:
                raise ValueError(
                    "Expect exactly one element per line after @docker_version_info header"
                )
            yield json.loads(line[0])

    return DockerParseMultilineResult(generator(), version)


def parse(string_table: StringTable, *, strict=True) -> DockerParseResult:
    """
    expected layout of string_table:

    [
        ["@docker_version_info", "{... json: version info (may be empty) ...}"],
        ["{... json: data ...}", ?],
        ?
    ]

    If strict is False quersion marks may be present but will be ignored.
    If strict is True (default) and data in question mark position is present
        an Value Error will be thrown
    """
    version = ensure_valid_docker_header(string_table)
    string_table = _cleanup_oci_error_message(string_table)
    if strict:
        if len(string_table) != 2 or len(string_table[0]) != 2 or len(string_table[1]) != 1:
            raise ValueError(
                "Expected list of length 2. "
                "First element list of 2 strings, second element list of 1 string"
            )
    return DockerParseResult(json.loads(string_table[1][0]), version)


def ensure_valid_docker_header(string_table: StringTable) -> Dict:
    """
    make sure string_table conforms to the @docker_version_info schema
    """
    version = get_version(string_table)
    if version is None:
        raise AgentOutputMalformatted()
    return version


def get_version(string_table: StringTable) -> Optional[Dict]:
    try:
        if string_table[0][0] == "@docker_version_info":
            version_info = json.loads(string_table[0][1])
            # if the docker library is not found, version_info may be an empty dict
            assert isinstance(version_info, dict)
            return version_info
    except IndexError:
        pass
    return None


def get_short_id(string: str) -> str:
    return string.rsplit(":", 1)[-1][:12]


def format_labels(labels: Dict[str, str]) -> str:
    return ", ".join("%s: %s" % item for item in sorted(labels.items()))


class MemorySection(NamedTuple):
    mem_total: int
    mem_usage: int
    mem_cache: int

    def to_mem_used(self) -> SectionMemUsed:
        # it seems to be a common problem, that mem_cache > mem_usage,
        # so we make sure that we don't report negative values for memory usage.
        # all container runtimes seem to do it this way:
        # https://github.com/google/cadvisor/blob/c6ad44633aa0cee60a28430ddec632dca53becac/container/libcontainer/handler.go#L823
        # https://github.com/containerd/cri/blob/bc08a19f3a44bda9fd141e6ee4b8c6b369e17e6b/pkg/server/container_stats_list_linux.go#L123
        # https://github.com/docker/cli/blob/70a00157f161b109be77cd4f30ce0662bfe8cc32/cli/command/container/stats_helpers.go#L245
        container_memory_usage = max(self.mem_usage - self.mem_cache, 0)
        return {
            "MemTotal": self.mem_total,
            "MemFree": self.mem_total - container_memory_usage,
        }


def _mem_bytes(line: List[str]) -> int:
    if len(line) == 2 and line[1] == "kB":
        return int(line[0]) * 1024
    return int(line[0])


def parse_container_memory(string_table: StringTable, cgroup: int = 1) -> MemorySection:
    parsed = {line[0]: line[1:] for line in string_table}

    host_memory_total = _mem_bytes(parsed["MemTotal:"])
    if cgroup == 1:
        container_memory_usage = _mem_bytes(parsed["usage_in_bytes"])
        # we use the docker way and remove total_inactive_file:
        # https://github.com/docker/cli/blob/70a00157f161b109be77cd4f30ce0662bfe8cc32/cli/command/container/stats_helpers.go#L227-L238
        container_memory_total_inactive_file = _mem_bytes(parsed["total_inactive_file"])
        # cgroup v1 uses a huge value to signal unlimited: https://unix.stackexchange.com/a/421182
        container_memory_total = min(host_memory_total, _mem_bytes(parsed["limit_in_bytes"]))
    else:
        container_memory_usage = _mem_bytes(parsed["memory.current"])
        if (memory_max := parsed["memory.max"]) == ["max"]:
            container_memory_total = host_memory_total
        else:
            container_memory_total = _mem_bytes(memory_max)
        container_memory_total_inactive_file = _mem_bytes(parsed["inactive_file"])

    return MemorySection(
        mem_total=container_memory_total,
        mem_usage=container_memory_usage,
        mem_cache=container_memory_total_inactive_file,
    )


def is_string_table_heading(line: List[str]) -> bool:
    return len(line) == 1 and line[0].startswith("[") and line[0].endswith("]")
