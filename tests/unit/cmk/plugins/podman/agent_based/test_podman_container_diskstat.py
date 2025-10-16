# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.podman.agent_based.cee.podman_container_diskstat import (
    _check_diskstat_testable,
    discover_podman_container_diskstat,
)

from .lib import SECTION_CONTAINER_STATS


def test_discover_podman_container_diskstat() -> None:
    assert list(discover_podman_container_diskstat(SECTION_CONTAINER_STATS)) == [
        Service(item="SUMMARY")
    ]


def test_check_diskstat_testable() -> None:
    assert list(
        _check_diskstat_testable(
            read_ios=SECTION_CONTAINER_STATS.read_io,
            write_ios=SECTION_CONTAINER_STATS.write_io,
            params={},
            value_store={},
            this_time=0.0,
        )
    ) == [
        Result(state=State.OK, notice="Read operations: 3674112.00/s"),
        Metric("disk_read_ios", 3674112.0),
        Result(state=State.OK, notice="Write operations: 8872.00/s"),
        Metric("disk_write_ios", 8872.0),
    ]
