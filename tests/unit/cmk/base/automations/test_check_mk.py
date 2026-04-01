#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import cmk.ccc.debug
import cmk.ccc.resulttype as result

# We need an active check plugin that exists.
# The ExecutableFinder demands a location that exits :-/
# We're importing it here, so that this fails the linters if that is removed.
# TODO: implement a dedicated minimal plugin
import cmk.plugins.monitoring_plugins.server_side_calls.ftp
from cmk.automations import results as automation_results
from cmk.automations.results import DiagHostResult
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.automations import check_mk
from cmk.base.automations.automations import AutomationContext
from cmk.base.config import ConfigCache
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.version import Edition
from cmk.checkengine.discovery import CheckPreview, CheckPreviewEntry, QualifiedDiscovery
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.discover_plugins import PluginLocation
from cmk.fetchers import (
    Fetcher,
    FetcherSecrets,
    Mode,
    PiggybackFetcher,
    PlainFetcherTrigger,
)
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, replace_macros
from cmk.server_side_calls_backend import load_active_checks
from cmk.snmplib import oids_to_walk, SNMPContextConfig
from cmk.utils import config_warnings
from cmk.utils.tags import TagGroupID, TagID
from tests.testlib.common.empty_config import EMPTY_CONFIG
from tests.testlib.unit.base_configuration_scenario import Scenario

_TEST_LOCATION = PluginLocation(
    cmk.plugins.monitoring_plugins.server_side_calls.ftp.__name__,
    "yolo",
)


