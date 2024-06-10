#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access


from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.utils import password_store
from cmk.utils.hostaddress import HostName

from cmk.base.server_side_calls import ActiveCheck, ActiveServiceData
from cmk.base.server_side_calls._active_checks import (
    _get_host_address_config,
    ActiveServiceDescription,
    HostAddressConfiguration,
)

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
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
                    detected_executable="echo",
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
                    detected_executable="echo",
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
                    detected_executable="echo",
                ),
            ],
            id="macros_replaced_legacy_plugin",
        ),
        pytest.param(
            [
                ("http", [{"name": "myHTTPName on my_host_alias"}]),
            ],
            {},
            {
                PluginLocation(f"{__name__}", "httpv1"): ActiveCheckConfig(
                    name="http",
                    parameter_parser=lambda p: p,
                    commands_function=lambda *_: (
                        [
                            ActiveCheckCommand(
                                service_description="HTTP myHTTPName on my_host_alias",
                                command_arguments=[
                                    "--arg1",
                                    "argument1",
                                    "--arg2",
                                    "argument2",
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
                    plugin_name="http",
                    description="HTTP myHTTPName on my_host_alias",
                    command="check_mk_active-http",
                    command_display="check_mk_active-http!--arg1 argument1 --arg2 argument2",
                    command_line="check_http --arg1 argument1 --arg2 argument2",
                    params={"name": "myHTTPName on my_host_alias"},
                    expanded_args="--arg1 argument1 --arg2 argument2",
                    detected_executable="check_http",
                ),
            ],
            id="http_active_service_plugin",
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
                    detected_executable="echo",
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
                "password": ("cmk_postprocessed", "explicit_password", ("uuid1234", "p4ssw0rd!")),
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
                "password": ("cmk_postprocessed", "explicit_password", ("uuid1234", "p4ssw0rd!")),
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
        password_store_file=Path("/pw/store"),
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
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plug-in is missing an argument function or a service name\n",
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
                    expanded_args="--pwstore=2@0@/pw/store@stored_password --password " "'***'",
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
            "\nWARNING: Invalid configuration (active check: my_active_check) on host myhost: active check plug-in is missing an argument function or a service name\n",
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
    host_attrs: Mapping[str, str],
    expected_result: HostAddressConfiguration,
) -> None:
    host_config = _get_host_address_config(hostname, host_attrs)
    assert host_config == expected_result
