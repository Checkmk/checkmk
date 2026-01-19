#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"


import importlib
import io
import itertools
import os
import socket
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

import pytest
from pytest import MonkeyPatch

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
import cmk.plugins.collection.server_side_calls.ftp
from cmk.base import config

# We need an active check plugin that exists.
# The ExecutableFinder demands a location that exits :-/
# We're importing it here, so that this fails the linters if that is removed.
from cmk.base.app import make_app
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core.nagios._create_config import (
    _format_nagios_object,
    create_nagios_config_commands,
    create_nagios_host_spec,
    create_nagios_servicedefs,
    NagiosConfig,
)
from cmk.base.core.nagios._precompile_host_checks import (
    dump_precompiled_hostcheck,
    HostCheckStore,
    PrecompileMode,
)
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import AgentBasedPlugins, AutocheckEntry, CheckPlugin, CheckPluginName
from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig
from cmk.server_side_calls_backend import load_active_checks
from cmk.utils import ip_lookup, paths
from cmk.utils.labels import ABCLabelConfig, LabelManager, Labels
from cmk.utils.servicename import ServiceName
from tests.testlib.unit.base_configuration_scenario import Scenario
from tests.unit.cmk.base.empty_config import EMPTY_CONFIG

_TEST_LOCATION = PluginLocation(
    cmk.plugins.collection.server_side_calls.ftp.__name__,
    "yolo",
)


def ip_address_of_never_called(
    _h: HostName, _f: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
) -> HostAddress:
    raise AssertionError(
        "It seems you unmocked some things in the test? This used to not be called."
    )


def ip_address_of_return_local(
    host_name: HostName,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6] | None = None,
) -> HostAddress:
    return HostAddress("127.0.0.1")


def _patch_plugin_loading(
    monkeypatch: pytest.MonkeyPatch,
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
) -> None:
    monkeypatch.setattr(
        config,
        load_active_checks.__name__,
        lambda *a, **kw: loaded_active_checks,
    )


