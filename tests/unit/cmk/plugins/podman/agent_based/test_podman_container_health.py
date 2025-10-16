# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.podman.agent_based.cee.lib import (
    ContainerHealth,
    HealthCheckLog,
    PodmanContainerNetworkSettings,
    SectionPodmanContainerConfig,
    SectionPodmanContainerInspect,
    SectionPodmanContainerState,
)
from cmk.plugins.podman.agent_based.cee.podman_container_health import (
    check_podman_container_health,
    discover_podman_container_health,
    Params,
)

from .lib import SECTION_RUNNING

_DEFAULT_PARAMS = Params(
    healthy=0,
    starting=0,
    unhealthy=2,
    no_healthcheck=1,
)

SECTION_NO_HEALTHCHECK = SectionPodmanContainerInspect(
    State=SectionPodmanContainerState(
        Status="running",
        StartedAt="2025-08-01T13:00:00+02:00",
        ExitCode=0,
        Health=ContainerHealth(
            Log=[HealthCheckLog(Output="testOutput", ExitCode=0)],
            FailingStreak=0,
            Status="healthy",
        ),
    ),
    Config=SectionPodmanContainerConfig(
        HealthcheckOnFailureAction="none",
        Hostname="test-hostname",
        Labels={"key1": "value1", "key2": "value2"},
        User="username",
    ),
    NetworkSettings=PodmanContainerNetworkSettings(
        IPAddress="192.168.1.100",
        Gateway="192.168.1.1",
        MacAddress="00:11:22:33:44:55",
    ),
    RestartCount=5,
    Pod="",
)


def test_discover_podman_container_health() -> None:
    assert list(discover_podman_container_health(SECTION_RUNNING)) == [Service()]


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            SECTION_RUNNING,
            _DEFAULT_PARAMS,
            [
                Result(
                    state=State.OK,
                    summary="Status: healthy",
                    details="Last health report: testOutput\n    "
                    "Health check command: Test_Command\n    "
                    "Consecutive failed healthchecks: 0\n    "
                    "On failure action: do some action here\n    "
                    "Last saved exit code: 0",
                ),
            ],
            id="Healthy -> OK",
        ),
        pytest.param(
            SECTION_NO_HEALTHCHECK,
            _DEFAULT_PARAMS,
            [
                Result(
                    state=State.WARN,
                    summary="No health check configured",
                    details="Last health report: testOutput\n    "
                    "Health check command: No health check command configured\n    "
                    "Consecutive failed healthchecks: 0\n    "
                    "On failure action: none\n    "
                    "Last saved exit code: 0",
                ),
            ],
            id="No Healthcheck -> WARN",
        ),
        pytest.param(
            SECTION_RUNNING,
            {"healthy": 2},
            [
                Result(
                    state=State.CRIT,
                    summary="Status: healthy",
                    details="Last health report: testOutput\n    "
                    "Health check command: Test_Command\n    "
                    "Consecutive failed healthchecks: 0\n    "
                    "On failure action: do some action here\n    "
                    "Last saved exit code: 0",
                ),
            ],
            id="Healthy -> CRIT (custom params)",
        ),
    ],
)
def test_check_podman_container_health(
    section: SectionPodmanContainerInspect,
    params: Params,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_podman_container_health(
                params,
                section,
            ),
        )
        == expected_result
    )
