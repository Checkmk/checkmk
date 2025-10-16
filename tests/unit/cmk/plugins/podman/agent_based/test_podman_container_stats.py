# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.


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


def test_discover_podman_container_stats() -> None:
    section = parse_podman_container_stats(STRING_TABLE)
    assert section == SectionPodmanContainerStats(
        CPU=42.20,
        MemLimit=16483930112,
        MemUsage=45056,
        BlockInput=3674112,
        BlockOutput=0,
    )