def test_format_nagios_object() -> None:
    spec = {
        "use": "ding",
        "bla": "däng",
        "check_interval": "hüch",
        "_HÄÄÄÄ": "XXXXXX_YYYY",
    }
    cfg = _format_nagios_object("service", spec)
    assert isinstance(cfg, str)
    assert (
        cfg
        == """define service {
  %-29s %s
  %-29s %s
  %-29s %s
  %-29s %s
}

"""
        % tuple(itertools.chain(*sorted(spec.items(), key=lambda x: x[0])))
    )


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        (
            "localhost",
            {
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
                "_ADDRESS_4": "127.0.0.1",
                "_ADDRESS_6": "",
                "_ADDRESS_FAMILY": "4",
                "_TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp",
                "__TAG_address_family": "ip-v4-only",
                "__TAG_agent": "cmk-agent",
                "__TAG_criticality": "prod",
                "__TAG_ip-v4": "ip-v4",
                "__TAG_networking": "lan",
                "__TAG_piggyback": "auto-piggyback",
                "__TAG_site": "unit",
                "__TAG_snmp_ds": "no-snmp",
                "__TAG_tcp": "tcp",
                "__TAG_checkmk-agent": "checkmk-agent",
                "_FILENAME": "/wato/hosts.mk",
                "address": "127.0.0.1",
                "alias": "localhost",
                "check_command": "check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%",
                "contact_groups": "check-mk-notify",
                "host_name": "localhost",
                "hostgroups": "check_mk",
                "use": "check_mk_host",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "unit",
            },
        ),
        (
            "host2",
            {
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
                "_ADDRESS_4": "0.0.0.0",
                "_ADDRESS_6": "",
                "_ADDRESS_FAMILY": "4",
                "_FILENAME": "/wato/hosts.mk",
                "_TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp",
                "__TAG_address_family": "ip-v4-only",
                "__TAG_agent": "cmk-agent",
                "__TAG_criticality": "prod",
                "__TAG_ip-v4": "ip-v4",
                "__TAG_networking": "lan",
                "__TAG_piggyback": "auto-piggyback",
                "__TAG_site": "unit",
                "__TAG_snmp_ds": "no-snmp",
                "__TAG_tcp": "tcp",
                "__TAG_checkmk-agent": "checkmk-agent",
                "address": "0.0.0.0",
                "alias": "lOCALhost",
                "check_command": "check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%",
                "contact_groups": "check-mk-notify",
                "host_name": "host2",
                "hostgroups": "check_mk",
                "use": "check_mk_host",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "unit",
            },
        ),
        (
            "cluster1",
            {
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
                "_ADDRESS_4": "",
                "_ADDRESS_6": "",
                "_ADDRESS_FAMILY": "4",
                "_FILENAME": "/wato/hosts.mk",
                "_NODEIPS": "",
                "_NODEIPS_4": "",
                "_NODEIPS_6": "",
                "_NODENAMES": "",
                "_TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp",
                "__TAG_address_family": "ip-v4-only",
                "__TAG_agent": "cmk-agent",
                "__TAG_criticality": "prod",
                "__TAG_ip-v4": "ip-v4",
                "__TAG_networking": "lan",
                "__TAG_piggyback": "auto-piggyback",
                "__TAG_site": "unit",
                "__TAG_snmp_ds": "no-snmp",
                "__TAG_tcp": "tcp",
                "__TAG_checkmk-agent": "checkmk-agent",
                "address": "0.0.0.0",
                "alias": "cluster1",
                "check_command": "check-mk-host-ping-cluster!-w 200.00,80.00% -c 500.00,100.00%",
                "contact_groups": "check-mk-notify",
                "host_name": "cluster1",
                "hostgroups": "check_mk",
                "parents": "",
                "use": "check_mk_cluster",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "unit",
            },
        ),
        (
            "cluster2",
            {
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
                "_ADDRESS_4": "",
                "_ADDRESS_6": "",
                "_ADDRESS_FAMILY": "4",
                "_FILENAME": "/wato/hosts.mk",
                "_NODEIPS": "127.0.0.1 127.0.0.2",
                "_NODEIPS_4": "127.0.0.1 127.0.0.2",
                "_NODEIPS_6": "",
                "_NODENAMES": "node1 node2",
                "_TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp",
                "__TAG_address_family": "ip-v4-only",
                "__TAG_agent": "cmk-agent",
                "__TAG_criticality": "prod",
                "__TAG_ip-v4": "ip-v4",
                "__TAG_networking": "lan",
                "__TAG_piggyback": "auto-piggyback",
                "__TAG_site": "unit",
                "__TAG_snmp_ds": "no-snmp",
                "__TAG_tcp": "tcp",
                "__TAG_checkmk-agent": "checkmk-agent",
                "address": "0.0.0.0",
                "alias": "CLUSTer",
                "check_command": "check-mk-host-ping-cluster!-w 200.00,80.00% -c 500.00,100.00%",
                "contact_groups": "check-mk-notify",
                "host_name": "cluster2",
                "hostgroups": "check_mk",
                "parents": "node1,node2",
                "use": "check_mk_cluster",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "unit",
            },
        ),
        (
            "node1",
            {
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
                "_ADDRESS_4": "127.0.0.1",
                "_ADDRESS_6": "",
                "_ADDRESS_FAMILY": "4",
                "_FILENAME": "/wato/hosts.mk",
                "_TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp",
                "__TAG_address_family": "ip-v4-only",
                "__TAG_agent": "cmk-agent",
                "__TAG_criticality": "prod",
                "__TAG_ip-v4": "ip-v4",
                "__TAG_networking": "lan",
                "__TAG_piggyback": "auto-piggyback",
                "__TAG_site": "unit",
                "__TAG_snmp_ds": "no-snmp",
                "__TAG_tcp": "tcp",
                "__TAG_checkmk-agent": "checkmk-agent",
                "address": "127.0.0.1",
                "alias": "node1",
                "check_command": "check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%",
                "contact_groups": "check-mk-notify",
                "host_name": "node1",
                "hostgroups": "check_mk",
                "parents": "switch",
                "use": "check_mk_host",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "unit",
            },
        ),
    ],
)
def test_create_nagios_host_spec(
    hostname_str: str, result: dict[str, str], monkeypatch: MonkeyPatch
) -> None:
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.ULTIMATEMT:
        result = result.copy()
        result["_CUSTOMER"] = "provider"
        result["__LABELSOURCE_cmk/customer"] = "discovered"
        result["__LABEL_cmk/customer"] = "provider"

    ts = Scenario()
    ts.add_host(HostName("localhost"))
    ts.add_host(HostName("host2"))
    ts.add_cluster(HostName("cluster1"))

    ts.add_cluster(HostName("cluster2"), nodes=[HostName("node1"), HostName("node2")])
    ts.add_host(HostName("node1"))
    ts.add_host(HostName("node2"))
    ts.add_host(HostName("switch"))
    ts.set_option(
        "ipaddresses",
        {
            HostName("node1"): "127.0.0.1",
            HostName("node2"): "127.0.0.2",
        },
    )

    ts.set_option(
        "extra_host_conf",
        {
            "alias": [
                ("lOCALhost", ["localhost"]),
            ],
        },
    )

    ts.set_option(
        "extra_host_conf",
        {
            "alias": [
                {"id": "01", "condition": {"host_name": ["host2"]}, "value": "lOCALhost"},
                {"id": "02", "condition": {"host_name": ["cluster2"]}, "value": "CLUSTer"},
            ],
            "parents": [
                {"id": "03", "condition": {"host_name": ["node1", "node2"]}, "value": "switch"},
            ],
        },
    )

    hostname = HostName(hostname_str)
    outfile = io.StringIO()
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})

    config_cache = ts.apply(monkeypatch)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(config_cache.ip_lookup_config()),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    host_attrs = config_cache.get_host_attributes(
        hostname, socket.AddressFamily.AF_INET, ip_address_of
    )

    host_spec = create_nagios_host_spec(
        cfg, config_cache, hostname, socket.AddressFamily.AF_INET, host_attrs, ip_address_of
    )
    assert host_spec == result


