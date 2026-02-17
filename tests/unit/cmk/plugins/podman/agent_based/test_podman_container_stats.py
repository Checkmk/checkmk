#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.podman.agent_based.lib import SectionPodmanContainerStats
from cmk.plugins.podman.agent_based.podman_container_stats import (
    parse_podman_container_stats,
)

STRING_TABLE = [
    [
        '{"AvgCPU": 0.042,"ContainerID": "50baa2b53cb3548c717526bd80ec",'
        '"Name": "root","PerCPU": null,"CPU": 42.20,"CPUNano": 3709000,'
        '"CPUSystemNano": 3709,"SystemNano": 1755534848733998037,"MemUsage": 45056,'
        '"MemLimit": 16483930112,"MemPerc": 0.0002733328744654168,"NetInput": 7494,'
        '"NetOutput": 586,"BlockInput": 3674112,"BlockOutput": 0,"PIDs": 1,"UpTime": '
        '3709000,"Duration": 3709000}'
    ]
]


CLI_STRING_TABLE = [
    [
        '{"id": "63f10448c71c", "name": "nonroot-test", "cpu_time": "3.472ms",'
        '"cpu_percent": "5.28%", "avg_cpu": "5.28%",'
        '"mem_usage": "45.06kB / 16.48GB", "mem_percent": "0.00%",'
        '"net_io": "1.98kB / 430B", "block_io": "3.67MB / 512kB", "pids": "1"}'
    ]
]


def test_discover_podman_container_stats() -> None:
    section = parse_podman_container_stats(STRING_TABLE)
    assert section == SectionPodmanContainerStats(
        CPU=42.20,
        MemLimit=16483930112,
        MemUsage=45056,
        BlockInput=3674112,
        BlockOutput=0,
    )


def test_parse_podman_container_stats_cli_format() -> None:
    section = parse_podman_container_stats(CLI_STRING_TABLE)
    assert section == SectionPodmanContainerStats(
        CPU=5.28,
        MemUsage=45060,
        MemLimit=16480000000,
        BlockInput=3670000,
        BlockOutput=512000,
    )
