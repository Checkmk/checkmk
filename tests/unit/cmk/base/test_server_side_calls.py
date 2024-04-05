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
import cmk.utils.version as cmk_version
from cmk.utils import password_store
from cmk.utils.hostaddress import HostAddress, HostName

import cmk.base.config as base_config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.server_side_calls import (
    ActiveCheck,
    ActiveServiceData,
    SpecialAgent,
    SpecialAgentInfoFunctionResult,
)
from cmk.base.server_side_calls._active_checks import (
    _get_host_address_config,
    ActiveServiceDescription,
    HostAddressConfiguration,
)
from cmk.base.server_side_calls._commons import ActiveCheckError, commandline_arguments, InfoFunc
from cmk.base.server_side_calls._special_agents import SpecialAgentCommandLine

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    PlainTextSecret,
    ResolvedIPAddressFamily,
    SpecialAgentCommand,
    SpecialAgentConfig,
    StoredSecret,
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
    resolved_address="0.0.0.1",
    alias="host_alias",
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.DUAL_STACK,
        ipv4_address="0.0.0.2",
        ipv6_address="fe80::240",
        additional_ipv4_addresses=["0.0.0.4", "0.0.0.5"],
        additional_ipv6_addresses=[
            "fe80::241",
            "fe80::242",
            "fe80::243",
        ],
    ),
)

HOST_CONFIG_WITH_MACROS = HostConfig(
    name="hostname",
    resolved_address="0.0.0.1",
    alias="host_alias",
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.DUAL_STACK,
        ipv4_address="0.0.0.2",
        ipv6_address="fe80::240",
        additional_ipv4_addresses=["0.0.0.4", "0.0.0.5"],
        additional_ipv6_addresses=[
            "fe80::241",
            "fe80::242",
            "fe80::243",
        ],
    ),
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


class ConfigCacheMock:
    def __init__(
        self,
        alias: str,
        additional_ipaddresses: tuple[Sequence[str], Sequence[str]],
        tags: Mapping[str, str],
        labels: Mapping[str, str],
    ):
        self._tags = tags
        self._labels = labels
        self._alias = alias
        self._additional_ipaddresses = additional_ipaddresses

    @staticmethod
    def address_family(host_name: str) -> ip_lookup.AddressFamily:
        host_family_mapping = {"host_name": ip_lookup.AddressFamily.DUAL_STACK}
        return host_family_mapping[host_name]

    def additional_ipaddresses(self, _host_name: str) -> tuple[Sequence[str], Sequence[str]]:
        return self._additional_ipaddresses

    def explicit_host_attributes(self, _host_name: str) -> Mapping[str, str]:
        return {"_attr1": "value1"}

    def alias(self, _host_name: str) -> str:
        return self._alias

    def labels(self, _host_name: str) -> Mapping[str, str]:
        return self._labels

    def tags(self, _host_name: str) -> Mapping[str, str]:
        return self._tags


class SpecialAgentLegacyConfiguration(NamedTuple):
    args: Sequence[str]
    stdin: str | None


