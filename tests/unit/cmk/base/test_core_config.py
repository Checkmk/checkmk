#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

import pytest

from tests.testlib.base import Scenario

import cmk.utils.config_path
import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils import password_store
from cmk.utils.config_path import ConfigPath, LATEST_CONFIG
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.nagios_utils
from cmk.base.check_utils import ConfiguredService
from cmk.base.core_factory import create_core


@pytest.fixture(name="config_path")
def fixture_config_path():
    ConfigPath.ROOT.mkdir(parents=True, exist_ok=True)
    try:
        yield ConfigPath.ROOT
    finally:
        shutil.rmtree(ConfigPath.ROOT)


def test_do_create_config_nagios(core_scenario, config_path) -> None:
    core_config.do_create_config(create_core("nagios"))

    assert Path(cmk.utils.paths.nagios_objects_file).exists()
    assert config.PackedConfigStore.from_serial(LATEST_CONFIG).path.exists()


def test_active_check_arguments_basics() -> None:
    assert (
        core_config.active_check_arguments(HostName("bla"), "blub", "args 123 -x 1 -y 2")
        == "args 123 -x 1 -y 2"
    )

    assert (
        core_config.active_check_arguments(
            HostName("bla"), "blub", ["args", "123", "-x", "1", "-y", "2"]
        )
        == "'args' '123' '-x' '1' '-y' '2'"
    )

    assert (
        core_config.active_check_arguments(
            HostName("bla"), "blub", ["args", "1 2 3", "-d=2", "--hallo=eins", 9]
        )
        == "'args' '1 2 3' '-d=2' '--hallo=eins' 9"
    )

    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", (1, 2))  # type: ignore[arg-type]


@pytest.mark.parametrize("pw", ["abc", "123", "x'äd!?", "aädg"])
def test_active_check_arguments_password_store(pw) -> None:
    password_store.save({"pw-id": pw})
    assert core_config.active_check_arguments(
        HostName("bla"), "blub", ["arg1", ("store", "pw-id", "--password=%s"), "arg3"]
    ) == "--pwstore=2@11@pw-id 'arg1' '--password=%s' 'arg3'" % ("*" * len(pw))


def test_active_check_arguments_not_existing_password(capsys) -> None:
    assert (
        core_config.active_check_arguments(
            HostName("bla"), "blub", ["arg1", ("store", "pw-id", "--password=%s"), "arg3"]
        )
        == "--pwstore=2@11@pw-id 'arg1' '--password=***' 'arg3'"
    )
    stderr = capsys.readouterr().err
    assert 'The stored password "pw-id" used by service "blub" on host "bla"' in stderr


def test_active_check_arguments_wrong_types() -> None:
    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments(HostName("bla"), "blub", 1)  # type: ignore[arg-type]

    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments(
            HostName("bla"), "blub", (1, 2)  # type: ignore[arg-type]
        )


def test_active_check_arguments_str() -> None:
    assert (
        core_config.active_check_arguments(HostName("bla"), "blub", "args 123 -x 1 -y 2")
        == "args 123 -x 1 -y 2"
    )


def test_active_check_arguments_list() -> None:
    assert core_config.active_check_arguments(HostName("bla"), "blub", ["a", "123"]) == "'a' '123'"


def test_active_check_arguments_list_with_numbers() -> None:
    assert core_config.active_check_arguments(HostName("bla"), "blub", [1, 1.2]) == "1 1.2"


def test_active_check_arguments_list_with_pwstore_reference() -> None:
    assert (
        core_config.active_check_arguments(
            HostName("bla"), "blub", ["a", ("store", "pw1", "--password=%s")]
        )
        == "--pwstore=2@11@pw1 'a' '--password=***'"
    )


def test_active_check_arguments_list_with_invalid_type() -> None:
    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments(
            HostName("bla"), "blub", [None]  # type: ignore[list-item]
        )


