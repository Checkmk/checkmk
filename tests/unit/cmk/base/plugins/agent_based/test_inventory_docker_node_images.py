#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.utils.docker as docker
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_docker_node_images import (
    inventory_docker_node_images,
    parse_docker_node_images,
)

from .utils_inventory import sort_inventory_result


def test_inventory_docker_node_images_empty():
    with pytest.raises(docker.AgentOutputMalformatted) as e:
        parse_docker_node_images([])
        assert (
            "Did not find expected '@docker_version_info' at beginning of agent section."
            " Agents <= 1.5.0 are no longer supported."
        ) in str(e)


AGENT_OUTPUT = (
    '@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}\n'
    "[[[images]]]\n"
    '{"RepoDigests": [], "Id": "sha256:b2bf42ca5d8f3245e58832a1d67d5ce9cfbfe754e9b552b5e5f0e6d26dea4aa5", '
    '"RepoTags": ["hello:world"], "Created": "2021-02-12T11:29:33.063968737Z", "VirtualSize": 1231733, '
    '"Config": {"Labels": {"image_label_command_line": "1", "image_label_dockerfile": "2"}}}\n'
    "[[[containers]]]\n"
    '{"Id": "891a6f6a1c2807c544b0342d79fa79da05cc7f8d40927d72fe7b2513622b91d1", "Created": '
    '"2021-02-12T12:15:28.230110819Z", "Name": "/relaxed_shaw", "State": {"Status": "running", '
    '"Running": true, "Paused": false, "Restarting": false, "OOMKilled": false, "Dead": false, '
    '"Pid": 3436979, "ExitCode": 0, "Error": "", "StartedAt": "2021-02-12T12:15:28.592056523Z", '
    '"FinishedAt": "0001-01-01T00:00:00Z"}, "Config": {"Labels": {"another_container_label": "2", '
    '"container": "label", "image_label_command_line": "1", "image_label_dockerfile": "2"}}, '
    '"Image": "sha256:b2bf42ca5d8f3245e58832a1d67d5ce9cfbfe754e9b552b5e5f0e6d26dea4aa5"}'
)

AGENT_OUTPUT_NULL_LABELS_ST = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    ["[[[images]]]"],
    [
        '{"Id": "sha256:666620a54926240737e6619b0246917892f8ea99f8f80eb3cf8a5f0d77a91c55", "RepoTags": ["plan'
        'tuml:latest"], "RepoDigests": [], "Parent": "sha256:3d69b34c9f0fc8debed7d47e1bb87b20192c642a515ddc93'
        'da4baf3a9d3d8a1f", "Comment": "", "Created": "2021-02-25T08:42:22.47977742Z", "Container": "2c78e65e'
        '14fd8f87df002ac2631b92a25ddfb0ef06386f04cb46495145bcb58a", "ContainerConfig": {"Hostname": "", "Doma'
        'inname": "", "User": "", "AttachStdin": false, "AttachStdout": false, "AttachStderr": false, "Tty": '
        'false, "OpenStdin": false, "StdinOnce": false, "Env": ["re", "mo", "ved"], "Cmd": ["dot", "-version"'
        '], "Image": "sha256:3d69b34c9f0fc8debed7d47e1bb87b20192c642a515ddc93da4baf3a9d3d8a1f", "Volumes": nu'
        'll, "WorkingDir": "", "Entrypoint": null, "OnBuild": null, "Labels": null}, "DockerVersion": "20.10.'
        '3", "Author": "", "Config": {"Hostname": "", "Domainname": "", "User": "", "AttachStdin": false, "At'
        'tachStdout": false, "AttachStderr": false, "Tty": false, "OpenStdin": false, "StdinOnce": false, "En'
        'v": ["re", "mo", "ved"], "Cmd": ["jshell"], "ArgsEscaped": true, "Image": "sha256:3d69b34c9f0fc8debe'
        'd7d47e1bb87b20192c642a515ddc93da4baf3a9d3d8a1f", "Volumes": null, "WorkingDir": "", "Entrypoint": nu'
        'll, "OnBuild": null, "Labels": null}, "Architecture": "amd64", "Os": "linux", "Size": 389770065, "Vi'
        'rtualSize": 389770065, "GraphDriver": {"Data": {"LowerDir": "re", "MergedDir": "mo", "UpperDir": "ve'
        'd", "WorkDir": "2"}, "Name": "overlay2"}, "RootFS": {"Type": "layers", "Layers": ["re", "mo", "ved"]'
        '}, "Metadata": {"LastTagTime": "2021-02-27T20:49:31.186386234+01:00"}}'
    ],
]


def test_inventory_docker_node_images():
    parsed = [line.split("\0") for line in AGENT_OUTPUT.split("\n")]
    assert sort_inventory_result(
        inventory_docker_node_images(parse_docker_node_images(parsed))
    ) == sort_inventory_result(
        [
            TableRow(
                path=["software", "applications", "docker", "images"],
                key_columns={
                    "id": "b2bf42ca5d8f",
                },
                inventory_columns={
                    "repotags": "hello:world",
                    "repodigests": "",
                    "creation": "2021-02-12T11:29:33.063968737Z",
                    "size": 1231733,
                    "labels": "image_label_command_line: 1, image_label_dockerfile: 2",
                },
                status_columns={
                    "amount_containers": 1,
                },
            ),
            TableRow(
                path=["software", "applications", "docker", "containers"],
                key_columns={
                    "id": "891a6f6a1c28",
                },
                inventory_columns={},
                status_columns={
                    "image": "b2bf42ca5d8f",
                    "name": "/relaxed_shaw",
                    "creation": "2021-02-12T12:15:28.230110819Z",
                    "labels": "another_container_label: 2, container: label, image_label_command_line: 1, image_label_dockerfile: 2",
                    "status": "running",
                },
            ),
        ]
    )


def test_inventory_docker_node_images_labels_null():
    assert sort_inventory_result(
        inventory_docker_node_images(parse_docker_node_images(AGENT_OUTPUT_NULL_LABELS_ST))
    ) == sort_inventory_result(
        [
            TableRow(
                path=["software", "applications", "docker", "images"],
                key_columns={
                    "id": "666620a54926",
                },
                inventory_columns={
                    "repotags": "plantuml:latest",
                    "repodigests": "",
                    "creation": "2021-02-25T08:42:22.47977742Z",
                    "size": 389770065,
                    "labels": "",
                },
                status_columns={
                    "amount_containers": 0,
                },
            ),
        ]
    )