def argument_function_with_exception(*args, **kwargs):
    raise Exception("Can't create argument list")


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins, hostname, host_attrs, host_config, stored_passwords, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ),
            ],
            id="one_active_service_legacy_plugin",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ),
            ],
            id="host_with_invalid_address_legacy_plugin",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ),
            ],
            id="http_active_service_legacy_plugin",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ),
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Second service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg2 argument2",
                    command_line="echo --arg2 argument2",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg2 argument2",
                ),
            ],
            id="multiple_active_services_legacy_plugin",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ),
            ],
            id="multiple_services_with_the_same_description_legacy_plugin",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ),
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Second service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--arg2 argument2",
                    command_line="check_my_active_check --arg2 argument2",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--arg2 argument2",
                ),
            ],
            id="multiple_services",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                                service_description="My service",
                                command_arguments=[
                                    "--password",
                                    PlainTextSecret(value="mypassword"),
                                ],
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
                    description="My service",
                    command="check_mk_active-my_active_check",
                    command_display="check_mk_active-my_active_check!--password mypassword",
                    command_line="check_my_active_check --password mypassword",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--password mypassword",
                ),
            ],
            id="one_service_password",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                                service_description="My service",
                                command_arguments=[
                                    "--password",
                                    StoredSecret(value="stored_password"),
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
                    command_display="check_mk_active-my_active_check!--pwstore=2@0@stored_password --password '**********'",
                    command_line="check_my_active_check --pwstore=2@0@stored_password --password '**********'",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--pwstore=2@0@stored_password --password '**********'",
                ),
            ],
            id="one_service_password_store",
        ),
    ],
)
def test_get_active_service_data(
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    host_config: HostConfig,
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
) -> None:
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
    )

    services = list(active_check.get_active_service_data(active_check_rules))
    assert services == expected_result


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {},
            {
                PluginLocation(
                    "cmk.plugins.my_stuff.server_side_calls", "active_check_my_active_check"
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
    )

    list(active_check.get_active_service_data(active_check_rules))

    captured = capsys.readouterr()
    assert (
        captured.out
        == "\nWARNING: Config creation for active check my_active_check failed on test_host: Can't create argument list\n"
    )


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {},
            {
                PluginLocation(
                    "cmk.plugins.my_stuff.server_side_calls", "active_check_my_active_check"
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plugin is missing an argument function or a service description\n",
            id="invalid_plugin_info",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                                service_description="My service",
                                command_arguments=[
                                    "--password",
                                    StoredSecret(value="stored_password"),
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
                    command_display="check_mk_active-my_active_check!--pwstore=2@0@stored_password "
                    "--password '***'",
                    command_line="check_my_active_check "
                    "--pwstore=2@0@stored_password --password "
                    "'***'",
                    params={"description": "My active check", "param1": "param1"},
                    expanded_args="--pwstore=2@0@stored_password --password " "'***'",
                ),
            ],
            '\nWARNING: The stored password "stored_password" used by host "myhost" does not exist.\n',
            id="stored_password_missing",
        ),
    ],
)
def test_get_active_service_data_warnings(
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
    )

    services = list(active_check_config.get_active_service_data(active_check_rules))
    assert services == expected_result

    captured = capsys.readouterr()
    assert captured.out == expected_warning


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins, hostname, host_attrs, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
                                service_description="My service",
                                command_arguments=["--password", StoredSecret(value="mypassword")],
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
                    params={"description": "My active check", "param1": "param1"},
                ),
            ],
            id="one_service",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
    active_check_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    legacy_active_check_plugins: Mapping[str, Mapping[str, str]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceDescription],
) -> None:
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
    )

    descriptions = list(active_check_config.get_active_service_descriptions(active_check_rules))
    assert descriptions == expected_result


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, hostname, host_attrs, expected_result, expected_warning",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plugin is missing an argument function or a service description\n",
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
    )

    descriptions = list(active_check_config.get_active_service_descriptions(active_check_rules))
    assert descriptions == expected_result

    captured = capsys.readouterr()
    assert captured.out == expected_warning


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


