# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import MutableMapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.podman.agent_based.cee.lib import (
    SectionPodmanContainerInspect,
)
from cmk.plugins.podman.agent_based.cee.podman_container_restarts import (
    _check_podman_container_restarts,
    discover_podman_container_restarts,
    Params,
)

from .lib import SECTION_RUNNING


def test_discover_podman_container_restarts() -> None:
    assert list(discover_podman_container_restarts(SECTION_RUNNING)) == [Service()]


@pytest.mark.parametrize(
    "section, params, value_store, expected_result",
    [
        pytest.param(
            SECTION_RUNNING,
            {},
            {},
            [
                Result(state=State.OK, summary="Total: 5"),
                Metric("podman_container_restarts_total", 5.0),
            ],
            id="No levels -> OK",
        ),
        pytest.param(
            SECTION_RUNNING,
            {"restarts_total": ("fixed", (4, 6))},
            {},
            [
                Result(state=State.WARN, summary="Total: 5 (warn/crit at 4/6)"),
                Metric("podman_container_restarts_total", 5.0, levels=(4.0, 6.0)),
            ],
            id="Above warn levels -> WARN",
        ),
        pytest.param(
            SECTION_RUNNING,
            {"restarts_total": ("fixed", (6, 8)), "restarts_last_hour": ("fixed", (2, 3))},
            {"restart_count_list": [(3, 5), (10, 3)]},
            [
                Result(state=State.OK, summary="Total: 5"),
                Metric("podman_container_restarts_total", 5.0, levels=(6.0, 8.0)),
                Result(state=State.WARN, summary="In last hour: 2 (warn/crit at 2/3)"),
                Metric("podman_container_restarts_last_hour", 2.0, levels=(2.0, 3.0)),
            ],
            id="Number of restart in the last hour above warn levels -> WARN",
        ),
    ],
)
def test_check_podman_container_restarts(
    section: SectionPodmanContainerInspect,
    params: Params,
    expected_result: CheckResult,
    value_store: MutableMapping[str, Any],
) -> None:
    assert (
        list(
            _check_podman_container_restarts(
                params,
                section,
                curr_timestamp_seconds=3605,
                host_value_store=value_store,
            ),
        )
        == expected_result
    )
