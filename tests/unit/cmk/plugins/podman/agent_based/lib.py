# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.podman.agent_based.lib import (
    ContainerHealth,
    ContainerHealthcheck,
    HealthCheckLog,
    PodmanContainerNetworkSettings,
    SectionPodmanContainerConfig,
    SectionPodmanContainerInspect,
    SectionPodmanContainerState,
    SectionPodmanContainerStats,
)

SECTION_RUNNING = SectionPodmanContainerInspect(
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
)

SECTION_PAUSED = SectionPodmanContainerInspect(
    State=SectionPodmanContainerState(
        Status="paused",
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

SECTION_CONTAINER_STATS = SectionPodmanContainerStats(
    CPU=42.2,
    MemLimit=16483930112,
    MemUsage=1450560000,
    BlockInput=3674112,
    BlockOutput=8872,
)
