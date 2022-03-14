#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_docker_container_labels import (
    inventory_docker_container_labels,
    parse_docker_container_labels,
)

from .utils_inventory import sort_inventory_result

AGENT_OUTPUT = (
    '@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}\n'
    '{"com.docker.swarm.node.id": "x2my5tv8bqg0yh5jq98gzodr2", '
    '"com.docker.swarm.service.id": "nrgxet23d204ywz1rjl8fbtff", '
    '"com.docker.swarm.service.name": "redis", '
    '"com.docker.swarm.task": "", '
    '"com.docker.swarm.task.id": "jjp7380fb51n4figvv4zxl350", '
    '"com.docker.swarm.task.name": "redis.1.jjp7380fb51n4figvv4zxl350"}'
)


def test_inv_docker_container_labels_parse():
    info = [line.split("\0") for line in AGENT_OUTPUT.split("\n")]
    assert parse_docker_container_labels(info) == {
        "com.docker.swarm.node.id": "x2my5tv8bqg0yh5jq98gzodr2",
        "com.docker.swarm.service.id": "nrgxet23d204ywz1rjl8fbtff",
        "com.docker.swarm.service.name": "redis",
        "com.docker.swarm.task": "",
        "com.docker.swarm.task.id": "jjp7380fb51n4figvv4zxl350",
        "com.docker.swarm.task.name": "redis.1.jjp7380fb51n4figvv4zxl350",
    }


def test_inv_docker_container_labels():
    info = [line.split("\0") for line in AGENT_OUTPUT.split("\n")]
    assert sort_inventory_result(
        inventory_docker_container_labels(parse_docker_container_labels(info))
    ) == sort_inventory_result(
        [
            Attributes(
                path=["software", "applications", "docker", "container"],
                inventory_attributes={
                    "labels": (
                        "com.docker.swarm.node.id: x2my5tv8bqg0yh5jq98gzodr2, "
                        "com.docker.swarm.service.id: nrgxet23d204ywz1rjl8fbtff, "
                        "com.docker.swarm.service.name: redis, "
                        "com.docker.swarm.task: , "
                        "com.docker.swarm.task.id: jjp7380fb51n4figvv4zxl350, "
                        "com.docker.swarm.task.name: redis.1.jjp7380fb51n4figvv4zxl350"
                    )
                },
                status_attributes={},
            )
        ]
    )
