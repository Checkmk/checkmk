#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

import pytest

import cmk.utils.paths
from cmk.utils import password_store
from cmk.utils.hostaddress import HostAddress, HostName

import cmk.base.config as base_config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.server_side_calls import (
    ActiveCheck,
    ActiveServiceData,
    load_active_checks,
    load_special_agents,
    SpecialAgent,
    SpecialAgentInfoFunctionResult,
)
from cmk.base.server_side_calls._active_checks import (
    _get_host_address_config,
    ActiveServiceDescription,
    HostAddressConfiguration,
)
from cmk.base.server_side_calls._commons import (
    ActiveCheckError,
    commandline_arguments,
    InfoFunc,
)
from cmk.base.server_side_calls._special_agents import SpecialAgentCommandLine

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

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


@contextmanager
def _with_file(path: Path) -> Iterator[None]:
    present = path.exists()
    path.touch()
    try:
        yield
    finally:
        if not present:
            path.unlink(missing_ok=True)


def make_config_cache_mock(
    *,
    additional_ipaddresses: tuple[Sequence[str], Sequence[str]],
    ip_stack: ip_lookup.AddressFamily,
    family: socket.AddressFamily,
) -> object:
    class ConfigCacheMock:
        @staticmethod
        def address_family(host_name: str) -> ip_lookup.AddressFamily:
            return ip_stack

        @staticmethod
        def default_address_family(host_name: str) -> socket.AddressFamily:
            return family

        @staticmethod
        def additional_ipaddresses(
            host_name: str,
        ) -> tuple[Sequence[str], Sequence[str]]:
            return additional_ipaddresses

        @staticmethod
        def alias(host_name: str) -> str:
            return "host alias"

    return ConfigCacheMock()


class TestSpecialAgentLegacyConfiguration(NamedTuple):
    args: Sequence[str]
    stdin: str | None


