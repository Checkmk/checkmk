#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.utils.hostaddress import HostName

import cmk.base.command_config as command_config
import cmk.base.config as base_config
from cmk.base.command_config import (
    _get_host_address_config,
    ActiveCheckConfig,
    ActiveServiceData,
    ActiveServiceDescription,
    HostAddressConfiguration,
)

from cmk.commands.v1 import ActiveCheckCommand, ActiveService, Secret, SecretType


@pytest.mark.parametrize(
    "active_checks, active_check_info, active_check_command, hostname, host_attrs, macros, stored_passwords, expected_result",
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            None,
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            None,
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            ActiveCheckCommand(
                name="my_active_check",
                parameter_parser=lambda p: p,
                service_function=lambda *_: (
                    [
                        ActiveService("First service", ["--arg1", "argument1"]),
                        ActiveService("Second service", ["--arg2", "argument2"]),
                    ]
                ),
            ),
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
            None,
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
            ActiveCheckCommand(
                name="my_active_check",
                parameter_parser=lambda p: p,
                service_function=lambda *_: (
                    [
                        ActiveService(
                            "My service", ["--password", Secret(SecretType.PASSWORD, "mypassword")]
                        ),
                    ]
                ),
            ),
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
            ActiveCheckCommand(
                name="my_active_check",
                parameter_parser=lambda p: p,
                service_function=lambda *_: (
                    [
                        ActiveService(
                            "My service",
                            ["--password", Secret(SecretType.STORE, "stored_password")],
                        ),
                    ]
                ),
            ),
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
    active_checks: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    active_check_command: ActiveCheckCommand,
    hostname: HostName,
    host_attrs: Mapping[str, str],
    macros: Mapping[str, str],
    stored_passwords: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_config, "active_check_info", active_check_info)
    monkeypatch.setattr(command_config, "get_active_check", lambda p: active_check_command)
    monkeypatch.setattr(base_config.ConfigCache, "get_host_attributes", lambda e, s: host_attrs)

    active_check_config = ActiveCheckConfig(
        hostname, host_attrs, translations={}, macros=macros, stored_passwords=stored_passwords
    )

    services = list(active_check_config.get_active_service_data(active_checks))
    assert services == expected_result


@pytest.mark.parametrize(
    "active_checks, active_check_info, active_check_command, hostname, host_attrs, expected_result, expected_warning",
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            [],
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plugin is missing an argument function or a service description\n",
            id="invalid_plugin_info",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {},
            ActiveCheckCommand(
                name="my_active_check",
                parameter_parser=lambda p: p,
                service_function=lambda *_: (
                    [
                        ActiveService(
                            "My service",
                            ["--password", Secret(SecretType.STORE, "stored_password")],
                        ),
                    ]
                ),
            ),
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
    active_checks: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    active_check_command: ActiveCheckCommand,
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceData],
    expected_warning: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(base_config, "active_check_info", active_check_info)
    monkeypatch.setattr(command_config, "get_active_check", lambda p: active_check_command)
    monkeypatch.setattr(base_config.ConfigCache, "get_host_attributes", lambda e, s: host_attrs)

    active_check_config = ActiveCheckConfig(hostname, host_attrs, translations={})

    services = list(active_check_config.get_active_service_data(active_checks))
    assert services == expected_result

    captured = capsys.readouterr()
    assert captured.out == expected_warning


@pytest.mark.parametrize(
    "active_checks, active_check_info, active_check_command, hostname, host_attrs, expected_result",
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            None,
            HostName("myhost"),
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
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
            ActiveCheckCommand(
                name="my_active_check",
                parameter_parser=lambda p: p,
                service_function=lambda *_: (
                    [
                        ActiveService(
                            "My service", ["--password", Secret(SecretType.PASSWORD, "mypassword")]
                        ),
                    ]
                ),
            ),
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
                    plugin_name="check_my_active_check",
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
            None,
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
    active_checks: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    active_check_command: ActiveCheckCommand,
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceDescription],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_config, "active_check_info", active_check_info)
    monkeypatch.setattr(command_config, "get_active_check", lambda p: active_check_command)
    monkeypatch.setattr(base_config.ConfigCache, "get_host_attributes", lambda e, s: host_attrs)

    active_check_config = ActiveCheckConfig(hostname, host_attrs, translations={})

    descriptions = list(active_check_config.get_active_service_descriptions(active_checks))
    assert descriptions == expected_result


@pytest.mark.parametrize(
    "active_checks, active_check_info, hostname, host_attrs, expected_result, expected_warning",
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
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            [],
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plugin is missing an argument function or a service description\n",
            id="invalid_plugin_info",
        ),
    ],
)
def test_get_active_service_descriptions_warnings(
    active_checks: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    hostname: HostName,
    host_attrs: Mapping[str, str],
    expected_result: Sequence[ActiveServiceDescription],
    expected_warning: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(base_config, "active_check_info", active_check_info)
    monkeypatch.setattr(base_config.ConfigCache, "get_host_attributes", lambda e, s: host_attrs)

    active_check_config = ActiveCheckConfig(hostname, host_attrs, translations={})

    descriptions = list(active_check_config.get_active_service_descriptions(active_checks))
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
