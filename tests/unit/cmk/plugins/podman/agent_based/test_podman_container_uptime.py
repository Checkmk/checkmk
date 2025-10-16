# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.
import datetime
from zoneinfo import ZoneInfo

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.podman.agent_based.lib import (
    ContainerHealth,
    ContainerHealthcheck,
    HealthCheckLog,
    PodmanContainerNetworkSettings,
    SectionPodmanContainerConfig,
    SectionPodmanContainerInspect,
    SectionPodmanContainerState,
)
from cmk.plugins.podman.agent_based.podman_container_inspect import (
    parse_podman_container_inspect,
)
from cmk.plugins.podman.agent_based.podman_container_uptime import (
    calculate_uptime,
    check_podman_container_uptime,
    discover_podman_container_uptime,
)

from .lib import SECTION_PAUSED, SECTION_RUNNING

STRING_TABLE = [
    [
        '{"Id": "id","Created": "created_date","Path": "sleep","Args": ["infinity"],'
        '"State": {"OciVersion": "1.1.0","Status": "running","Running": true,"Paused": '
        'false,"StartedAt": "2025-06-01T13:00:00+02:00","FinishedAt": "0001-01-01T00:00:00Z"}, '
        '"RestartCount": 5}'
    ]
]


def test_discover_podman_container_uptime() -> None:
    assert list(discover_podman_container_uptime(SECTION_RUNNING, None)) == [Service()]
    assert not list(discover_podman_container_uptime(parse_podman_container_inspect([[]]), None))


def test_check_podman_container_uptime() -> None:
    results = list(
        check_podman_container_uptime(
            {},
            SECTION_RUNNING,
            None,
        )
    )
    assert len(results) == 3
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert isinstance(results[1], Result)
    assert results[1].state == State.OK
    assert isinstance(results[2], Metric)
    assert results[2].name == "uptime"


def test_check_podman_container_uptime_no_running_container() -> None:
    results = list(
        check_podman_container_uptime(
            {},
            SECTION_PAUSED,
            None,
        )
    )
    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert results[0].summary == "Operational state: paused"


@pytest.mark.parametrize(
    "section, expected_time_diff",
    [
        pytest.param(
            SectionPodmanContainerInspect(
                State=SectionPodmanContainerState(
                    Status="running",
                    StartedAt="2025-06-01T13:00:00+02:00",
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
                Pod="",
            ),
            10800.0,
            id="Uptime 3 hours -> Different time zones",
        ),
        pytest.param(
            SectionPodmanContainerInspect(
                State=SectionPodmanContainerState(
                    Status="running",
                    StartedAt="2025-06-01T13:00:00+00:00",
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
                Pod="",
            ),
            3600.0,
            id="Uptime 1 hour -> The same time zones",
        ),
        pytest.param(
            SectionPodmanContainerInspect(
                State=SectionPodmanContainerState(
                    Status="running",
                    StartedAt="2025-06-01T13:00:00-01:00",
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
                Pod="",
            ),
            0.0,
            id="Just started -> No uptime -> Different time zones",
        ),
    ],
)
def test_calculate_uptime(
    section: SectionPodmanContainerInspect,
    expected_time_diff: float,
) -> None:
    now = datetime.datetime(2025, 6, 1, 14, 0, tzinfo=ZoneInfo("UTC"))
    uptime_section = calculate_uptime(now=now, started_at=section.state.started_at)
    assert uptime_section.uptime_sec == expected_time_diff
    assert uptime_section.message is None