def test_create_nagios_host_spec_service_period(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(hostname := HostName("localhost"))
    ts.set_option(
        "extra_host_conf",
        {
            "service_period": [
                {
                    "id": "fb112216-e458-474f-86d2-fee4d6cfec91",
                    "value": "24X7",
                    "condition": {},
                    "options": {"disabled": False},
                },
            ],
        },
    )

    config_cache = ts.apply(monkeypatch)

    host_attrs = config_cache.get_host_attributes(
        hostname, socket.AddressFamily.AF_INET, ip_address_of=lambda *a: HostAddress("")
    )

    cfg = NagiosConfig(io.StringIO(), [hostname], timeperiods={})
    host_spec = create_nagios_host_spec(
        cfg,
        config_cache,
        hostname,
        socket.AddressFamily.AF_INET,
        host_attrs,
        ip_address_of=lambda *a: HostAddress(""),
    )
    assert host_spec["_SERVICE_PERIOD"] == "24X7"
    assert "service_period" not in host_spec


@pytest.fixture(name="config_path")
def fixture_config_path(tmp_path: Path) -> Path:
    return Path(VersionedConfigPath(tmp_path, 42))


class TestHostCheckStore:
    def test_host_check_file_path(self, config_path: Path) -> None:
        assert HostCheckStore.host_check_file_path(config_path, HostName("abc")) == Path(
            config_path,
            "host_checks",
            "abc",
        )

    def test_host_check_source_file_path(self, config_path: Path) -> None:
        assert (
            HostCheckStore.host_check_source_file_path(
                config_path,
                HostName("abc"),
            )
            == config_path / "host_checks" / "abc.py"
        )

    def test_write(self, config_path: Path) -> None:
        hostname = HostName("aaa")
        store = HostCheckStore()

        assert config.delay_precompile is False

        assert not store.host_check_source_file_path(config_path, hostname).exists()
        assert not store.host_check_file_path(config_path, hostname).exists()

        store.write(config_path, hostname, "xyz", precompile_mode=PrecompileMode.INSTANT)

        assert store.host_check_source_file_path(config_path, hostname).exists()
        assert store.host_check_file_path(config_path, hostname).exists()

        with store.host_check_source_file_path(config_path, hostname).open() as s:
            assert s.read() == "xyz"

        with store.host_check_file_path(config_path, hostname).open("rb") as p:
            assert p.read().startswith(importlib.util.MAGIC_NUMBER)

        assert os.access(store.host_check_file_path(config_path, hostname), os.X_OK)


def _make_plugins_for_test() -> AgentBasedPlugins:
    """Don't load actual plugins, just create some dummy objects."""
    # most attributes are not used in this test
    return AgentBasedPlugins(
        agent_sections={},
        snmp_sections={},
        check_plugins={
            CheckPluginName("uptime"): CheckPlugin(
                name=CheckPluginName("uptime"),
                sections=[],
                service_name="",
                discovery_function=lambda: (),
                discovery_default_parameters=None,
                discovery_ruleset_name=None,
                discovery_ruleset_type="merged",
                check_function=lambda: (),
                check_default_parameters=None,
                check_ruleset_name=None,
                cluster_check_function=None,
                location=PluginLocation("some.test.module.name", "uptime"),
            )
        },
        inventory_plugins={},
        errors=(),
    )


def test_dump_precompiled_hostcheck(monkeypatch: MonkeyPatch, config_path: Path) -> None:
    hostname = HostName("localhost")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_autochecks(
        hostname,
        [AutocheckEntry(CheckPluginName("uptime"), None, {}, {})],
    )
    config_cache = ts.apply(monkeypatch)

    host_check = dump_precompiled_hostcheck(
        config_cache,
        passive_service_name_config=lambda *a: "",
        enforced_services_table=lambda hn: {},
        config_path=config_path,
        hostname=hostname,
        get_ip_stack_config=lambda *a: ip_lookup.IPStackConfig.IPv4,
        plugins=_make_plugins_for_test(),
        precompile_mode=PrecompileMode.INSTANT,
        ip_address_of=lambda *a: HostAddress("1.2.3.4"),
    )
    assert host_check is not None
    assert host_check.startswith("#!/usr/bin/env python3")

    try:
        exec(host_check)
    except Exception as e:
        assert False, f"Execution failed with error: {e}"


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


class FakeLabelConfig(ABCLabelConfig):
    def __init__(self, service_labels: Mapping[str, str]):
        self._service_lables = service_labels

    def host_labels(self, host_name: HostName, /) -> Labels:
        """Returns the configured labels for a host"""
        return {}

    def service_labels(
        self,
        host_name: HostName,
        service_name: ServiceName,
        labels_of_host: Callable[[HostName], Labels],
        /,
    ) -> Labels:
        return self._service_lables


@pytest.mark.parametrize(
    "active_checks, loaded_active_checks, host_attrs, service_labels, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {_TEST_LOCATION: MOCK_PLUGIN},
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {"os": "aix"},  # service labels
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  __LABELSOURCE_6F73            616978\n"
            "  __LABEL_6F73                  616978\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--arg1 arument1 --host_alias my_host_alias\n"
            "  check_interval                1.0\n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_perf,check_mk_default\n"
            "}\n"
            "\n",
            id="active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {_TEST_LOCATION: MOCK_PLUGIN},
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "0.0.0.0",
                "address": "0.0.0.0",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {"os": "aix"},  # service labels
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  __LABELSOURCE_6F73            616978\n"
            "  __LABEL_6F73                  616978\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!'Failed to lookup IP address and no explicit IP address configured'\n"
            "  check_interval                1.0\n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_perf,check_mk_default\n"
            "}\n"
            "\n",
            id="offline_active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {_TEST_LOCATION: MOCK_PLUGIN},
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            {},  # service labels
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--arg1 arument1 --host_alias my_host_alias\n"
            "  check_interval                1.0\n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_perf,check_mk_default\n"
            "}\n"
            "\n",
            id="duplicate_active_checks",
        ),
    ],
)
def test_create_nagios_servicedefs_active_check(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
    host_attrs: dict[str, Any],
    service_labels: Mapping[str, str],
    expected_result: str,
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_plugin_loading(monkeypatch, loaded_active_checks)
    monkeypatch.setattr(config, config.load_resource_cfg_macros.__name__, lambda *a: {})

    hostname = HostName("my_host")
    config_cache = config.ConfigCache(
        EMPTY_CONFIG,
        make_app(cmk_version.edition(paths.omd_root)).get_builtin_host_labels,
    )
    config_cache.label_manager = LabelManager(FakeLabelConfig(service_labels), {}, {}, {})
    monkeypatch.setattr(config_cache, "alias", lambda hn: {hostname: host_attrs["alias"]}[hn])
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    final_service_name_config = make_final_service_name_config(
        config_cache._loaded_config, config_cache.ruleset_matcher
    )
    outfile = io.StringIO()
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})
    license_counter = Counter("services")
    create_nagios_servicedefs(
        cfg,
        config_cache,
        final_service_name_config=final_service_name_config,
        passive_service_name_config=config_cache.make_passive_service_name_config(
            final_service_name_config
        ),
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=hostname,
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=license_counter,
        ip_address_of=ip_address_of_return_local,
        service_depends_on=lambda *a: (),
        for_relay=False,
    )

    assert outfile.getvalue() == expected_result
    assert license_counter["services"] == 1


