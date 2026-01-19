#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Never

import pytest

import cmk.ccc.debug
from cmk.ccc.hostaddress import HostName
from cmk.discover_plugins import PluginLocation
from cmk.fetchers import StoredSecrets
from cmk.password_store.v1_unstable import Secret
from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
)
from cmk.server_side_calls_backend import (
    ActiveCheck,
    ActiveServiceData,
    config_processing,
    NotSupportedError,
)
from cmk.utils import password_store

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


TEST_PLUGIN_STORE = {
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
                    command_arguments=sum(p.items(), ()),
                ),
            ]
        ),
    )
}


def test_get_active_service_data_respects_finalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", False)
    active_check = ActiveCheck(
        TEST_PLUGIN_STORE,
        HostName("myhost"),
        HOST_CONFIG,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=lambda x: x.upper(),
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets={},
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=False,
    )

    (service,) = active_check.get_active_service_data("my_active_check", [{}])
    assert service.description == "MY SERVICE"


def test_get_active_service_data_raises_for_relay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", False)
    active_check = ActiveCheck(
        TEST_PLUGIN_STORE,
        HostName("myhost"),
        HOST_CONFIG,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=str,
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets={},
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=True,
    )

    with pytest.raises(NotSupportedError):
        active_check.get_active_service_data("my_active_check", [{}])


def argument_function_with_exception(*args: object, **kwargs: object) -> Never:
    raise Exception("Can't create argument list")


