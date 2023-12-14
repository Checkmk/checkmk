#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest

import cmk.utils.paths
from cmk.utils import password_store
from cmk.utils.hostaddress import HostAddress, HostName

import cmk.base.config as base_config
from cmk.base.server_side_calls import (
    _get_host_address_config,
    _get_host_config,
    ActiveCheck,
    ActiveCheckError,
    ActiveServiceData,
    ActiveServiceDescription,
    commandline_arguments,
    HostAddressConfiguration,
    InfoFunc,
    SpecialAgent,
    SpecialAgentCommandLine,
    SpecialAgentInfoFunctionResult,
)

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    PlainTextSecret,
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


class TestSpecialAgentLegacyConfiguration(NamedTuple):
    args: Sequence[str]
    stdin: str | None


def argument_function_with_exception(*args, **kwargs):
    raise Exception("Can't create argument list")


@pytest.mark.parametrize(
    "active_check_rules, legacy_active_check_plugins, active_check_plugins, hostname, host_attrs, macros, stored_passwords, expected_result",
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
            {},
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
            {},
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
            {"$HOSTALIAS$": "myalias"},
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
            {},
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
            {},
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
            {},
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
                "my_active_check": ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand("First service", ["--arg1", "argument1"]),
                            ActiveCheckCommand("Second service", ["--arg2", "argument2"]),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            HOST_ATTRS,
            {},
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
            {},
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
                "my_active_check": ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand(
                                "My service",
                                ["--password", PlainTextSecret("mypassword")],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            HOST_ATTRS,
            {},
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
                "my_active_check": ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand(
                                "My service",
                                ["--password", StoredSecret("stored_password")],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            HOST_ATTRS,
            {},
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
    active_check_plugins: Mapping[str, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    macros: Mapping[str, str],
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
) -> None:
    active_check = ActiveCheck(
        active_check_plugins,
        legacy_active_check_plugins,
        hostname,
        host_attrs,
        translations={},
        macros=macros,
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
                "my_active_check": ActiveCheckConfig(
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
    active_check_plugins: Mapping[str, ActiveCheckConfig],
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
        HOST_ATTRS,
        translations={},
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
                "my_active_check": ActiveCheckConfig(
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
    active_check_plugins: Mapping[str, ActiveCheckConfig],
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
        HOST_ATTRS,
        translations={},
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
                "my_active_check": ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand(
                                "My service",
                                ["--password", StoredSecret("stored_password")],
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
    active_check_plugins: Mapping[str, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    active_check_config = ActiveCheck(
        active_check_plugins, legacy_active_check_plugins, hostname, host_attrs, translations={}
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
                "my_active_check": ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand(
                                "My service",
                                ["--password", StoredSecret("mypassword")],
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
    active_check_plugins: Mapping[str, ActiveCheckConfig],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceDescription],
) -> None:
    active_check_config = ActiveCheck(
        active_check_plugins, legacy_active_check_plugins, hostname, host_attrs, translations={}
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
        {}, legacy_active_check_plugins, hostname, host_attrs, translations={}
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


@pytest.mark.parametrize(
    "hostname, host_attrs, expected_result",
    [
        pytest.param(
            "myhost",
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "_ADDRESSES_4": "127.0.0.2 127.0.0.3",
                "_ADDRESSES_4_1": "127.0.0.2",
                "_ADDRESSES_4_2": "127.0.0.3",
                "_ADDRESSES_6": "",
            },
            HostConfig(
                name="myhost",
                address="127.0.0.1",
                alias="my_host_alias",
                ip_family=IPAddressFamily.IPV4,
                ipv4address="127.0.0.1",
                ipv6address=None,
                additional_ipv4addresses=["127.0.0.2", "127.0.0.3"],
                additional_ipv6addresses=[],
            ),
            id="ipv4 address",
        ),
        pytest.param(
            "myhost",
            {
                "alias": "my_host_alias",
                "_ADDRESS_6": "fe80::240",
                "address": "fe80::240",
                "_ADDRESS_FAMILY": "6",
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "fe80::241 fe80::242",
            },
            HostConfig(
                name="myhost",
                address="fe80::240",
                alias="my_host_alias",
                ip_family=IPAddressFamily.IPV6,
                ipv4address=None,
                ipv6address="fe80::240",
                additional_ipv4addresses=[],
                additional_ipv6addresses=["fe80::241", "fe80::242"],
            ),
            id="ipv6 address",
        ),
        pytest.param(
            "myhost",
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "",
                "address": "",
                "_ADDRESS_FAMILY": "4",
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
            },
            HostConfig(
                name="myhost",
                address=None,
                alias="my_host_alias",
                ip_family=IPAddressFamily.IPV4,
                ipv4address=None,
                ipv6address=None,
                additional_ipv4addresses=[],
                additional_ipv6addresses=[],
            ),
            id="no address",
        ),
    ],
)
def test_get_host_config(
    hostname: str,
    host_attrs: base_config.ObjectAttributes,
    expected_result: HostConfig,
) -> None:
    host_config = _get_host_config(hostname, host_attrs)
    assert host_config == expected_result


@pytest.mark.parametrize(
    ("plugins", "legacy_plugins", "host_attrs", "stored_passwords", "expected_result"),
    [
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: "arg0 arg;1"},
            {},
            {},
            [SpecialAgentCommandLine("agent_path arg0 arg;1", None)],
            id="legacy plugin string args",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: ["arg0", "arg;1"]},
            {},
            {},
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", None)],
            id="legacy plugin list args",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: TestSpecialAgentLegacyConfiguration(["arg0"], None)},
            {},
            {},
            [SpecialAgentCommandLine("agent_path arg0", None)],
            id="legacy plugin TestSpecialAgentConfiguration",
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
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", None)],
            id="legacy plugin TestSpecialAgentConfiguration, escaped arg",
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
            [SpecialAgentCommandLine("agent_path list0 list1", None)],
            id="legacy plugin TestSpecialAgentConfiguration, arg list",
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
            [SpecialAgentCommandLine("agent_path arg0 'arg;1'", "stdin_blob")],
            id="legacy plugin with stdin, escaped arg",
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
            [SpecialAgentCommandLine("agent_path list0 list1", "stdin_blob")],
            id="legacy plugin with stdin",
        ),
        pytest.param(
            {},
            {"test_agent": lambda a, b, c: ["-h", "$HOSTNAME$", "-a", "<IP>"]},
            {},
            {},
            [SpecialAgentCommandLine("agent_path -h 'test_host' -a '127.0.0.1'", None)],
            id="legacy plugin with macros",
        ),
        pytest.param(
            {
                "test_agent": SpecialAgentConfig(
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
            {},
            [SpecialAgentCommandLine("agent_path arg1 'arg2;1'", None)],
            id="one command, escaped arg",
        ),
        pytest.param(
            {
                "test_agent": SpecialAgentConfig(
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
            {},
            [
                SpecialAgentCommandLine("agent_path arg1 'arg2;1'", None),
                SpecialAgentCommandLine("agent_path arg3 arg4", None),
            ],
            id="multiple commands",
        ),
        pytest.param(
            {
                "test_agent": SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=lambda *_: (
                        [
                            SpecialAgentCommand(
                                command_arguments=["--password", StoredSecret("mypassword")],
                            ),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
            {},
            [SpecialAgentCommandLine("agent_path --pwstore=2@0@mypassword --password '***'", None)],
            id="missing stored password",
        ),
        pytest.param(
            {
                "test_agent": SpecialAgentConfig(
                    name="test_agent",
                    parameter_parser=lambda e: e,
                    commands_function=lambda *_: (
                        [
                            SpecialAgentCommand(
                                command_arguments=["--password", StoredSecret("mypassword")],
                            ),
                        ]
                    ),
                )
            },
            {},
            HOST_ATTRS,
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
                "test_agent": SpecialAgentConfig(
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
            {"mypassword": "123456"},
            [SpecialAgentCommandLine("agent_path -h '<HOST>' -a '$HOSTADDRESS$'", None)],
            id="command with macros",
        ),
    ],
)
def test_iter_special_agent_commands(
    plugins: Mapping[str, SpecialAgentConfig],
    legacy_plugins: Mapping[str, InfoFunc],
    host_attrs: Mapping[str, str],
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
        host_attrs,
        stored_passwords,
        {"$HOSTNAME$": "test_host", "$HOSTADDRESS$": "0.0.0.0", "HOSTALIAS": "test alias"},
    )
    commands = list(special_agent.iter_special_agent_commands("test_agent", {}))
    assert commands == expected_result


@pytest.mark.parametrize(
    "plugins, legacy_plugins",
    [
        pytest.param(
            {
                "test_agent": SpecialAgentConfig(
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
    plugins: Mapping[str, SpecialAgentConfig],
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
        plugins, legacy_plugins, HostName("test_host"), HostAddress("127.0.0.1"), HOST_ATTRS, {}, {}
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
                "test_agent": SpecialAgentConfig(
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
    plugins: Mapping[str, SpecialAgentConfig],
    legacy_plugins: Mapping[str, InfoFunc],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    special_agent = SpecialAgent(
        plugins, legacy_plugins, HostName("test_host"), HostAddress("127.0.0.1"), HOST_ATTRS, {}, {}
    )

    with pytest.raises(
        Exception,
        match="Can't create argument list",
    ):
        list(special_agent.iter_special_agent_commands("test_agent", {}))


def test_make_source_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cmk.utils.paths, "agents_dir", tmp_path)

    special_agent = SpecialAgent(
        {}, {}, HostName("test_host"), HostAddress("127.0.0.1"), {}, {}, {}
    )
    agent_path = special_agent._make_source_path("test_agent")

    assert agent_path == tmp_path / "special" / "agent_test_agent"


def test_make_source_path_local_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cmk.utils.paths, "local_agents_dir", tmp_path)

    (tmp_path / "special").mkdir(exist_ok=True)
    local_agent_path = tmp_path / "special" / "agent_test_agent"
    local_agent_path.touch()

    special_agent = SpecialAgent(
        {}, {}, HostName("test_host"), HostAddress("127.0.0.1"), {}, {}, {}
    )
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