def test_create_nagios_servicedefs_service_period(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(hostname := HostName("localhost"))
    ts.set_option(
        "extra_service_conf",
        {
            "service_period": [
                {
                    "id": "fb112216-e458-474f-86d2-fee4d6cfec92",
                    "value": "24X7",
                    "condition": {},
                    "options": {"disabled": False},
                },
            ],
        },
    )

    config_cache = ts.apply(monkeypatch)

    host_attrs = config_cache.get_host_attributes(
        hostname, socket.AddressFamily.AF_INET, ip_address_of_return_local
    )
    outfile = io.StringIO()
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})
    license_counter = Counter("services")
    create_nagios_servicedefs(
        cfg,
        config_cache,
        final_service_name_config=lambda *a: "",
        passive_service_name_config=lambda *a: "",
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=hostname,
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=license_counter,
        ip_address_of=ip_address_of_return_local,
        service_depends_on=lambda *a: (),
        for_relay=False,
    )

    config_snippet = outfile.getvalue()
    assert "service_period" not in config_snippet
    assert "_SERVICE_PERIOD" in config_snippet


@pytest.mark.parametrize(
    "active_checks, loaded_active_checks, host_attrs, expected_result, expected_warning",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
                ("my_active_check2", [{"description": "My active check", "param2": "param2"}]),
            ],
            {
                _TEST_LOCATION: ActiveCheckConfig(
                    name="my_active_check",
                    parameter_parser=lambda x: x,
                    commands_function=lambda params, host_config: (
                        ActiveCheckCommand(
                            service_description="My description",
                            command_arguments=("--option", "value"),
                        ),
                    ),
                ),
                PluginLocation(_TEST_LOCATION.module, "some_other_name"): ActiveCheckConfig(
                    name="my_active_check2",
                    parameter_parser=lambda x: x,
                    commands_function=lambda params, host_config: (
                        ActiveCheckCommand(
                            service_description="My description",
                            command_arguments=("--option", "value"),
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
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--option value\n"
            "  check_interval                1.0\n"
            "  host_name                     my_host\n"
            "  service_description           My description\n"
            "  use                           check_mk_perf,check_mk_default\n"
            "}\n"
            "\n",
            "\n"
            "WARNING: ERROR: Duplicate service name (active check) 'My description' for host 'my_host'!\n"
            " - 1st occurrence: check plug-in / item: active(my_active_check) / 'My description'\n"
            " - 2nd occurrence: check plug-in / item: active(my_active_check2) / None\n"
            "\n",
            id="duplicate_descriptions",
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
                            service_description="",
                            command_arguments=("--option", "value"),
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
            "\n\n# Active checks\n",
            "\n"
            "WARNING: Skipping invalid service with empty description (active check: my_active_check) on host my_host\n",
            id="empty_description",
        ),
    ],
)
def test_create_nagios_servicedefs_with_warnings(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
    host_attrs: dict[str, Any],
    expected_result: str,
    expected_warning: str,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_plugin_loading(monkeypatch, loaded_active_checks)
    monkeypatch.setattr(config, config.load_resource_cfg_macros.__name__, lambda *a: {})

    config_cache = config.ConfigCache(
        EMPTY_CONFIG,
        make_app(cmk_version.edition(paths.omd_root)).get_builtin_host_labels,
    )
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    final_service_name_config = make_final_service_name_config(
        config_cache._loaded_config, config_cache.ruleset_matcher
    )

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})
    license_counter = Counter("services")
    create_nagios_servicedefs(
        cfg,
        config_cache,
        final_service_name_config=final_service_name_config,
        passive_service_name_config=config_cache.make_passive_service_name_config(
            final_service_name_config
        ),
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=HostName("my_host"),
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=license_counter,
        ip_address_of=ip_address_of_return_local,
        service_depends_on=lambda *a: (),
        for_relay=False,
    )

    assert outfile.getvalue() == expected_result

    captured = capsys.readouterr()
    assert captured.err == expected_warning


