#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.elasticsearch.server_side_calls.special_agent import special_agent_elasticsearch
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret

TEST_HOST_CONFIG = HostConfig(
    name="my_host",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)


def test_agent_elasticsearch_arguments_cert_check() -> None:
    params: dict[str, object] = {
        "hosts": ["testhost"],
        "protocol": "https",
        "infos": ["cluster_health", "nodestats", "stats"],
    }
    (cmd,) = special_agent_elasticsearch(params, TEST_HOST_CONFIG)
    assert "--no-cert-check" not in cmd.command_arguments

    params["no_cert_check"] = True
    (cmd,) = special_agent_elasticsearch(params, TEST_HOST_CONFIG)
    assert "--no-cert-check" in cmd.command_arguments


def test_agent_elasticsearch_arguments_password_store() -> None:
    params: dict[str, object] = {
        "hosts": ["testhost"],
        "protocol": "https",
        "cluster_health": True,
        "nodestats": False,
        "user": "user",
        "password": Secret(0),
    }
    (cmd,) = special_agent_elasticsearch(params, TEST_HOST_CONFIG)
    assert cmd.command_arguments == [
        "-P",
        "https",
        "-u",
        "user",
        "-s",
        Secret(0).unsafe(),
        "--cluster-health",
        "--",
        "testhost",
    ]


def test_agent_elasticsearch_stats() -> None:
    params: dict[str, object] = {
        "hosts": ["testhost"],
        "protocol": "https",
        "cluster_health": True,
        "nodestats": False,
        "stats": ["*-*", "indices", "jvm"],
        "user": "user",
        "password": Secret(0),
    }
    (cmd,) = special_agent_elasticsearch(params, TEST_HOST_CONFIG)
    assert cmd.command_arguments == [
        "-P",
        "https",
        "-u",
        "user",
        "-s",
        Secret(0).unsafe(),
        "--cluster-health",
        "--stats",
        "*-*",
        "indices",
        "jvm",
        "--",
        "testhost",
    ]
