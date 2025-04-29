#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib.base import Scenario

import cmk.utils.debug
import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostAddress

from cmk.automations import results as automation_results
from cmk.automations.results import DiagHostResult

from cmk.fetchers import PiggybackFetcher

import cmk.base.automations.check_mk as check_mk
import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import ConfigCache


class TestAutomationDiagHost:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def ipaddress(self):
        return "1.2.3.4"

    @pytest.fixture
    def raw_data(self):
        return "<<<check_mk>>>\nraw data"

    @pytest.fixture
    def scenario(self, hostname, ipaddress, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("ipaddresses", {hostname: ipaddress})
        ts.apply(monkeypatch)
        return ts

    @pytest.fixture
    def patch_fetch(self, raw_data, monkeypatch):
        monkeypatch.setattr(
            check_mk,
            "get_raw_data",
            lambda _file_cache, fetcher, _mode: (
                result.OK(b"") if isinstance(fetcher, PiggybackFetcher) else result.OK(raw_data)
            ),
        )

    @pytest.mark.usefixtures("scenario")
    @pytest.mark.usefixtures("patch_fetch")
    def test_execute(self, hostname: str, ipaddress: str, raw_data: str) -> None:
        args = [hostname, "agent", ipaddress, "", "6557", "10", "5", "5", ""]
        assert check_mk.AutomationDiagHost().execute(args) == DiagHostResult(
            0,
            raw_data,
        )


def mock_argument_function(params: Mapping[str, str]) -> str:
    return "--arg1 arument1 --host_alias $HOSTALIAS$"


def mock_service_description(params: Mapping[str, str]) -> str:
    return "Active check of $HOSTNAME$"


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, service_attrs, active_check_args, expected_result",
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
                    "argument_function": mock_argument_function,
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {},
            ["my_host", "my_active_check", "Active check of my_host"],
            automation_results.ActiveCheckResult(
                state=0, output="--arg1 arument1 --host_alias my_host_alias"
            ),
            id="active_check",
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
                    "argument_function": mock_argument_function,
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {},
            ["my_host", "my_active_check", "Some other item"],
            automation_results.ActiveCheckResult(
                state=None, output="Failed to compute check result"
            ),
            id="no_active_check",
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
                    "argument_function": lambda _: [
                        "-n",  # relevant for quoting -- echo should eat this
                        "--arg1",
                        "arument1",
                        "--host_alias",
                        "$HOSTALIAS$",
                    ],
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {},
            ["my_host", "my_active_check", "Active check of my_host"],
            automation_results.ActiveCheckResult(
                state=0, output="--arg1 arument1 --host_alias my_host_alias"
            ),
            id="arguments_list",
        ),
        pytest.param(
            [
                (
                    "http",
                    [
                        {
                            "description": "My http check",
                            "param1": "param1",
                            "name": "my special HTTP",
                        }
                    ],
                ),
            ],
            {
                "http": {
                    "command_line": "echo $ARG1$",
                    "argument_function": mock_argument_function,
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {},
            ["my_host", "http", "HTTP my special HTTP"],
            automation_results.ActiveCheckResult(
                state=0, output="--arg1 arument1 --host_alias my_host_alias"
            ),
            id="arguments_list",
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
                    "argument_function": lambda _: ["echo", "$_SERVICEFOO$"],
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {"_FOO": "BAR"},
            ["my_host", "my_active_check", "Active check of my_host"],
            automation_results.ActiveCheckResult(state=0, output="echo BAR"),
            id="custom_service_attribute",
        ),
    ],
)
def test_automation_active_check(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Mapping[str, str],
    service_attrs: Mapping[str, str],
    active_check_args: list[str],
    expected_result: automation_results.ActiveCheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "active_check_info", active_check_info)
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *_: host_attrs)
    monkeypatch.setattr(core_config, "get_service_attributes", lambda *_: service_attrs)
    monkeypatch.setattr(config, "get_resource_macros", lambda *_: {})

    config_cache = config.reset_config_cache()
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    active_check = check_mk.AutomationActiveCheck()
    assert active_check.execute(active_check_args) == expected_result


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, active_check_args, error_message",
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
                    "argument_function": lambda _: None,
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            ["my_host", "my_active_check", "Active check of my_host"],
            "\nWARNING: Config creation for active check my_active_check failed on my_host: "
            "The check argument function needs to return either a list of arguments or a string of "
            "the concatenated arguments (Service: Active check of my_host).\n",
            id="invalid_args",
        ),
    ],
)
def test_automation_active_check_invalid_args(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Mapping[str, str],
    active_check_args: list[str],
    error_message: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(config, "active_check_info", active_check_info)
    monkeypatch.setattr(config, "ip_address_of", lambda *args: HostAddress("127.0.0.1"))
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *_: host_attrs)
    monkeypatch.setattr(config, "get_resource_macros", lambda *_: {})

    config_cache = config.reset_config_cache()
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: False,
    )

    active_check = check_mk.AutomationActiveCheck()
    active_check.execute(active_check_args)

    assert capsys.readouterr().err == error_message
