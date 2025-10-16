# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.podman.agent_based.podman_container_memory import (
    check_podman_container_memory,
    discover_podman_container_memory,
)

from .lib import SECTION_CONTAINER_STATS


def test_discover_podman_container_memory() -> None:
    assert list(discover_podman_container_memory(SECTION_CONTAINER_STATS)) == [Service()]


def test_check_podman_container_memory() -> None:
    assert list(
        check_podman_container_memory(
            params={
                "levels": (150.0, 200.0),
            },
            section=SECTION_CONTAINER_STATS,
        )
    ) == [
        Result(state=State.OK, summary="RAM: 8.80% - 1.35 GiB of 15.4 GiB"),
        Metric("mem_used", 1450560000.0, boundaries=(0.0, 16483930112.0)),
        Metric("mem_used_percent", 8.799843181475387, boundaries=(0.0, 100.0)),
        Metric(
            "mem_lnx_total_used",
            1450560000.0,
            levels=(24725895168.0, 32967860224.0),
            boundaries=(0.0, 16483930112.0),
        ),
    ]