def argument_function_with_exception(*args, **kwargs):
    raise Exception("Can't create argument list")


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins, hostname, host_attrs, host_config, stored_passwords, expected_result",
    [
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "Active check of $HOSTNAME$",
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Active check of myhost",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg1 arument1 --host_alias $HOSTALIAS$",
                    command_line="echo --arg1 arument1 --host_alias $HOSTALIAS$",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg1 arument1 --host_alias $HOSTALIAS$",
                    detected_executable="echo",
                ),
            ],
            id="one_active_service_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "Active check of $HOSTNAME$",
                }
            },
            {},
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "0.0.0.0",
                "address": "0.0.0.0",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Active check of myhost",
                    command="check-mk-custom",
                    command_display="check-mk-custom!--arg1 arument1 --host_alias $HOSTALIAS$",
                    command_line='echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2',
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg1 arument1 --host_alias $HOSTALIAS$",
                    detected_executable="echo",
                ),
            ],
            id="host_with_invalid_address_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "Active check of $HOSTNAME$",
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG_WITH_MACROS,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Active check of myhost",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg1 arument1 --host_alias myalias",
                    command_line="echo --arg1 arument1 --host_alias myalias",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg1 arument1 --host_alias myalias",
                    detected_executable="echo",
                ),
            ],
            id="macros_replaced_legacy_plugin",
        ),
        pytest.param(
            [
                ("http", [{"name": "myHTTPName on $HOSTALIAS$"}]),
            ],
            {
                "http": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "Active check of $HOSTALIAS$",
                }
            },
            {},
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "0.0.0.0",
                "address": "0.0.0.0",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="http",
                    description="HTTP myHTTPName on my_host_alias",
                    command="check-mk-custom",
                    command_display="check-mk-custom!--arg1 arument1 --host_alias $HOSTALIAS$",
                    command_line='echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2',
                    params={"name": "myHTTPName on $HOSTALIAS$"},
                    expanded_args="--arg1 arument1 --host_alias $HOSTALIAS$",
                    detected_executable="echo",
                ),
            ],
            id="http_active_service_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_generator": lambda *_: (
                        yield from [
                            ("First service", "--arg1 argument1"),
                            ("Second service", "--arg2 argument2"),
                        ]
                    ),
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="First service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg1 argument1",
                    command_line="echo --arg1 argument1",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg1 argument1",
                    detected_executable="echo",
                ),
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Second service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg2 argument2",
                    command_line="echo --arg2 argument2",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg2 argument2",
                    detected_executable="echo",
                ),
            ],
            id="multiple_active_services_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_generator": lambda *_: (
                        yield from [
                            ("My service", "--arg1 argument1"),
                            ("My service", "--arg2 argument2"),
                        ]
                    ),
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="My service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg1 argument1",
                    command_line="echo --arg1 argument1",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg1 argument1",
                    detected_executable="echo",
                ),
            ],
            id="multiple_services_with_the_same_description_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {},
            {
                PluginLocation(
                    # this is not what we'd expect here, but we need a module that we know to be importable.
                    f"{__name__}",
                    "active_check_my_active_check",
                ): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand(
                                service_description="First service",
                                command_arguments=["--arg1", "argument1"],
                            ),
                            ActiveCheckCommand(
                                service_description="Second service",
                                command_arguments=["--arg2", "argument2"],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="First service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg1 argument1",
                    command_line="check_my_active_check --arg1 argument1",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg1 argument1",
                    detected_executable="check_my_active_check",
                ),
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Second service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg2 argument2",
                    command_line="check_my_active_check --arg2 argument2",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg2 argument2",
                    detected_executable="check_my_active_check",
                ),
            ],
            id="multiple_services",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {},
            {},
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [],
            id="unimplemented_check_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [
                        {
                            "description": "My active check",
                            "password": (
                                "cmk_postprocessed",
                                "stored_password",
                                ("stored_password", ""),
                            ),
                        }
                    ],
                ),
            ],
            {},
            {
                PluginLocation(
                    # this is not what we'd expect here, but we need a module that we know to be importable.
                    f"{__name__}",
                    "active_check_my_active_check",
                ): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda p, *_: (
                        [
                            ActiveCheckCommand(
                                service_description="My service",
                                command_arguments=[
                                    p["password"].unsafe("--secret=%s"),
                                ],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            HOST_ATTRS,
            HOST_CONFIG,
            {"stored_password": "mypassword"},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="My service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--pwstore=1@9@/pw/store@stored_password '--secret=**********'",
                    command_line="check_my_active_check --pwstore=1@9@/pw/store@stored_password '--secret=**********'",
                    params={
                        "description": "My active check",
                        "password": (
                            "cmk_postprocessed",
                            "stored_password",
                            ("stored_password", ""),
                        ),
                    },
                    expanded_args="--pwstore=1@9@/pw/store@stored_password '--secret=**********'",
                    detected_executable="check_my_active_check",
                ),
            ],
            id="one_service_password_store",
        ),
    ],
)
def test_get_active_service_data(
    monkeypatch: pytest.MonkeyPatch,
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    host_config: HostConfig,
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", True)
    active_check = ActiveCheck(
        active_check_plugins,
        legacy_active_check_plugins,
        hostname,
        host_config,
        host_attrs,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords=stored_passwords,
        password_store_file=Path("/pw/store"),
    )

    services = list(active_check.get_active_service_data(active_check_rules))
    assert services == expected_result


_PASSWORD_TEST_ACTIVE_CHECKS = {
    PluginLocation(
        "cmk.plugins.test.server_side_calls.test_check",
        "active_check_test_check",
    ): ActiveCheckConfig(
        name="test_check",
        parameter_parser=lambda p: p,
        commands_function=lambda p, *_: (
            [
                ActiveCheckCommand(
                    service_description="My service",
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


def test_get_active_service_data_password_with_hack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ActiveCheck,
        "_get_command",
        lambda self, pn, cl: ("check_mk_active-check_path", f"/path/to/check_{pn}", cl),
    )
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "test_check", True)
    active_check = ActiveCheck(
        plugins=_PASSWORD_TEST_ACTIVE_CHECKS,
        legacy_plugins={},
        host_name=HostName("myhost"),
        host_config=HOST_CONFIG,
        host_attrs=HOST_ATTRS,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={"uuid1234": "p4ssw0rd!"},
        password_store_file=Path("/pw/store"),
    )

    assert list(
        active_check.get_active_service_data(
            [
                (
                    "test_check",
                    [
                        {
                            "description": "My active check",
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("uuid1234", "p4ssw0rd!"),
                            ),
                        }
                    ],
                )
            ]
        )
    ) == [
        ActiveServiceData(
            plugin_name="test_check",
            description="My service",
            command="check_mk_active-check_path",
            command_display="check_mk_active-check_path!--pwstore=4@1@/pw/store@uuid1234 --password-id uuid1234:/pw/store --password-plain-in-curly '{*********}'",
            command_line="check_test_check --pwstore=4@1@/pw/store@uuid1234 --password-id uuid1234:/pw/store --password-plain-in-curly '{*********}'",
            params={
                "description": "My active check",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid1234", "p4ssw0rd!"),
                ),
            },
            expanded_args="--pwstore=4@1@/pw/store@uuid1234 --password-id uuid1234:/pw/store --password-plain-in-curly '{*********}'",
            detected_executable="/path/to/check_test_check",
        ),
    ]


def test_get_active_service_data_password_without_hack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ActiveCheck,
        "_get_command",
        lambda self, pn, cl: ("check_mk_active-check_path", f"/path/to/check_{pn}", cl),
    )
    active_check = ActiveCheck(
        plugins=_PASSWORD_TEST_ACTIVE_CHECKS,
        legacy_plugins={},
        host_name=HostName("myhost"),
        host_config=HOST_CONFIG,
        host_attrs=HOST_ATTRS,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={"uuid1234": "p4ssw0rd!"},
        password_store_file=Path("/pw/store"),
    )

    assert list(
        active_check.get_active_service_data(
            [
                (
                    "test_check",
                    [
                        {
                            "description": "My active check",
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("uuid1234", "p4ssw0rd!"),
                            ),
                        }
                    ],
                )
            ]
        )
    ) == [
        ActiveServiceData(
            plugin_name="test_check",
            description="My service",
            command="check_mk_active-check_path",
            command_display="check_mk_active-check_path!--password-id uuid1234:/pw/store --password-plain-in-curly '{p4ssw0rd\\!}'",
            command_line="check_test_check --password-id uuid1234:/pw/store --password-plain-in-curly '{p4ssw0rd!}'",
            params={
                "description": "My active check",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid1234", "p4ssw0rd!"),
                ),
            },
            expanded_args="--password-id uuid1234:/pw/store --password-plain-in-curly '{p4ssw0rd\\!}'",
            detected_executable="/path/to/check_test_check",
        ),
    ]


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins",
    [
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {},
            {
                PluginLocation(
                    "cmk.plugins.my_stuff.server_side_calls",
                    "active_check_my_active_check",
                ): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=argument_function_with_exception,
                )
            },
            id="active check",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_generator": argument_function_with_exception,
                }
            },
            {},
            id="legacy active check",
        ),
    ],
)
def test_test_get_active_service_data_crash(
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: False,
    )

    active_check = ActiveCheck(
        active_check_plugins,
        legacy_active_check_plugins,
        HostName("test_host"),
        HOST_CONFIG,
        HOST_ATTRS,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    list(active_check.get_active_service_data(active_check_rules))

    assert (
        capsys.readouterr().err
        == "\nWARNING: Config creation for active check my_active_check failed on test_host: Can't create argument list\n"
    )


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins",
    [
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {},
            {
                PluginLocation(
                    "cmk.plugins.my_stuff.server_side_calls",
                    "active_check_my_active_check",
                ): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=argument_function_with_exception,
                )
            },
            id="active check",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_generator": argument_function_with_exception,
                }
            },
            {},
            id="legacy active check",
        ),
    ],
)
def test_test_get_active_service_data_crash_with_debug(
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    active_check = ActiveCheck(
        active_check_plugins,
        legacy_active_check_plugins,
        HostName("test_host"),
        HOST_CONFIG,
        HOST_ATTRS,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    with pytest.raises(
        Exception,
        match="Can't create argument list",
    ):
        list(active_check.get_active_service_data(active_check_rules))


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins, hostname, host_attrs, expected_result, expected_warning",
    [
        pytest.param(
            [
                ("my_active_check", [{}]),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "",
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            [],
            "\nWARNING: Skipping invalid service with empty description (active check: my_active_check) on host myhost\n",
            id="empty_description",
        ),
        pytest.param(
            [
                ("my_active_check", [{}]),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_description": lambda _: "Active check of $HOSTNAME$",
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            [],
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plug-in is missing an argument function or a service description\n",
            id="invalid_plugin_info",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [
                        {
                            "description": "My active check",
                            "password": (
                                "cmk_postprocessed",
                                "stored_password",
                                ("stored_password", ""),
                            ),
                        }
                    ],
                ),
            ],
            {},
            {
                PluginLocation(
                    # this is not what we'd expect here, but we need a module that we know to be importable.
                    f"{__name__}",
                    "active_check_my_active_check",
                ): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda p, *_: (
                        [
                            ActiveCheckCommand(
                                service_description="My service",
                                command_arguments=[
                                    "--password",
                                    p["password"].unsafe(),
                                ],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "_ADDRESSES_4": "127.0.0.1",
                "_ADDRESSES_6": "",
                "display_name": "my_host",
            },
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="My service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--pwstore=2@0@/pw/store@stored_password "
                    "--password '***'",
                    command_line="check_my_active_check "
                    "--pwstore=2@0@/pw/store@stored_password --password "
                    "'***'",
                    params={
                        "description": "My active check",
                        "password": (
                            "cmk_postprocessed",
                            "stored_password",
                            ("stored_password", ""),
                        ),
                    },
                    expanded_args="--pwstore=2@0@/pw/store@stored_password --password '***'",
                    detected_executable="check_my_active_check",
                ),
            ],
            '\nWARNING: The stored password "stored_password" used by host "myhost" does not exist (anymore).\n',
            id="stored_password_missing",
        ),
    ],
)
def test_get_active_service_data_warnings(
    monkeypatch: pytest.MonkeyPatch,
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", True)
    active_check_config = ActiveCheck(
        active_check_plugins,
        legacy_active_check_plugins,
        hostname,
        HOST_CONFIG,
        host_attrs,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    services = list(active_check_config.get_active_service_data(active_check_rules))

    assert services == expected_result
    assert capsys.readouterr().err == expected_warning


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins, hostname, host_attrs, expected_result",
    [
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "Active check of $HOSTNAME$",
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            [
                ActiveServiceDescription(
                    plugin_name="my_active_check",
                    description="Active check of myhost",
                    params={"description": "My active check", "param1": "param1"},
                ),
            ],
            id="one_service_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_generator": lambda *_: (
                        yield from [
                            ("First service", "--arg1 argument1"),
                            ("Second service", "--arg2 argument2"),
                        ]
                    ),
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            [
                ActiveServiceDescription(
                    plugin_name="my_active_check",
                    description="First service",
                    params={"description": "My active check", "param1": "param1"},
                ),
                ActiveServiceDescription(
                    plugin_name="my_active_check",
                    description="Second service",
                    params={"description": "My active check", "param1": "param1"},
                ),
            ],
            id="multiple_active_services_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "service_generator": lambda *_: (
                        yield from [
                            ("My service", "--arg1 argument1"),
                            ("My service", "--arg2 argument2"),
                        ]
                    ),
                }
            },
            {},
            HostName("myhost"),
            HOST_ATTRS,
            [
                ActiveServiceDescription(
                    plugin_name="my_active_check",
                    description="My service",
                    params={"description": "My active check", "param1": "param1"},
                ),
                ActiveServiceDescription(
                    plugin_name="my_active_check",
                    description="My service",
                    params={"description": "My active check", "param1": "param1"},
                ),
            ],
            id="multiple_services_with_the_same_description_legacy_plugin",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [
                        {
                            "description": "My active check",
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                (":uuid:1234", "myp4ssw0rd"),
                            ),
                        }
                    ],
                ),
            ],
            {},
            {
                PluginLocation(
                    # this is not what we'd expect here, but we need a module that we know to be importable.
                    f"{__name__}",
                    "active_check_my_active_check",
                ): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda p, *_: (
                        [
                            ActiveCheckCommand(
                                service_description="My service",
                                command_arguments=["--password", p["password"]],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "_ADDRESSES_4": "127.0.0.1",
                "_ADDRESSES_6": "",
                "display_name": "my_host",
            },
            [
                ActiveServiceDescription(
                    plugin_name="my_active_check",
                    description="My service",
                    params={
                        "description": "My active check",
                        "password": (
                            "cmk_postprocessed",
                            "explicit_password",
                            (":uuid:1234", "myp4ssw0rd"),
                        ),
                    },
                ),
            ],
            id="one_service",
        ),
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {},
            {},
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "_ADDRESSES_4": "127.0.0.1",
                "_ADDRESSES_6": "",
                "display_name": "my_host",
            },
            [],
            id="unimplemented_plugin",
        ),
    ],
)
def test_get_active_service_descriptions(
    monkeypatch: pytest.MonkeyPatch,
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceDescription],
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", True)
    active_check_config = ActiveCheck(
        active_check_plugins,
        legacy_active_check_plugins,
        hostname,
        HOST_CONFIG,
        host_attrs,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    descriptions = list(active_check_config.get_active_service_descriptions(active_check_rules))
    assert descriptions == expected_result


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, hostname, host_attrs, expected_result, expected_warning",
    [
        pytest.param(
            [
                (
                    "my_active_check",
                    [{"description": "My active check", "param1": "param1"}],
                ),
            ],
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                }
            },
            HostName("myhost"),
            HOST_ATTRS,
            [],
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plug-in is missing an argument function or a service description\n",
            id="invalid_plugin_info",
        ),
    ],
)
def test_get_active_service_descriptions_warnings(
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceDescription],
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    active_check_config = ActiveCheck(
        {},
        legacy_active_check_plugins,
        hostname,
        HOST_CONFIG,
        host_attrs,
        http_proxies={},
        service_name_finalizer=lambda x: x,
        use_new_descriptions_for=[],
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    descriptions = list(active_check_config.get_active_service_descriptions(active_check_rules))

    assert descriptions == expected_result
    assert capsys.readouterr().err == expected_warning


@pytest.mark.parametrize(
    "hostname, host_attrs, expected_result",
    [
        (
            "myhost",
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESSES_4": "127.0.0.2 127.0.0.3",
                "_ADDRESSES_4_1": "127.0.0.2",
                "_ADDRESSES_4_2": "127.0.0.3",
            },
            HostAddressConfiguration(
                hostname="myhost",
                host_address="127.0.0.1",
                alias="my_host_alias",
                ipv4address="127.0.0.1",
                ipv6address=None,
                indexed_ipv4addresses={
                    "$_HOSTADDRESSES_4_1$": "127.0.0.2",
                    "$_HOSTADDRESSES_4_2$": "127.0.0.3",
                },
                indexed_ipv6addresses={},
            ),
        )
    ],
)
def test_get_host_address_config(
    hostname: str,
    host_attrs: base_config.ObjectAttributes,
    expected_result: HostAddressConfiguration,
) -> None:
    host_config = _get_host_address_config(hostname, host_attrs)
    assert host_config == expected_result


