# #!/usr/bin/env python3
# # Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.podman.agent_based.lib import (
    ContainerHealth,
    PodmanContainerNetworkSettings,
    SectionPodmanContainerConfig,
    SectionPodmanContainerInspect,
    SectionPodmanContainerState,
)
from cmk.plugins.podman.agent_based.podman_container_inspect import (
    parse_podman_container_inspect,
)

STRING_TABLE = [
    [
        '{"Id": "id","Created": "created_date","Path": "sleep","Args": ["infinity"],'
        '"State": {"OciVersion": "1.1.0","Status": "running","Running": true,"Paused": '
        'false,"StartedAt": "2025-08-01T13:00:00+02:00","FinishedAt": "0001-01-01T00:00:00Z", '
        '"ExitCode": 0, "Health": {"Log": null, "FailingStreak": 0, "Status": "healthy"}}, '
        '"RestartCount": 5, "Pod": "", "Config": {"HealthcheckOnFailureAction": "none", '
        '"Hostname": "test-hostname", "Labels": {"key1": "value1", "key2": "value2"}, "User": "username"},'
        '"NetworkSettings": {"IPAddress": "192.168.1.100", "Gateway": "192.168.1.1", '
        '"MacAddress": "00:11:22:33:44:55"}}'
    ]
]


def test_discover_podman_container_inspect() -> None:
    section = parse_podman_container_inspect(STRING_TABLE)
    assert section == SectionPodmanContainerInspect(
        State=SectionPodmanContainerState(
            Status="running",
            StartedAt="2025-08-01T13:00:00+02:00",
            ExitCode=0,
            Health=ContainerHealth(Log=None, FailingStreak=0, Status="healthy"),
        ),
        RestartCount=5,
        Pod="",
        Config=SectionPodmanContainerConfig(
            HealthcheckOnFailureAction="none",
            Healthcheck=None,
            Hostname="test-hostname",
            Labels={"key1": "value1", "key2": "value2"},
            User="username",
        ),
        NetworkSettings=PodmanContainerNetworkSettings(
            IPAddress="192.168.1.100",
            Gateway="192.168.1.1",
            MacAddress="00:11:22:33:44:55",
        ),
    )