def test_get_host_config(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = ConfigCacheMock(
        "alias",
        ([], [HostAddress("fe80::241"), HostAddress("fe80::242"), HostAddress("fe80::243")]),
        {"tag1": "value1", "tag2": "value2"},
        {"label1": "value1", "label2": "value2"},
    )

    monkeypatch.setattr(base_config, "ConfigCache", ConfigCacheMock)
    monkeypatch.setattr(base_config, "ipaddresses", {"host_name": ""})
    monkeypatch.setattr(base_config, "ipv6addresses", {"host_name": HostAddress("::1")})
    monkeypatch.setattr(base_config, "resolve_address_family", lambda *args: socket.AF_INET6)
    monkeypatch.setattr(cmk_version, "edition", lambda: cmk_version.Edition.CEE)
    monkeypatch.setattr(base_config, "ip_address_of", mock_ip_address_of)

    host_config = base_config.get_ssc_host_config(
        HostName("host_name"),
        config_cache,  # type: ignore[arg-type]
        {
            "$HOSTNAME$": "test_host",
            "$HOSTADDRESS$": "0.0.0.0",
            "HOSTALIAS": "test alias",
            "$HOST_EC_SL$": 30,
        },
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="alias",
        resolved_address="::1",
        resolved_ipv4_address="0.0.0.1",
        resolved_ipv6_address="::1",
        address_config=NetworkAddressConfig(
            ip_family=IPAddressFamily.DUAL_STACK,
            ipv4_address=None,
            ipv6_address="::1",
            additional_ipv4_addresses=[],
            additional_ipv6_addresses=["fe80::241", "fe80::242", "fe80::243"],
        ),
        resolved_ip_family=ResolvedIPAddressFamily.IPV6,
        custom_attributes={"attr1": "value1"},
        tags={"tag1": "value1", "tag2": "value2"},
        labels={"label1": "value1", "label2": "value2"},
        macros={
            "$HOSTADDRESS$": "0.0.0.0",
            "$HOSTNAME$": "test_host",
            "HOSTALIAS": "test alias",
            "$HOST_EC_SL$": "30",
        },
    )


@pytest.mark.parametrize(
    (
        "plugins",
        "legacy_plugins",
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
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 arg;1", None)],
            id="legacy plugin string args",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: ["arg0", "arg;1"]},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", None)],
            id="legacy plugin list args",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: SpecialAgentLegacyConfiguration(["arg0"], None)},
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0", None)],
            id="legacy plugin TestSpecialAgentConfiguration",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: SpecialAgentLegacyConfiguration(
                    ["arg0", "arg;1"], None
                )
            },
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", None)],
            id="legacy plugin TestSpecialAgentConfiguration, escaped arg",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: SpecialAgentLegacyConfiguration(
                    ["list0", "list1"], None
                )
            },
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path list0 list1", None)],
            id="legacy plugin TestSpecialAgentConfiguration, arg list",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: SpecialAgentLegacyConfiguration(
                    ["arg0", "arg;1"], "stdin_blob"
                )
            },
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", "stdin_blob")],
            id="legacy plugin with stdin, escaped arg",
        ),
        pytest.param(
            {},
            {
                "test_agent": lambda a, b, c: SpecialAgentLegacyConfiguration(
                    ["list0", "list1"], "stdin_blob"
                )
            },
            {},
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path list0 list1", "stdin_blob")],
            id="legacy plugin with stdin",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: ["-h", "$HOSTNAME$", "-a", "<IP>"]},
            {},
            HOST_CONFIG_WITH_MACROS,
            {},
            [SpecialAgentCommandLine("agent_path -h 'test_host' -a '127.0.0.1'", None)],
            id="legacy plugin with macros",
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
                                command_arguments=["--password", StoredSecret(value="mypassword")],
                            ),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
            HOST_CONFIG,
            {},
            [SpecialAgentCommandLine("agent_path --pwstore=2@0@mypassword --password '***'", None)],
            id="missing stored password",
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
                                command_arguments=["--password", StoredSecret(value="mypassword")],
                            ),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
            HOST_CONFIG,
            {"mypassword": "123456"},
            [
                SpecialAgentCommandLine(
                    "agent_path --pwstore=2@0@mypassword --password '******'", None
                )
            ],
            id="stored password",
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
    legacy_plugins: Mapping[str, InfoFunc],
    host_attrs: Mapping[str, str],
    host_config: HostConfig,
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[SpecialAgentCommandLine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SpecialAgent, "_make_source_path", lambda *_: "agent_path")

    special_agent = SpecialAgent(
        plugins,
        legacy_plugins,
        HostName("test_host"),
        HostAddress("127.0.0.1"),
        host_config,
        host_attrs,
        http_proxies={},
        stored_passwords=stored_passwords,
    )
    commands = list(special_agent.iter_special_agent_commands("test_agent", {}))
    assert commands == expected_result