def mock_ip_address_of(
    config_cache: base_config.ConfigCache,
    host_name: HostName,
    family: socket.AddressFamily | ip_lookup.AddressFamily,
) -> HostAddress | None:
    if family == socket.AF_INET:
        return HostAddress("0.0.0.1")

    return HostAddress("::1")


def test_get_host_config_macros_stringified() -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([], []),
        ip_stack=ip_lookup.AddressFamily.NO_IP,
        family=socket.AddressFamily.AF_INET,
    )

    host_config = base_config.get_ssc_host_config(
        HostName("host_name"),
        config_cache,  # type: ignore[arg-type]
        {"$HOST_EC_SL$": 30},
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        macros={"$HOST_EC_SL$": "30"},
    )


def test_get_host_config_no_ip() -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=(
            [HostAddress("ignore.v4.noip")],
            [HostAddress("ignore.v6.noip")],
        ),
        ip_stack=ip_lookup.AddressFamily.NO_IP,
        family=socket.AddressFamily.AF_INET6,
    )

    host_config = base_config.get_ssc_host_config(
        HostName("host_name"),
        config_cache,  # type: ignore[arg-type]
        {},
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        primary_family=IPAddressFamily.IPV6,
        macros={},
    )


def test_get_host_config_ipv4(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=(
            [HostAddress("1.2.3.4")],
            [HostAddress("ignore.v6.noip")],
        ),
        ip_stack=ip_lookup.AddressFamily.IPv4,
        family=socket.AddressFamily.AF_INET,
    )

    monkeypatch.setattr(base_config, "ip_address_of", mock_ip_address_of)

    host_config = base_config.get_ssc_host_config(
        HostName("host_name"),
        config_cache,  # type: ignore[arg-type]
        {},
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        ipv4_config=IPv4Config(
            address="0.0.0.1",
            additional_addresses=["1.2.3.4"],
        ),
        primary_family=IPAddressFamily.IPV4,
        macros={},
    )


