# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.podman.agent_based.podman_container_cpu_utilization import (
    _check_cpu_utilization_testable,
    discover_podman_container_cpu_utilization,
)

from .lib import SECTION_CONTAINER_STATS


def test_discover_podman_container_cpu_utilization() -> None:
    assert list(discover_podman_container_cpu_utilization(SECTION_CONTAINER_STATS)) == [Service()]


def test_check_cpu_utilization_testable() -> None:
    assert list(
        _check_cpu_utilization_testable(
            util=SECTION_CONTAINER_STATS.cpu_util, params={}, value_store={}, this_time=0.0
        )
    ) == [
        Result(state=State.OK, summary="Total CPU: 42.20%"),
        Metric("util", 42.2, boundaries=(0.0, None)),
    ]
