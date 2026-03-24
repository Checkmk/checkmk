#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import HostLabel
from cmk.plugins.podman.agent_based.lib import (
    ContainerHealth,
    PodmanContainerNetworkSettings,
    SectionPodmanContainerConfig,
    SectionPodmanContainerInspect,
    SectionPodmanContainerState,
)
from cmk.plugins.podman.agent_based.podman_container_inspect import (
    host_label_function,
    parse_podman_container_inspect,
)

STRING_TABLE = [
    [
        '{"Id": "id","Created": "created_date","Path": "sleep","Args": ["infinity"],'
        '"State": {"OciVersion": "1.1.0","Status": "running","Running": true,"Paused": '
        'false,"StartedAt": "2025-08-01T13:00:00+02:00","FinishedAt": "0001-01-01T00:00:00Z", '
        '"ExitCode": 0, "Health": {"Log": null, "FailingStreak": 0, "Status": "healthy"}}, '
        '"RestartCount": 5, "Pod": "", "ImageName": "registry.checkmk.com/enterprise/check-mk-enterprise:2.3.0p35",'
        '"Config": {"HealthcheckOnFailureAction": "none", '
        '"Hostname": "test-hostname", "Labels": {"key1": "value1", "key2": "value2"}, "User": "username"},'
        '"NetworkSettings": {"IPAddress": "192.168.1.100", "Gateway": "192.168.1.1", '
        '"MacAddress": "00:11:22:33:44:55"}, "SocketUser": "hostuser"}'
    ]
]

STRING_TABLE_NO_SOCKET_USER = [
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
        ImageName="registry.checkmk.com/enterprise/check-mk-enterprise:2.3.0p35",
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
        SocketUser="hostuser",
    )


def test_discover_podman_container_inspect_no_socket_user() -> None:
    section = parse_podman_container_inspect(STRING_TABLE_NO_SOCKET_USER)
    assert section is not None
    assert section.socket_user is None


def test_host_label_function_uses_socket_user() -> None:
    section = parse_podman_container_inspect(STRING_TABLE)
    assert section is not None
    labels = list(host_label_function(section))
    assert HostLabel("cmk/podman/user", "hostuser") in labels


def test_host_label_function_omits_user_label_when_no_socket_user() -> None:
    section = parse_podman_container_inspect(STRING_TABLE_NO_SOCKET_USER)
    assert section is not None
    labels = list(host_label_function(section))
    assert not any(label.name == "cmk/podman/user" for label in labels)


@pytest.mark.parametrize(
    "image_name, expected_labels",
    [
        (
            "registry.checkmk.com/enterprise/check-mk-enterprise:2.3.0p35",
            [
                HostLabel(
                    "cmk/docker_image",
                    "registry.checkmk.com/enterprise/check-mk-enterprise:2.3.0p35",
                ),
                HostLabel("cmk/docker_image_name", "check-mk-enterprise"),
                HostLabel("cmk/docker_image_version", "2.3.0p35"),
            ],
        ),
        (
            "doctor:strange",
            [
                HostLabel("cmk/docker_image", "doctor:strange"),
                HostLabel("cmk/docker_image_name", "doctor"),
                HostLabel("cmk/docker_image_version", "strange"),
            ],
        ),
        (
            "fiction/doctor:strange",
            [
                HostLabel("cmk/docker_image", "fiction/doctor:strange"),
                HostLabel("cmk/docker_image_name", "doctor"),
                HostLabel("cmk/docker_image_version", "strange"),
            ],
        ),
        (
            "library:8080/fiction/doctor",
            [
                HostLabel("cmk/docker_image", "library:8080/fiction/doctor"),
                HostLabel("cmk/docker_image_name", "doctor"),
            ],
        ),
        (
            "",
            [],
        ),
    ],
)
def test_host_label_function_image_labels(
    image_name: str, expected_labels: list[HostLabel]
) -> None:
    section = SectionPodmanContainerInspect(
        State=SectionPodmanContainerState(
            Status="running",
            StartedAt="2025-08-01T13:00:00+02:00",
            ExitCode=0,
            Health=None,
        ),
        RestartCount=0,
        Pod="",
        ImageName=image_name,
        Config=SectionPodmanContainerConfig(
            HealthcheckOnFailureAction="none",
            Healthcheck=None,
            Hostname="test-hostname",
            Labels=None,
            User="",
        ),
        NetworkSettings=PodmanContainerNetworkSettings(
            IPAddress="",
            Gateway="",
            MacAddress="",
        ),
    )
    labels = list(host_label_function(section))
    # Filter to only image-related labels for this test
    image_labels = [l for l in labels if l.name.startswith("cmk/docker_image")]
    assert image_labels == expected_labels
