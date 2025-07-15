#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import replace

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

from tests.unit.cmk.base.emptyconfig import EMPTYCONFIG

import cmk.ccc.debug
import cmk.ccc.resulttype as result
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.tags import TagGroupID, TagID

from cmk.automations import results as automation_results
from cmk.automations.results import DiagHostResult

from cmk.fetchers import PiggybackFetcher

from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base import config, core_config
from cmk.base.automations import check_mk
from cmk.base.config import ConfigCache

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, replace_macros
from cmk.server_side_calls_backend import load_active_checks


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
        return ts.apply(monkeypatch)

    @pytest.fixture
    def patch_fetch(self, raw_data, monkeypatch):
        monkeypatch.setattr(
            check_mk,
            "get_raw_data",
            lambda _file_cache, fetcher, _mode: (
                result.OK(b"") if isinstance(fetcher, PiggybackFetcher) else result.OK(raw_data)
            ),
        )

    @pytest.mark.usefixtures("patch_fetch")
    def test_execute(
        self, hostname: str, ipaddress: str, raw_data: str, scenario: ConfigCache
    ) -> None:
        args = [hostname, "agent", ipaddress, "", "6557", "10", "5", "5", ""]
        configured_tags = {
            HostName("testhost"): {
                TagGroupID("checkmk-agent"): TagID("checkmk-agent"),
                TagGroupID("piggyback"): TagID("auto-piggyback"),
                TagGroupID("networking"): TagID("lan"),
                TagGroupID("agent"): TagID("cmk-agent"),
                TagGroupID("criticality"): TagID("prod"),
                TagGroupID("snmp_ds"): TagID("no-snmp"),
                TagGroupID("site"): TagID("unit"),
                TagGroupID("address_family"): TagID("ip-v4-only"),
                TagGroupID("tcp"): TagID("tcp"),
                TagGroupID("ip-v4"): TagID("ip-v4"),
            }
        }

        loaded_config = replace(EMPTYCONFIG, host_tags=configured_tags)

        assert check_mk.AutomationDiagHost().execute(
            args,
            AgentBasedPlugins.empty(),
            config.LoadingResult(
                loaded_config=loaded_config,
                config_cache=ConfigCache(loaded_config),
            ),
        ) == DiagHostResult(
            0,
            raw_data,
        )


MOCK_PLUGIN = ActiveCheckConfig(
    name="my_active_check",
    parameter_parser=lambda x: x,
    commands_function=lambda params, host_config: (
        ActiveCheckCommand(
            service_description=f"Active check of {host_config.name}",
            command_arguments=("--arg1", "arument1", "--host_alias", f"{host_config.alias}"),
        ),
    ),
)


def _patch_plugin_loading(
    monkeypatch: pytest.MonkeyPatch,
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
) -> None:
    monkeypatch.setattr(
        config,
        load_active_checks.__name__,
        lambda *a, **kw: loaded_active_checks,
    )


class AutomationActiveCheckTestable(check_mk.AutomationActiveCheck):
    def _execute_check_plugin(self, commandline: Sequence[str]) -> tuple[int, str]:
        return (0, f"Assume I ran {commandline!r}")


@pytest.mark.parametrize(
    "active_checks, loaded_active_checks, host_attrs, service_attrs, active_check_args, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                PluginLocation("cmk.plugins", "some_name"): MOCK_PLUGIN,
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
                state=0,
                output="Assume I ran 'check_my_active_check --arg1 arument1 --host_alias my_host'",
            ),
            id="active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                PluginLocation("cmk.plugins", "some_name"): MOCK_PLUGIN,
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
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                PluginLocation("cmk.plugins", "some_name"): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda x: x,
                    commands_function=lambda params, host_config: (
                        ActiveCheckCommand(
                            service_description=f"Active check of {host_config.name}",
                            command_arguments=(
                                replace_macros("$_SERVICEFOO$", host_config.macros),
                            ),
                        ),
                    ),
                ),
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
            automation_results.ActiveCheckResult(
                state=0, output="Assume I ran \"check_my_active_check 'BAR'\""
            ),
            id="custom_service_attribute",
        ),
    ],
)
def test_automation_active_check(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
    host_attrs: Mapping[str, str],
    service_attrs: Mapping[str, str],
    active_check_args: list[str],
    expected_result: automation_results.ActiveCheckResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_plugin_loading(monkeypatch, loaded_active_checks)
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *a, **kw: host_attrs)
    monkeypatch.setattr(core_config, "get_service_attributes", lambda *a, **kw: service_attrs)
    monkeypatch.setattr(config, "get_resource_macros", lambda *a, **kw: {})

    config_cache = config.ConfigCache(EMPTYCONFIG)
    monkeypatch.setattr(config_cache, "active_checks", lambda *a, **kw: active_checks)

    active_check = AutomationActiveCheckTestable()
    assert (
        active_check.execute(
            active_check_args,
            AgentBasedPlugins.empty(),
            config.LoadingResult(
                loaded_config=EMPTYCONFIG,
                config_cache=config_cache,
            ),
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "active_checks, loaded_active_checks, host_attrs, active_check_args, error_message",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                PluginLocation("some_module", "some_name"): ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda x: x,
                    commands_function=lambda params, host_config: (
                        ActiveCheckCommand(
                            service_description=f"Active check of {host_config.name}",
                            command_arguments=(1, 2, 3),  # type: ignore[arg-type]  # wrong on purpose
                        ),
                    ),
                ),
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            ["my_host", "my_active_check", "Active check of my_host"],
            (
                "\nWARNING: Config creation for active check my_active_check failed on my_host: "
                "Got invalid argument list from SSC plugin: 1 at index 0 in (1, 2, 3). Expected either `str` or `Secret`.\n"
            ),
            id="invalid_args",
        ),
    ],
)
def test_automation_active_check_invalid_args(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
    host_attrs: Mapping[str, str],
    active_check_args: list[str],
    error_message: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_plugin_loading(monkeypatch, loaded_active_checks)
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *a, **kw: host_attrs)
    monkeypatch.setattr(config, "get_resource_macros", lambda *a, **kw: {})

    loaded_config = replace(
        EMPTYCONFIG, ipaddresses={HostName("my_host"): HostAddress("127.0.0.1")}
    )
    config_cache = config.ConfigCache(loaded_config)
    monkeypatch.setattr(config_cache, "active_checks", lambda *a, **kw: active_checks)

    monkeypatch.setattr(cmk.ccc.debug, "enabled", lambda: False)

    active_check = check_mk.AutomationActiveCheck()
    active_check.execute(
        active_check_args,
        AgentBasedPlugins.empty(),
        config.LoadingResult(loaded_config=loaded_config, config_cache=config_cache),
    )

    assert error_message == capsys.readouterr().err
