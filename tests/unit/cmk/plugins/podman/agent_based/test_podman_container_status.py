# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.podman.agent_based.cee.lib import (
    ContainerHealth,
    ContainerHealthcheck,
    HealthCheckLog,
    PodmanContainerNetworkSettings,
    SectionPodmanContainerConfig,
    SectionPodmanContainerInspect,
    SectionPodmanContainerState,
)
from cmk.plugins.podman.agent_based.cee.podman_container_status import (
    check_podman_container_status,
    DEFAULT_CHECK_PARAMETERS,
    discover_podman_container_status,
    Params,
)

from .lib import SECTION_PAUSED, SECTION_RUNNING

SECTION_EXITED_WITH_ZERO = SectionPodmanContainerInspect(
    State=SectionPodmanContainerState(
        Status="exited",
        StartedAt="2025-08-01T13:00:00+02:00",
        ExitCode=0,
        Health=ContainerHealth(
            Log=[HealthCheckLog(Output="testOutput", ExitCode=0)],
            FailingStreak=0,
            Status="healthy",
        ),
    ),
    Config=SectionPodmanContainerConfig(
        HealthcheckOnFailureAction="do some action here",
        Healthcheck=ContainerHealthcheck(
            Test=["CMD", "Test_Command"],
        ),
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
    Pod="Pod1",
)

SECTION_EXITED_WITH_NON_ZERO = SectionPodmanContainerInspect(
    State=SectionPodmanContainerState(
        Status="exited",
        StartedAt="2025-08-01T13:00:00+02:00",
        ExitCode=1,
        Health=ContainerHealth(
            Log=[HealthCheckLog(Output="testOutput", ExitCode=0)],
            FailingStreak=0,
            Status="healthy",
        ),
    ),
    Config=SectionPodmanContainerConfig(
        HealthcheckOnFailureAction="do some action here",
        Healthcheck=ContainerHealthcheck(
            Test=["CMD", "Test_Command"],
        ),
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
    Pod="Pod1",
)


def test_discover_podman_container_status() -> None:
    assert list(discover_podman_container_status(SECTION_RUNNING)) == [Service()]


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            SECTION_RUNNING,
            DEFAULT_CHECK_PARAMETERS,
            [
                Result(state=State.OK, summary="Running"),
            ],
            id="Running -> OK. Empty Pod value",
        ),
        pytest.param(
            SECTION_EXITED_WITH_ZERO,
            DEFAULT_CHECK_PARAMETERS,
            [
                Result(state=State.OK, summary="Exited with zero"),
                Result(state=State.OK, summary="Pod: Pod1"),
            ],
            id="Exited with zero -> OK. Contains Pod",
        ),
        pytest.param(
            SECTION_EXITED_WITH_NON_ZERO,
            DEFAULT_CHECK_PARAMETERS,
            [
                Result(state=State.CRIT, summary="Exited with non zero"),
                Result(state=State.OK, summary="Pod: Pod1"),
            ],
            id="Exited with non zero -> CRIT. Contains Pod",
        ),
        pytest.param(
            SECTION_PAUSED,
            {"paused": 0},
            [
                Result(state=State.OK, summary="Paused"),
                Result(state=State.OK, summary="Pod: Pod1"),
            ],
            id="Paused -> OK (because of params). Contains Pod",
        ),
    ],
)
def test_check_podman_container_status(
    section: SectionPodmanContainerInspect,
    params: Params,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_podman_container_status(
                params,
                section,
            ),
        )
        == expected_result
    )