def test_get_host_config_ipv6(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([HostAddress("ignore.v4.ipv6")], [HostAddress("::42")]),
        ip_stack=ip_lookup.AddressFamily.IPv6,
        family=socket.AddressFamily.AF_INET6,
    )

    monkeypatch.setattr(base_config, "ip_address_of", mock_ip_address_of)

    host_config = base_config.get_ssc_host_config(
        HostName("host_name"),
        config_cache,  # type: ignore[arg-type]
        {},
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        ipv6_config=IPv6Config(
            address="::1",
            additional_addresses=["::42"],
        ),
        primary_family=IPAddressFamily.IPV6,
        macros={},
    )


def test_get_host_config_dual(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([HostAddress("2.3.4.2")], [HostAddress("::42")]),
        ip_stack=ip_lookup.AddressFamily.DUAL_STACK,
        family=socket.AddressFamily.AF_INET6,
    )

    monkeypatch.setattr(base_config, "ip_address_of", mock_ip_address_of)

    host_config = base_config.get_ssc_host_config(
        HostName("host_name"),
        config_cache,  # type: ignore[arg-type]
        {},
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        ipv4_config=IPv4Config(
            address="0.0.0.1",
            additional_addresses=["2.3.4.2"],
        ),
        ipv6_config=IPv6Config(
            address="::1",
            additional_addresses=["::42"],
        ),
        primary_family=IPAddressFamily.IPV6,
        macros={},
    )


