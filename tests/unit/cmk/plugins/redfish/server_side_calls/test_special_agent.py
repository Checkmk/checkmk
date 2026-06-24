#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.plugins.redfish.server_side_calls.special_agent import special_agent_redfish
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret

_HOST = HostConfig(name="idrac", ipv4_config=IPv4Config(address="10.0.0.1"))

_BASE: Mapping[str, object] = {
    "user": "redfish",
    "password": Secret(1),
    "port": 443,
    "proto": "https",
    "retries": 2,
    "timeout": 3.0,
    "debug": False,
}


def _command_arguments(params: Mapping[str, object]) -> Sequence[object]:
    commands = list(special_agent_redfish(params, _HOST))
    assert len(commands) == 1
    return commands[0].command_arguments


def test_system_retry_args_emitted_when_set() -> None:
    args = _command_arguments({**_BASE, "system_retry": {"count": 3, "delay": 2.0}})
    assert "--systems_retries" in args
    assert args[args.index("--systems_retries") + 1] == "3"
    assert "--systems_retry_delay" in args
    assert args[args.index("--systems_retry_delay") + 1] == "2"


def test_system_retry_args_absent_when_unset() -> None:
    args = _command_arguments(dict(_BASE))
    assert "--systems_retries" not in args
    assert "--systems_retry_delay" not in args
