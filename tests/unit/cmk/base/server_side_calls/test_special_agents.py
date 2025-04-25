#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils import password_store

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    SpecialAgentCommand,
    SpecialAgentConfig,
)
from cmk.server_side_calls_backend import SpecialAgent
from cmk.server_side_calls_backend._special_agents import SpecialAgentCommandLine

HOST_ATTRS = {
    "alias": "my_host_alias",
    "_ADDRESS_4": "127.0.0.1",
    "address": "127.0.0.1",
    "_ADDRESS_FAMILY": "4",
    "_ADDRESSES_4": "127.0.0.1",
    "_ADDRESSES_6": "",
    "display_name": "my_host",
}

HOST_CONFIG = HostConfig(
    name="hostname",
    alias="host_alias",
    ipv4_config=IPv4Config(
        address="0.0.0.1",
        additional_addresses=["0.0.0.4", "0.0.0.5"],
    ),
    ipv6_config=IPv6Config(
        address="fe80::240",
        additional_addresses=["fe80::241", "fe80::242", "fe80::243"],
    ),
    primary_family=IPAddressFamily.IPV4,
)

HOST_CONFIG_WITH_MACROS = HostConfig(
    name="hostname",
    alias="host_alias",
    ipv4_config=IPv4Config(
        address="0.0.0.1",
        additional_addresses=["0.0.0.4", "0.0.0.5"],
    ),
    ipv6_config=IPv6Config(
        address="fe80::240",
        additional_addresses=["fe80::241", "fe80::242", "fe80::243"],
    ),
    primary_family=IPAddressFamily.IPV4,
    macros={
        "$HOSTNAME$": "test_host",
        "$HOSTADDRESS$": "0.0.0.0",
        "$HOSTALIAS$": "myalias",
        "<IP>": "127.0.0.1",
        "<HOST>": "test_host",
    },
)


class SpecialAgentLegacyConfiguration(NamedTuple):
    args: Sequence[str]
    stdin: str | None


@contextmanager
def _with_file(path: Path) -> Iterator[None]:
    present = path.exists()
    path.touch()
    try:
        yield
    finally:
        if not present:
            path.unlink(missing_ok=True)


def argument_function_with_exception(*args, **kwargs):
    raise RuntimeError("Can't create argument list")


@pytest.mark.parametrize(
    (
        "plugins",
        "parameters",
        "host_attrs",
        "host_config",
        "stored_passwords",
        "expected_result",
    ),
    [
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
                ): SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=lambda *_: (
                        [
                            SpecialAgentCommand(
                                command_arguments=["arg1", "arg2;1"],
                            ),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg1 'arg2;1'", None)],
            id="one command, escaped arg",
        ),
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
                ): SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=lambda *_: (
                        [
                            SpecialAgentCommand(command_arguments=["arg1", "arg2;1"]),
                            SpecialAgentCommand(command_arguments=["arg3", "arg4"]),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [
                SpecialAgentCommandLine("agent_path arg1 'arg2;1'", None),
                SpecialAgentCommandLine("agent_path arg3 arg4", None),
            ],
            id="multiple commands",
        ),
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
                ): SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=lambda *_: (
                        [
                            SpecialAgentCommand(
                                command_arguments=["-h", "<HOST>", "-a", "$HOSTADDRESS$"],
                            ),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
            HOST_CONFIG,
            {"mypassword": "123456"},
            [SpecialAgentCommandLine("agent_path -h '<HOST>' -a '$HOSTADDRESS$'", None)],
            id="command with macros",
        ),
    ],
)
def test_iter_special_agent_commands(
    plugins: Mapping[PluginLocation, SpecialAgentConfig],
    parameters: Mapping[str, object],
    host_attrs: Mapping[str, str],
    host_config: HostConfig,
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[SpecialAgentCommandLine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_AGENTS, "test_agent", True)

    special_agent = SpecialAgent(
        plugins,
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        host_config,
        host_attrs,
        http_proxies={},
        stored_passwords=stored_passwords,
        password_store_file=Path("/pw/store"),
        finder=lambda *_: "agent_path",
    )
    commands = list(special_agent.iter_special_agent_commands("test_agent", parameters))
    assert commands == expected_result


_PASSWORD_TEST_PLUGINS = {
    PluginLocation(
        "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
    ): SpecialAgentConfig(
        name="test_agent",
        parameter_parser=lambda e: e,
        commands_function=lambda p, *_: (
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--password-id",
                        p["password"],
                        "--password-plain-in-curly",
                        p["password"].unsafe("{%s}"),
                    ],
                ),
            ]
        ),
    )
}


def test_iter_special_agent_commands_stored_password_with_hack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_AGENTS, "test_agent", True)

    special_agent = SpecialAgent(
        plugins=_PASSWORD_TEST_PLUGINS,
        host_name=HostName("test_host"),
        host_address=HostAddress("127.0.0.1"),
        host_config=HOST_CONFIG,
        host_attrs=HOST_ATTRS,
        http_proxies={},
        stored_passwords={"1234": "p4ssw0rd!"},
        password_store_file=Path("/pw/store"),
        finder=lambda *_: "agent_path",
    )
    assert list(
        special_agent.iter_special_agent_commands(
            "test_agent",
            {"password": ("cmk_postprocessed", "explicit_password", ("1234", "p4ssw0rd!"))},
        )
    ) == [
        SpecialAgentCommandLine(
            "agent_path --pwstore=4@1@/pw/store@1234 --password-id 1234:/pw/store --password-plain-in-curly '{*********}'",
            None,
        )
    ]


def test_iter_special_agent_commands_stored_password_without_hack() -> None:
    special_agent = SpecialAgent(
        plugins=_PASSWORD_TEST_PLUGINS,
        host_name=HostName("test_host"),
        host_address=HostAddress("127.0.0.1"),
        host_config=HOST_CONFIG,
        host_attrs=HOST_ATTRS,
        http_proxies={},
        stored_passwords={"uuid1234": "p4ssw0rd!"},
        password_store_file=Path("/pw/store"),
        finder=lambda *_: "agent_path",
    )
    assert list(
        special_agent.iter_special_agent_commands(
            "test_agent",
            {"password": ("cmk_postprocessed", "explicit_password", ("uuid1234", "p4ssw0rd!"))},
        )
    ) == [
        SpecialAgentCommandLine(
            "agent_path --password-id uuid1234:/pw/store --password-plain-in-curly '{p4ssw0rd!}'",
            None,
        )
    ]


def test_iter_special_agent_commands_crash() -> None:
    special_agent = SpecialAgent(
        {
            PluginLocation(
                "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
            ): SpecialAgentConfig(
                name="test_agent",
                parameter_parser=lambda e: e,
                commands_function=argument_function_with_exception,
            )
        },
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        HOST_CONFIG,
        HOST_ATTRS,
        http_proxies={},
        stored_passwords={},
        password_store_file=Path("/pw/store"),
        finder=lambda *_: "/path/to/agent",
    )

    with pytest.raises(
        RuntimeError,
        match="Can't create argument list",
    ):
        list(special_agent.iter_special_agent_commands("test_agent", {}))