@pytest.mark.parametrize(
    (
        "plugins",
        "legacy_plugins",
        "parameters",
        "host_attrs",
        "host_config",
        "stored_passwords",
        "expected_result",
    ),
    [
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: "arg0 arg;1"},
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 arg;1", None)],
            id="legacy plug-in string args",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: ["arg0", "arg;1"]},
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", None)],
            id="legacy plug-in list args",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: TestSpecialAgentLegacyConfiguration(["arg0"], None)},
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0", None)],
            id="legacy plug-in TestSpecialAgentConfiguration",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: TestSpecialAgentLegacyConfiguration(
                    ["arg0", "arg;1"], None
                )
            },
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", None)],
            id="legacy plug-in TestSpecialAgentConfiguration, escaped arg",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: TestSpecialAgentLegacyConfiguration(
                    ["list0", "list1"], None
                )
            },
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path list0 list1", None)],
            id="legacy plug-in TestSpecialAgentConfiguration, arg list",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: TestSpecialAgentLegacyConfiguration(
                    ["arg0", "arg;1"], "stdin_blob"
                )
            },
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", "stdin_blob")],
            id="legacy plug-in with stdin, escaped arg",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: TestSpecialAgentLegacyConfiguration(
                    ["list0", "list1"], "stdin_blob"
                )
            },
            {},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path list0 list1", "stdin_blob")],
            id="legacy plug-in with stdin",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: ["-h", "$HOSTNAME$", "-a", "<IP>"]},
            {},
            {},
            HOST_CONFIG_WITH_MACROS,
            {},
            [SpecialAgentCommandLine("agent_path -h 'test_host' -a '127.0.0.1'", None)],
            id="legacy plug-in with macros",
        ),
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent",
                    "special_agent_text",
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
                    "cmk.plugins.test.server_side_calls.test_agent",
                    "special_agent_text",
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
                    "cmk.plugins.test.server_side_calls.test_agent",
                    "special_agent_text",
                ): SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=lambda *_: (
                        [
                            SpecialAgentCommand(
                                command_arguments=[
                                    "-h",
                                    "<HOST>",
                                    "-a",
                                    "$HOSTADDRESS$",
                                ],
                            ),
                        ]
                    ),
                )
            },
            {},
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
    legacy_plugins: Mapping[str, InfoFunc],
    parameters: Mapping[str, object],
    host_attrs: Mapping[str, str],
    host_config: HostConfig,
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[SpecialAgentCommandLine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SpecialAgent, "_make_source_path", lambda *_: "agent_path")
    monkeypatch.setitem(password_store.hack.HACK_AGENTS, "test_agent", True)

    special_agent = SpecialAgent(
        plugins,
        legacy_plugins,
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        host_config,
        host_attrs,
        http_proxies={},
        stored_passwords=stored_passwords,
        password_store_file=Path("/pw/store"),
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
    monkeypatch.setattr(SpecialAgent, "_make_source_path", lambda *_: "agent_path")
    monkeypatch.setitem(password_store.hack.HACK_AGENTS, "test_agent", True)

    special_agent = SpecialAgent(
        plugins=_PASSWORD_TEST_PLUGINS,
        legacy_plugins={},
        host_name=HostName("test_host"),
        host_address=HostAddress("127.0.0.1"),
        host_config=HOST_CONFIG,
        host_attrs=HOST_ATTRS,
        http_proxies={},
        stored_passwords={"1234": "p4ssw0rd!"},
        password_store_file=Path("/pw/store"),
    )
    assert list(
        special_agent.iter_special_agent_commands(
            "test_agent",
            {
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("1234", "p4ssw0rd!"),
                )
            },
        )
    ) == [
        SpecialAgentCommandLine(
            "agent_path --pwstore=4@1@/pw/store@1234 --password-id 1234:/pw/store --password-plain-in-curly '{*********}'",
            None,
        )
    ]