@pytest.mark.parametrize(
    "active_check_rule, active_check_plugins, hostname, host_config, stored_passwords, expected_result",
    [
        pytest.param(
            ("http", [{"name": "myHTTPName on my_host_alias"}]),
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
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="http",
                    description="HTTP myHTTPName on my_host_alias",
                    command_name="check_mk_active-http",
                    configuration={"name": "myHTTPName on my_host_alias"},
                    command=("/path/to/check_http", "--arg1", "argument1", "--arg2", "argument2"),
                ),
            ],
            id="http_active_service_plugin",
        ),
        pytest.param(
            ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            HOST_CONFIG,
            {},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="First service",
                    command_name="check_mk_active-my_active_check",
                    configuration={"description": "My active check", "param1": "param1"},
                    command=("/path/to/check_my_active_check", "--arg1", "argument1"),
                ),
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="Second service",
                    command_name="check_mk_active-my_active_check",
                    configuration={"description": "My active check", "param1": "param1"},
                    command=("/path/to/check_my_active_check", "--arg2", "argument2"),
                ),
            ],
            id="multiple_services",
        ),
        pytest.param(
            ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            {},
            HostName("myhost"),
            HOST_CONFIG,
            {},
            [],
            id="unimplemented_check_plugin",
        ),
        pytest.param(
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
            HOST_CONFIG,
            {"stored_password": Secret("mypassword")},
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="My service",
                    command_name="check_mk_active-my_active_check",
                    configuration={
                        "description": "My active check",
                        "password": (
                            "cmk_postprocessed",
                            "stored_password",
                            ("stored_password", ""),
                        ),
                    },
                    command=(
                        "/path/to/check_my_active_check",
                        "--pwstore=1@9@/pw/store@stored_password",
                        "'--secret=**********'",
                    ),
                ),
            ],
            id="one_service_password_store",
        ),
    ],
)
def test_get_active_service_data(
    monkeypatch: pytest.MonkeyPatch,
    active_check_rule: tuple[str, Sequence[Mapping[str, object]]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    host_config: HostConfig,
    stored_passwords: Mapping[str, Secret[str]],
    expected_result: Sequence[ActiveServiceData],
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", True)
    active_check = ActiveCheck(
        active_check_plugins,
        hostname,
        host_config,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=lambda x: x,
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets=stored_passwords,
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=False,
    )

    services = active_check.get_active_service_data(*active_check_rule)
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
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "test_check", True)
    active_check = ActiveCheck(
        plugins=_PASSWORD_TEST_ACTIVE_CHECKS,
        host_name=HostName("myhost"),
        host_config=HOST_CONFIG,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=lambda x: x,
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets={"uuid1234": Secret("p4ssw0rd!")},
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=False,
    )

    assert active_check.get_active_service_data(
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
    ) == [
        ActiveServiceData(
            plugin_name="test_check",
            description="My service",
            command_name="check_mk_active-test_check",
            configuration={
                "description": "My active check",
                "password": ("cmk_postprocessed", "explicit_password", ("uuid1234", "p4ssw0rd!")),
            },
            command=(
                "/path/to/check_test_check",
                "--pwstore=4@1@/pw/store@uuid1234",
                "--password-id",
                "uuid1234:/pw/store",
                "--password-plain-in-curly",
                "'{*********}'",
            ),
        ),
    ]


def test_get_active_service_data_password_without_hack() -> None:
    active_check = ActiveCheck(
        plugins=_PASSWORD_TEST_ACTIVE_CHECKS,
        host_name=HostName("myhost"),
        host_config=HOST_CONFIG,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=lambda x: x,
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets={"uuid1234": Secret("p4ssw0rd!")},
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=False,
    )

    assert active_check.get_active_service_data(
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
    ) == [
        ActiveServiceData(
            plugin_name="test_check",
            description="My service",
            command_name="check_mk_active-test_check",
            configuration={
                "description": "My active check",
                "password": ("cmk_postprocessed", "explicit_password", ("uuid1234", "p4ssw0rd!")),
            },
            command=(
                "/path/to/check_test_check",
                "--password-id",
                "uuid1234:/pw/store",
                "--password-plain-in-curly",
                "'{p4ssw0rd!}'",
            ),
        ),
    ]


@pytest.mark.parametrize(
    "active_check_rule, active_check_plugins",
    [
        pytest.param(
            ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
    ],
)
def test_test_get_active_service_data_crash_with_debug(
    active_check_rule: tuple[str, Sequence[Mapping[str, object]]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.ccc.debug,
        "enabled",
        lambda: True,
    )

    active_check = ActiveCheck(
        active_check_plugins,
        HostName("test_host"),
        HOST_CONFIG,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=lambda x: x,
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets={},
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=False,
    )

    with pytest.raises(
        Exception,
        match="Can't create argument list",
    ):
        active_check.get_active_service_data(*active_check_rule)


@pytest.mark.parametrize(
    "active_check_rule, active_check_plugins, hostname, expected_result, expected_warning",
    [
        pytest.param(
            ("my_active_check", [{}]),
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
                                service_description="",
                                command_arguments=["--conf", "conf"],
                            ),
                        ]
                    ),
                )
            },
            HostName("myhost"),
            [],
            "\nWARNING: Skipping invalid service with empty description (active check: my_active_check) on host myhost\n",
            id="empty_description",
        ),
        pytest.param(
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
            [
                ActiveServiceData(
                    plugin_name="my_active_check",
                    description="My service",
                    command_name="check_mk_active-my_active_check",
                    configuration={
                        "description": "My active check",
                        "password": (
                            "cmk_postprocessed",
                            "stored_password",
                            ("stored_password", ""),
                        ),
                    },
                    command=(
                        "/path/to/check_my_active_check",
                        "--pwstore=2@0@/pw/store@stored_password",
                        "--password",
                        "'***'",
                    ),
                ),
            ],
            '\nWARNING: The stored password "stored_password" used by host "myhost" does not exist (anymore).\n',
            id="stored_password_missing",
        ),
    ],
)
def test_get_active_service_data_warnings(
    monkeypatch: pytest.MonkeyPatch,
    active_check_rule: tuple[str, Sequence[Mapping[str, object]]],
    active_check_plugins: Mapping[PluginLocation, ActiveCheckConfig],
    hostname: HostName,
    expected_result: Sequence[ActiveServiceData],
    expected_warning: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(password_store.hack.HACK_CHECKS, "my_active_check", True)
    active_check_config = ActiveCheck(
        active_check_plugins,
        hostname,
        HOST_CONFIG,
        global_proxies_with_lookup=config_processing.GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda _name: None
        ),
        oauth2_connections={},
        service_name_finalizer=lambda x: x,
        secrets_config=StoredSecrets(
            path=Path("/pw/store"),
            secrets={},
        ),
        finder=lambda executable, module: f"/path/to/{executable}",
        ip_lookup_failed=False,
        for_relay=False,
    )

    services = active_check_config.get_active_service_data(*active_check_rule)
    assert services == expected_result

    captured = capsys.readouterr()
    assert captured.err == expected_warning
