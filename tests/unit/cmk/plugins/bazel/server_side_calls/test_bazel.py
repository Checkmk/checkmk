#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.bazel.server_side_calls.special_agent import special_agent_bazel_cache
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="my_horst",
    ipv4_config=IPv4Config(address="17.1.10.93"),
)


def test_bazel_command_contains_all_configured_options() -> None:
    params = {
        "user": "username",
        "password": Secret(123),
        "port": 9090,
        "protocol": "https",
        "verify_cert": True,
    }

    commands = list(special_agent_bazel_cache(params, HOST_CONFIG))

    assert commands == [
        SpecialAgentCommand(
            command_arguments=[
                "--host",
                "my_horst",
                "--user",
                "username",
                "--password",
                Secret(123).unsafe(),
                "--port",
                "9090",
                "--protocol",
                "https",
            ]
        )
    ]


def test_bazel_command_verifies_certificate_when_verification_is_enabled() -> None:
    (command,) = special_agent_bazel_cache({"verify_cert": True}, HOST_CONFIG)

    assert "--no-cert-check" not in command.command_arguments


def test_bazel_command_skips_certificate_check_when_verification_is_disabled() -> None:
    (command,) = special_agent_bazel_cache({"verify_cert": False}, HOST_CONFIG)

    assert "--no-cert-check" in command.command_arguments


def test_bazel_command_reads_unmigrated_certificate_verification_setting() -> None:
    (command,) = special_agent_bazel_cache({"no_cert_check": True}, HOST_CONFIG)

    assert "--no-cert-check" not in command.command_arguments