def test_iter_special_agent_commands_stored_password_without_hack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SpecialAgent, "_make_source_path", lambda *_: "agent_path")

    special_agent = SpecialAgent(
        plugins=_PASSWORD_TEST_PLUGINS,
        legacy_plugins={},
        host_name=HostName("test_host"),
        host_address=HostAddress("127.0.0.1"),
        host_config=HOST_CONFIG,
        host_attrs=HOST_ATTRS,
        http_proxies={},
        stored_passwords={"uuid1234": "p4ssw0rd!"},
        password_store_file=Path("/pw/store"),
    )
    assert list(
        special_agent.iter_special_agent_commands(
            "test_agent",
            {
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid1234", "p4ssw0rd!"),
                )
            },
        )
    ) == [
        SpecialAgentCommandLine(
            "agent_path --password-id uuid1234:/pw/store --password-plain-in-curly '{p4ssw0rd!}'",
            None,
        )
    ]


@pytest.mark.parametrize(
    "plugins, legacy_plugins",
    [
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent",
                    "special_agent_text",
                ): SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=argument_function_with_exception,
                )
            },
            {},
            id="special agent",
        ),
        pytest.param(
            {},
            {"test_agent": argument_function_with_exception},
            id="legacy special agent",
        ),
    ],
)
def test_iter_special_agent_commands_crash(
    plugins: Mapping[PluginLocation, SpecialAgentConfig],
    legacy_plugins: Mapping[str, InfoFunc],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: False,
    )

    special_agent = SpecialAgent(
        plugins,
        legacy_plugins,
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        HOST_CONFIG,
        HOST_ATTRS,
        http_proxies={},
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    list(special_agent.iter_special_agent_commands("test_agent", {}))

    assert (
        capsys.readouterr().err
        == "\nWARNING: Config creation for special agent test_agent failed on test_host: Can't create argument list\n"
    )


@pytest.mark.parametrize(
    "plugins, legacy_plugins",
    [
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent",
                    "special_agent_text",
                ): SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=argument_function_with_exception,
                )
            },
            {},
            id="special agent",
        ),
        pytest.param(
            {},
            {"test_agent": argument_function_with_exception},
            id="legacy special agent",
        ),
    ],
)
def test_iter_special_agent_commands_crash_with_debug(
    plugins: Mapping[PluginLocation, SpecialAgentConfig],
    legacy_plugins: Mapping[str, InfoFunc],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    special_agent = SpecialAgent(
        plugins,
        legacy_plugins,
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        HOST_CONFIG,
        HOST_ATTRS,
        http_proxies={},
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    with pytest.raises(
        Exception,
        match="Can't create argument list",
    ):
        list(special_agent.iter_special_agent_commands("test_agent", {}))


def test_make_source_path() -> None:
    special_agent = SpecialAgent(
        {},
        {},
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        HOST_CONFIG,
        host_attrs={},
        http_proxies={},
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    shipped_path = Path(cmk.utils.paths.agents_dir, "special", "agent_test_agent")
    with _with_file(shipped_path):
        agent_path = special_agent._make_source_path("test_agent")

    assert agent_path == shipped_path


def test_make_source_path_local_agent() -> None:
    special_agent = SpecialAgent(
        {},
        {},
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        HOST_CONFIG,
        host_attrs={},
        http_proxies={},
        stored_passwords={},
        password_store_file=Path("/pw/store"),
    )

    local_agent_path = Path(cmk.utils.paths.agents_dir, "special", "agent_test_agent")
    with _with_file(local_agent_path):
        agent_path = special_agent._make_source_path("test_agent")

    assert agent_path == local_agent_path


@pytest.mark.parametrize(
    "args, passwords, expected_result",
    [
        pytest.param("args 123 -x 1 -y 2", {}, "args 123 -x 1 -y 2", id="string argument"),
        pytest.param(
            ["args", "1; echo", "-x", "1", "-y", "2"],
            {},
            "args '1; echo' -x 1 -y 2",
            id="list argument",
        ),
        pytest.param(
            ["args", "1 2 3", "-d=2", "--hallo=eins", 9],
            {},
            "args '1 2 3' -d=2 --hallo=eins 9",
            id="list argument with numbers",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
            {"pw-id": "aädg"},
            "--pwstore=2@11@/my/password/store@pw-id arg1 '--password=*****' arg3",
            id="password store argument",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id; echo HI;", "--password=%s"), "arg3"],
            {"pw-id; echo HI;": "the password"},
            "'--pwstore=2@11@/my/password/store@pw-id; echo HI;' arg1 '--password=************' arg3",
            id="password store sanitization (CMK-14149)",
        ),
    ],
)
def test_commandline_arguments(
    args: SpecialAgentInfoFunctionResult,
    passwords: Mapping[str, str],
    expected_result: str,
) -> None:
    cmdline_args = commandline_arguments(
        HostName("test"),
        "test service",
        args,
        passwords,
        Path("/my/password/store"),
    )
    assert cmdline_args == expected_result


@pytest.mark.parametrize(
    "host_name, service_name, expected_warning",
    [
        pytest.param(
            HostName("test"),
            "test service",
            'The stored password "pw-id" used by service "test service" on host "test" does not exist (anymore).',
            id="host and service names present",
        ),
        pytest.param(
            HostName("test"),
            None,
            'The stored password "pw-id" used by host "test" does not exist (anymore).',
            id="service name not present",
        ),
        pytest.param(
            None,
            None,
            'The stored password "pw-id" does not exist (anymore).',
            id="host and service names not present",
        ),
    ],
)
def test_commandline_arguments_nonexisting_password(
    host_name: HostName,
    service_name: str,
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commandline_arguments(
        host_name,
        service_name,
        ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
        {},
        Path("/pw/store"),
    )
    captured = capsys.readouterr()
    assert expected_warning in captured.err


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(None, id="None argument"),
        pytest.param(1, id="integer argument"),
        pytest.param((1, 2), id="integer tuple"),
    ],
)
def test_commandline_arguments_invalid_arguments_type(
    args: int | tuple[int, int] | None,
) -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"The check argument function needs to return either a list of arguments or a string of the concatenated arguments \(Service: test service\).",
    ):
        commandline_arguments(
            HostName("test"),
            "test service",
            args,  # type: ignore[arg-type]
            {},
            Path("/pw/store"),
        )


def test_commandline_arguments_invalid_argument() -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"Invalid argument for command line: \(1, 2\)",
    ):
        commandline_arguments(
            HostName("test"),
            "test service",
            ["arg1", (1, 2), "arg3"],  # type: ignore[list-item]
            {},
            Path("/pw/store"),
        )


def test_hack_apply_map_special_agents_is_complete() -> None:
    assert set(password_store.hack.HACK_AGENTS) == {
        p.name for p in load_special_agents()[1].values()
    }


def test_hack_apply_map_active_checks_is_complete() -> None:
    assert set(password_store.hack.HACK_CHECKS) == {
        p.name for p in load_active_checks()[1].values()
    }
