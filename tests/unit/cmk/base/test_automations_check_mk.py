#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from unittest.mock import MagicMock

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

import cmk.ccc.debug

import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostAddress

from cmk.automations import results as automation_results
from cmk.automations.results import DiagHostResult

from cmk.snmplib import oids_to_walk, SNMPContextConfig

from cmk.fetchers import PiggybackFetcher

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
        assert check_mk.AutomationDiagHost().execute(args, False) == DiagHostResult(
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

    config_cache = config.reset_config_cache()
    monkeypatch.setattr(config_cache, "active_checks", lambda *a, **kw: active_checks)

    active_check = AutomationActiveCheckTestable()
    assert active_check.execute(active_check_args, False) == expected_result


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
    monkeypatch.setattr(
        config, config.lookup_ip_address.__name__, lambda *a, **kw: HostAddress("127.0.0.1")
    )
    monkeypatch.setattr(ConfigCache, "get_host_attributes", lambda *a, **kw: host_attrs)
    monkeypatch.setattr(config, "get_resource_macros", lambda *a, **kw: {})

    config_cache = config.reset_config_cache()
    monkeypatch.setattr(config_cache, "active_checks", lambda *a, **kw: active_checks)

    monkeypatch.setattr(cmk.ccc.debug, "enabled", lambda: False)

    active_check = check_mk.AutomationActiveCheck()
    active_check.execute(active_check_args, False)

    assert error_message == capsys.readouterr().err


@pytest.mark.parametrize(
    "contexts",
    [
        pytest.param([""], id="single_default_context"),
        pytest.param(["", "vrf1", "mgmt"], id="multiple_contexts"),
    ],
)
def test_execute_snmp_walk_uses_all_configured_contexts(contexts: list[str]) -> None:
    """All configured SNMPv3 contexts are used when downloading an SNMP walk."""
    snmp_config_mock = MagicMock()
    snmp_config_mock.snmpv3_contexts_of.return_value = SNMPContextConfig(
        section=None, contexts=contexts, timeout_policy="stop"
    )
    backend_mock = MagicMock()
    backend_mock.walk.return_value = []

    check_mk._execute_snmp_walk(snmp_config_mock, backend_mock)

    walked_contexts = [c.kwargs["context"] for c in backend_mock.walk.call_args_list]
    assert walked_contexts == contexts * len(oids_to_walk())


def test_execute_snmp_walk_deduplicates_oids_across_contexts() -> None:
    """OIDs returned by multiple contexts for the same walk OID appear only once in the output."""
    shared_oid = ".1.3.6.1.2.1.1.0"
    snmp_config_mock = MagicMock()
    snmp_config_mock.snmpv3_contexts_of.return_value = SNMPContextConfig(
        section=None, contexts=["", "vrf1"], timeout_policy="stop"
    )
    backend_mock = MagicMock()
    # Return the shared OID only when walking the first subtree, empty for others.
    backend_mock.walk.side_effect = lambda oid, context: (
        [(shared_oid, b"value")] if oid == ".1.3.6.1.2.1" else []
    )

    raw_data, _ = check_mk._execute_snmp_walk(snmp_config_mock, backend_mock)

    assert raw_data.count(shared_oid.encode()) == 1
    assert b".1.3.6.1.2.1.1.0 value" in raw_data