@pytest.mark.parametrize(
    "plugins, legacy_plugins",
    [
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
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
            {}, {"test_agent": argument_function_with_exception}, id="legacy special agent"
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
    )

    list(special_agent.iter_special_agent_commands("test_agent", {}))

    captured = capsys.readouterr()
    assert (
        captured.out
        == "\nWARNING: Config creation for special agent test_agent failed on test_host: Can't create argument list\n"
    )


@pytest.mark.parametrize(
    "plugins, legacy_plugins",
    [
        pytest.param(
            {
                PluginLocation(
                    "cmk.plugins.test.server_side_calls.test_agent", "special_agent_text"
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
            {}, {"test_agent": argument_function_with_exception}, id="legacy special agent"
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
    )

    local_agent_path = Path(cmk.utils.paths.agents_dir, "special", "agent_test_agent")
    with _with_file(local_agent_path):
        agent_path = special_agent._make_source_path("test_agent")

    assert agent_path == local_agent_path


@pytest.mark.parametrize(
    "args, passwords_from_store, password_store_elements, expected_result",
    [
        pytest.param("args 123 -x 1 -y 2", None, {}, "args 123 -x 1 -y 2", id="string argument"),
        pytest.param(
            ["args", "1; echo", "-x", "1", "-y", "2"],
            None,
            {},
            "args '1; echo' -x 1 -y 2",
            id="list argument",
        ),
        pytest.param(
            ["args", "1 2 3", "-d=2", "--hallo=eins", 9],
            None,
            {},
            "args '1 2 3' -d=2 --hallo=eins 9",
            id="list argument with numbers",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
            {"pw-id": ["abc", "123", "x'äd!?", "aädg"]},
            {},
            "--pwstore=2@11@pw-id arg1 '--password=****' arg3",
            id="passwords_from_store",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id", "--password=%s"), "arg3"],
            None,
            {"pw-id": ["abc", "123", "x'äd!?", "aädg"]},
            "--pwstore=2@11@pw-id arg1 '--password=****' arg3",
            id="password store argument",
        ),
        pytest.param(
            ["arg1", ("store", "pw-id; echo HI;", "--password=%s"), "arg3"],
            None,
            {"pw-id; echo HI;": "the password"},
            "'--pwstore=2@11@pw-id; echo HI;' arg1 '--password=************' arg3",
            id="password store sanitization (CMK-14149)",
        ),
    ],
)
def test_commandline_arguments(
    args: SpecialAgentInfoFunctionResult,
    passwords_from_store: Mapping[str, str] | None,
    password_store_elements: Mapping[str, str],
    expected_result: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(password_store, "load", lambda: password_store_elements)
    cmdline_args = commandline_arguments(
        HostName("test"), "test service", args, passwords_from_store
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
            'The stored password "pw-id" used by host host "test" does not exist (anymore).',
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
        host_name, service_name, ["arg1", ("store", "pw-id", "--password=%s"), "arg3"]
    )
    captured = capsys.readouterr()
    assert expected_warning in captured.out


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(None, id="None argument"),
        pytest.param(1, id="integer argument"),
        pytest.param((1, 2), id="integer tuple"),
    ],
)
def test_commandline_arguments_invalid_arguments_type(args: int | tuple[int, int] | None) -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"The check argument function needs to return either a list of arguments or a string of the concatenated arguments \(Service: test service\).",
    ):
        commandline_arguments(HostName("test"), "test service", args)  # type: ignore[arg-type]


def test_commandline_arguments_invalid_argument() -> None:
    with pytest.raises(
        ActiveCheckError,
        match=r"Invalid argument for command line: \(1, 2\)",
    ):
        commandline_arguments(HostName("test"), "test service", ["arg1", (1, 2), "arg3"])  # type: ignore[list-item]