class _MockFetcherTrigger(PlainFetcherTrigger):
    def __init__(self, payload: bytes, omd_root: Path) -> None:
        super().__init__(omd_root)
        self._payload = payload

    def _trigger(self, fetcher: Fetcher, mode: Mode, secret: FetcherSecrets) -> result.Result:
        if isinstance(fetcher, PiggybackFetcher):
            return result.OK(b"")
        return result.OK(self._payload)


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

        loaded_config = replace(EMPTY_CONFIG, host_tags=configured_tags)

        assert check_mk.AutomationDiagHost().execute(
            AutomationContext(
                edition=(app := make_app(Edition.COMMUNITY)).edition,
                make_bake_on_restart=app.make_bake_on_restart,
                create_core=app.create_core,
                make_fetcher_trigger=lambda *args: _MockFetcherTrigger(
                    raw_data.encode("utf-8"), Path("/")
                ),
                make_metric_backend_fetcher=app.make_metric_backend_fetcher,
                get_builtin_host_labels=app.get_builtin_host_labels,
            ),
            args,
            AgentBasedPlugins.empty(),
            config.LoadingResult(
                loaded_config=loaded_config,
                config_cache=ConfigCache(loaded_config, app.get_builtin_host_labels, app.edition),
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
                _TEST_LOCATION: MOCK_PLUGIN,
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
                _TEST_LOCATION: MOCK_PLUGIN,
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
                _TEST_LOCATION: ActiveCheckConfig(
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
    monkeypatch.setattr(check_mk, "get_service_attributes", lambda *a, **kw: service_attrs)
    monkeypatch.setattr(config, config.load_resource_cfg_macros.__name__, lambda *a, **kw: {})

    app = make_app(Edition.COMMUNITY)
    config_cache = config.ConfigCache(EMPTY_CONFIG, app.get_builtin_host_labels, app.edition)
    monkeypatch.setattr(config_cache, "active_checks", lambda *a, **kw: active_checks)

    active_check = AutomationActiveCheckTestable()
    assert (
        active_check.execute(
            AutomationContext(
                edition=app.edition,
                make_bake_on_restart=app.make_bake_on_restart,
                create_core=app.create_core,
                make_fetcher_trigger=app.make_fetcher_trigger,
                make_metric_backend_fetcher=app.make_metric_backend_fetcher,
                get_builtin_host_labels=app.get_builtin_host_labels,
            ),
            active_check_args,
            AgentBasedPlugins.empty(),
            config.LoadingResult(
                loaded_config=EMPTY_CONFIG,
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
    monkeypatch.setattr(config, config.load_resource_cfg_macros.__name__, lambda *a, **kw: {})

    loaded_config = replace(
        EMPTY_CONFIG, ipaddresses={HostName("my_host"): HostAddress("127.0.0.1")}
    )
    app = make_app(Edition.COMMUNITY)
    config_cache = config.ConfigCache(loaded_config, app.get_builtin_host_labels, app.edition)
    monkeypatch.setattr(config_cache, "active_checks", lambda *a, **kw: active_checks)

    monkeypatch.setattr(cmk.ccc.debug, "enabled", lambda: False)

    active_check = check_mk.AutomationActiveCheck()
    active_check.execute(
        AutomationContext(
            edition=app.edition,
            make_bake_on_restart=app.make_bake_on_restart,
            create_core=app.create_core,
            make_fetcher_trigger=app.make_fetcher_trigger,
            make_metric_backend_fetcher=app.make_metric_backend_fetcher,
            get_builtin_host_labels=app.get_builtin_host_labels,
        ),
        active_check_args,
        AgentBasedPlugins.empty(),
        config.LoadingResult(loaded_config=loaded_config, config_cache=config_cache),
    )

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


class TestWarnServiceNameConflicts:
    """Unit tests for _warn_service_name_conflicts."""

    def _make_entry(
        self, description: str, check_plugin_name: str, check_source: str = "unchanged"
    ) -> CheckPreviewEntry:
        return CheckPreviewEntry(
            check_source=check_source,
            check_plugin_name=check_plugin_name,
            ruleset_name=None,
            discovery_ruleset_name=None,
            item=None,
            old_discovered_parameters={},
            new_discovered_parameters={},
            effective_parameters={},
            description=description,
            state=None,
            output="",
            metrics=[],
            old_labels={},
            new_labels={},
            found_on_nodes=[HostName("my_host")],
        )

    def _make_preview(self, entries: list) -> CheckPreview:
        return CheckPreview(
            table={HostName("my_host"): entries},
            labels=QualifiedDiscovery.empty(),
            source_results={},
            kept_labels={},
        )

    def test_no_conflict(self) -> None:
        config_warnings.initialize()
        preview = self._make_preview(
            [
                self._make_entry("Service A", "plugin_one", "unchanged"),
                self._make_entry("Service B", "plugin_two", "new"),
            ]
        )
        check_mk._warn_service_name_conflicts(HostName("my_host"), preview)
        assert config_warnings.get_configuration(additional_warnings=()) == []

    def test_passive_passive_conflict_emits_warning(self) -> None:
        config_warnings.initialize()
        preview = self._make_preview(
            [
                self._make_entry("Check_MK Agent", "checkmk_agent", "unchanged"),
                self._make_entry("Check_MK Agent", "custom_query_metric_backend", "new"),
            ]
        )
        check_mk._warn_service_name_conflicts(HostName("my_host"), preview)
        warnings = config_warnings.get_configuration(additional_warnings=())
        assert len(warnings) == 1
        assert "Check_MK Agent" in warnings[0]
        assert "checkmk_agent" in warnings[0]
        assert "custom_query_metric_backend" in warnings[0]

    def test_vanished_monitored_conflict_emits_warning(self) -> None:
        """A vanished (but still monitored) service can conflict with a new service.

        This is the real-world scenario: the existing monitored service shows as
        "vanished" on the discovery page while the new conflicting service is "new".
        """
        config_warnings.initialize()
        preview = self._make_preview(
            [
                self._make_entry("Check_MK Agent", "checkmk_agent", "vanished"),
                self._make_entry("Check_MK Agent", "custom_query_metric_backend", "new"),
            ]
        )
        check_mk._warn_service_name_conflicts(HostName("my_host"), preview)
        warnings = config_warnings.get_configuration(additional_warnings=())
        assert len(warnings) == 1
        assert "Check_MK Agent" in warnings[0]
        assert "checkmk_agent" in warnings[0]
        assert "custom_query_metric_backend" in warnings[0]

    def test_more_than_two_conflicts_emits_single_warning(self) -> None:
        config_warnings.initialize()
        preview = self._make_preview(
            [
                self._make_entry("My Service", "plugin_a", "unchanged"),
                self._make_entry("My Service", "plugin_b", "new"),
                self._make_entry("My Service", "plugin_c", "new"),
            ]
        )
        check_mk._warn_service_name_conflicts(HostName("my_host"), preview)
        warnings = config_warnings.get_configuration(additional_warnings=())
        assert len(warnings) == 1
        assert "My Service" in warnings[0]
        assert "plugin_a" in warnings[0]
        assert "plugin_b" in warnings[0]
        assert "plugin_c" in warnings[0]

    def test_ignored_active_does_not_trigger_warning(self) -> None:
        config_warnings.initialize()
        preview = self._make_preview(
            [
                self._make_entry("Service A", "plugin_one", "ignored_active"),
                self._make_entry("Service A", "plugin_two", "unchanged"),
            ]
        )
        check_mk._warn_service_name_conflicts(HostName("my_host"), preview)
        assert config_warnings.get_configuration(additional_warnings=()) == []

    def test_active_passive_conflict_emits_warning(self) -> None:
        config_warnings.initialize()
        preview = self._make_preview(
            [
                self._make_entry("Check_MK Agent", "checkmk_agent", "unchanged"),
                self._make_entry("Check_MK Agent", "httpv2", "active"),
            ]
        )
        check_mk._warn_service_name_conflicts(HostName("my_host"), preview)
        warnings = config_warnings.get_configuration(additional_warnings=())
        assert len(warnings) == 1
        assert "Check_MK Agent" in warnings[0]