@pytest.mark.parametrize(
    "active_checks, loaded_active_checks, host_attrs, expected_result",
    [
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
                            command_arguments=("--option", "value"),
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
            "\n\n# Active checks\n",
            id="omitted_service",
        ),
    ],
)
def test_create_nagios_servicedefs_omit_service(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
    host_attrs: dict[str, Any],
    expected_result: str,
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_plugin_loading(monkeypatch, loaded_active_checks)
    monkeypatch.setattr(config, config.load_resource_cfg_macros.__name__, lambda *a: {})

    config_cache = config.ConfigCache(
        EMPTY_CONFIG,
        make_app(cmk_version.edition(paths.omd_root)).get_builtin_host_labels,
    )
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)
    monkeypatch.setattr(config_cache, "service_ignored", lambda *_: True)

    outfile = io.StringIO()
    hostname = HostName("my_host")
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})
    license_counter = Counter("services")
    create_nagios_servicedefs(
        cfg,
        config_cache,
        final_service_name_config=lambda *a: "",
        passive_service_name_config=lambda *a: "",
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=hostname,
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=license_counter,
        ip_address_of=ip_address_of_return_local,
        service_depends_on=lambda *a: (),
        for_relay=False,
    )

    assert outfile.getvalue() == expected_result
    assert license_counter["services"] == 0


