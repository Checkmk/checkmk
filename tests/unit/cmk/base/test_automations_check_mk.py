#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib.base import Scenario

import cmk.utils.exceptions as exceptions
from cmk.utils.type_defs import result

from cmk.automations import results as automation_results
from cmk.automations.results import DiagHostResult

from cmk.fetchers import PiggybackFetcher

import cmk.base.automations.check_mk as check_mk
import cmk.base.config as config
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
    def test_execute(self, hostname, ipaddress, raw_data) -> None:  # type:ignore[no-untyped-def]
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
    "active_checks, active_check_info, host_attrs, active_check_args, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            ["my_host", "my_active_check", "Active check of my_host"],
            automation_results.ActiveCheckResult(
                state=0, output="--arg1 arument1 --host_alias my_host_alias"
            ),
            id="active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            ["my_host", "my_active_check", "Some other item"],
            automation_results.ActiveCheckResult(
                state=None, output="Failed to compute check result"
            ),
            id="no_active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            ["my_host", "http", "HTTP my special HTTP"],
            automation_results.ActiveCheckResult(
                state=0, output="--arg1 arument1 --host_alias my_host_alias"
            ),
            id="arguments_list",
        ),
    ],
)
def test_automation_active_check(  # type:ignore[no-untyped-def]
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Mapping[str, str],
    active_check_args: list[str],
    expected_result: automation_results.ActiveCheckResult,
    monkeypatch,
):
    monkeypatch.setattr(config, "active_check_info", active_check_info)
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *_: host_attrs)
    monkeypatch.setattr(check_mk.AutomationActiveCheck, "_load_resource_file", lambda *_: None)

    config_cache = config.get_config_cache()
    config_cache.initialize()
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    active_check = check_mk.AutomationActiveCheck()
    assert active_check.execute(active_check_args) == expected_result


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, active_check_args, error_message",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
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
            r"The check argument function needs to return either a list of arguments or a string of the concatenated arguments \(Host: my_host, Service: Active check of my_host\).",
            id="invalid_args",
        ),
    ],
)
def test_automation_active_check_invalid_args(  # type:ignore[no-untyped-def]
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Mapping[str, str],
    active_check_args: list[str],
    error_message: str,
    monkeypatch,
):
    monkeypatch.setattr(config, "active_check_info", active_check_info)
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *_: host_attrs)
    monkeypatch.setattr(check_mk.AutomationActiveCheck, "_load_resource_file", lambda *_: None)

    config_cache = config.get_config_cache()
    config_cache.initialize()
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    active_check = check_mk.AutomationActiveCheck()
    with pytest.raises(exceptions.MKGeneralException, match=error_message):
        active_check.execute(active_check_args)