def test_get_host_attributes(fixup_ip_lookup, monkeypatch) -> None:
    ts = Scenario()
    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.set_option(
        "host_labels",
        {
            "test-host": {
                "ding": "dong",
            },
        },
    )
    config_cache = ts.apply(monkeypatch)

    expected_attrs = {
        "_ADDRESSES_4": "",
        "_ADDRESSES_6": "",
        "_ADDRESS_4": "0.0.0.0",
        "_ADDRESS_6": "",
        "_ADDRESS_FAMILY": "4",
        "_FILENAME": "/wato/hosts.mk",
        "_TAGS": "/wato/ auto-piggyback ip-v4 ip-v4-only lan no-agent no-snmp prod site:unit",
        "__TAG_address_family": "ip-v4-only",
        "__TAG_agent": "no-agent",
        "__TAG_criticality": "prod",
        "__TAG_ip-v4": "ip-v4",
        "__TAG_networking": "lan",
        "__TAG_piggyback": "auto-piggyback",
        "__TAG_site": "unit",
        "__TAG_snmp_ds": "no-snmp",
        "__LABEL_ding": "dong",
        "__LABEL_cmk/site": "NO_SITE",
        "__LABELSOURCE_cmk/site": "discovered",
        "__LABELSOURCE_ding": "explicit",
        "address": "0.0.0.0",
        "alias": "test-host",
    }

    if cmk_version.is_managed_edition():
        expected_attrs["_CUSTOMER"] = "provider"

    attrs = core_config.get_host_attributes("test-host", config_cache)
    assert attrs == expected_attrs


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname,result",
    [
        (
            "localhost",
            {
                "check_interval": 1.0,
                "contact_groups": "ding",
            },
        ),
        ("blub", {"check_interval": 40.0}),
    ],
)
def test_get_cmk_passive_service_attributes(monkeypatch, hostname, result) -> None:
    ts = Scenario()
    ts.add_host("localhost")
    ts.add_host("blub")
    ts.set_option(
        "extra_service_conf",
        {
            "contact_groups": [
                ("ding", ["localhost"], ["CPU load$"]),
            ],
            "check_interval": [
                (40.0, ["blub"], ["Check_MK$"]),
                (33.0, ["localhost"], ["CPU load$"]),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config(hostname)
    check_mk_attrs = core_config.get_service_attributes(hostname, "Check_MK", config_cache)

    service = ConfiguredService(
        check_plugin_name=CheckPluginName("cpu_loads"),
        item=None,
        description="CPU load",
        parameters=TimespecificParameters(),
        discovered_parameters={},
        service_labels={},
    )
    service_spec = core_config.get_cmk_passive_service_attributes(
        config_cache, host_config, service, check_mk_attrs
    )
    assert service_spec == result


@pytest.mark.parametrize(
    "tag_groups,result",
    [
        (
            {
                "tg1": "val1",
                "tg2": "val1",
            },
            {
                "__TAG_tg1": "val1",
                "__TAG_tg2": "val1",
            },
        ),
        (
            {"täg-113232_eybc": "äbcdef"},
            {
                "__TAG_täg-113232_eybc": "äbcdef",
            },
        ),
        (
            {"a.d B/E u-f N_A": "a.d B/E u-f N_A"},
            {
                "__TAG_a.d B/E u-f N_A": "a.d B/E u-f N_A",
            },
        ),
    ],
)
def test_get_tag_attributes(tag_groups, result) -> None:
    attributes = core_config._get_tag_attributes(tag_groups, "TAG")
    assert attributes == result
    for k, v in attributes.items():
        assert isinstance(k, str)
        assert isinstance(v, str)


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
            core_config.HostAddressConfiguration(
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
def test_get_host_config(
    hostname: str,
    host_attrs: config.ObjectAttributes,
    expected_result: core_config.HostAddressConfiguration,
):
    host_config = core_config._get_host_address_config(hostname, host_attrs)
    assert host_config == expected_result


@pytest.mark.parametrize(
    "check_name, active_check_info, hostname, host_attrs, expected_result",
    [
        pytest.param(
            "my_active_check",
            {
                "my_active_check": {
                    "command_line": "echo $ARG1$",
                    "argument_function": lambda _: "--arg1 arument1 --host_alias $HOSTALIAS$",
                    "service_description": lambda _: "Active check of $HOSTNAME$",
                }
            },
            "myhost",
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            [("Active check of myhost", "--arg1 arument1 --host_alias $HOSTALIAS$")],
            id="one_active_service",
        ),
        pytest.param(
            "my_active_check",
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
            "myhost",
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            [("First service", "--arg1 argument1"), ("Second service", "--arg2 argument2")],
            id="multiple_active_services",
        ),
    ],
)
def test_iter_active_check_services(
    check_name: str,
    active_check_info: Mapping[str, Mapping[str, str]],
    hostname: str,
    host_attrs: dict[str, Any],
    expected_result: Sequence[Tuple[str, str]],
    monkeypatch,
):
    monkeypatch.setattr(config, "active_check_info", active_check_info)
    monkeypatch.setattr(core_config, "get_host_attributes", lambda e, s: host_attrs)

    cache = config.get_config_cache()
    cache.initialize()

    active_info = active_check_info[check_name]
    services = list(
        core_config.iter_active_check_services(check_name, active_info, hostname, host_attrs, {})
    )
    assert services == expected_result