@pytest.mark.parametrize(
    "active_checks, loaded_active_checks, host_attrs, error_message",
    [
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
                            command_arguments=("--option", 42),  # type: ignore[arg-type]  # invalid on purpose
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
            "\nWARNING: Config creation for active check my_active_check failed on my_host:"
            " Got invalid argument list from SSC plugin: 42 at index 1 in ('--option', 42)."
            " Expected either `str` or `Secret`.\n",
            id="invalid_args",
        ),
    ],
)
def test_create_nagios_servicedefs_invalid_args(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    loaded_active_checks: Mapping[PluginLocation, ActiveCheckConfig],
    host_attrs: dict[str, Any],
    error_message: str,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_plugin_loading(monkeypatch, loaded_active_checks)

    config_cache = config.ConfigCache(
        EMPTY_CONFIG,
        make_app(cmk_version.edition(paths.omd_root)).get_builtin_host_labels,
    )
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    monkeypatch.setattr(cmk.ccc.debug, "enabled", lambda: False)

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})
    license_counter = Counter("services")

    create_nagios_servicedefs(
        cfg,
        config_cache,
        final_service_name_config=lambda *a: "",
        passive_service_name_config=lambda *a: "",
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=hostname,
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=license_counter,
        ip_address_of=ip_address_of_return_local,
        service_depends_on=lambda *a: (),
        for_relay=False,
    )

    assert error_message == capsys.readouterr().err


@pytest.mark.parametrize(
    "active_checks, host_attrs, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--option value\n"
            "  check_interval                1.0\n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_perf,check_mk_default\n"
            "}\n"
            "\n"
            "\n"
            "# ------------------------------------------------------------\n"
            "# Dummy check commands and active check commands\n"
            "# ------------------------------------------------------------\n"
            "\n"
            "define command {\n"
            "  command_line                  check_my_active_check $ARG1$\n"
            "  command_name                  check_mk_active-my_active_check\n"
            "}\n"
            "\n",
            id="active_check",
        ),
    ],
)
def test_create_nagios_config_commands(
    active_checks: tuple[str, Sequence[Mapping[str, str]]],
    host_attrs: dict[str, Any],
    expected_result: str,
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_plugin_loading(
        monkeypatch,
        {
            _TEST_LOCATION: ActiveCheckConfig(
                name="my_active_check",
                parameter_parser=lambda x: x,
                commands_function=lambda params, host_config: (
                    ActiveCheckCommand(
                        service_description=f"Active check of {host_config.name}",
                        command_arguments=("--option", "value"),
                    ),
                ),
            ),
        },
    )
    monkeypatch.setattr(config, config.load_resource_cfg_macros.__name__, lambda *a: {})

    config_cache = config.ConfigCache(
        EMPTY_CONFIG,
        make_app(cmk_version.edition(paths.omd_root)).get_builtin_host_labels,
    )
    monkeypatch.setattr(config_cache, "active_checks", lambda *args, **kw: active_checks)

    final_service_name_config = make_final_service_name_config(
        config_cache._loaded_config, config_cache.ruleset_matcher
    )
    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = NagiosConfig(outfile, [hostname], timeperiods={})
    license_counter = Counter("services")
    create_nagios_servicedefs(
        cfg,
        config_cache,
        final_service_name_config=final_service_name_config,
        passive_service_name_config=config_cache.make_passive_service_name_config(
            final_service_name_config
        ),
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=hostname,
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=license_counter,
        ip_address_of=lambda *a: HostAddress("127.0.0.1"),
        service_depends_on=lambda *a: (),
        for_relay=False,
    )
    create_nagios_config_commands(cfg)

    assert license_counter["services"] == 1
    assert outfile.getvalue() == expected_result
