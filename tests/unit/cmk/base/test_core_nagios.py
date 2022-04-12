#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import importlib
import io
import itertools
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

import cmk.utils.exceptions as exceptions
import cmk.utils.version as cmk_version
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.core_nagios as core_nagios


def test_format_nagios_object() -> None:
    spec = {
        "use": "ding",
        "bla": "däng",
        "check_interval": "hüch",
        "_HÄÄÄÄ": "XXXXXX_YYYY",
    }
    cfg = core_nagios._format_nagios_object("service", spec)
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
                "host_name": "localhost",
                "hostgroups": "check_mk",
                "use": "check_mk_host",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "NO_SITE",
            },
        ),
        (
            "host2",
            {
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
                "host_name": "host2",
                "hostgroups": "check_mk",
                "use": "check_mk_host",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "NO_SITE",
            },
        ),
        (
            "cluster1",
            {
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
                "host_name": "cluster1",
                "hostgroups": "check_mk",
                "parents": "",
                "use": "check_mk_cluster",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "NO_SITE",
            },
        ),
        (
            "cluster2",
            {
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
                "host_name": "cluster2",
                "hostgroups": "check_mk",
                "parents": "node1,node2",
                "use": "check_mk_cluster",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "NO_SITE",
            },
        ),
        (
            "node1",
            {
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
                "host_name": "node1",
                "hostgroups": "check_mk",
                "parents": "switch",
                "use": "check_mk_host",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABEL_cmk/site": "NO_SITE",
            },
        ),
    ],
)
def test_create_nagios_host_spec(
    hostname_str: str, result: Dict[str, str], monkeypatch: MonkeyPatch
) -> None:
    if cmk_version.is_managed_edition():
        result = result.copy()
        result["_CUSTOMER"] = "provider"

    ts = Scenario()
    ts.add_host(HostName("localhost"))
    ts.add_host(HostName("host2"))
    ts.add_cluster(HostName("cluster1"))

    ts.add_cluster(HostName("cluster2"), nodes=["node1", "node2"])
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
                ("lOCALhost", ["host2"]),
                ("CLUSTer", ["cluster2"]),
            ],
            "parents": [
                ("switch", ["node1", "node2"]),
            ],
        },
    )

    hostname = HostName(hostname_str)
    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])

    config_cache = ts.apply(monkeypatch)
    host_attrs = core_config.get_host_attributes(hostname, config_cache)

    host_spec = core_nagios._create_nagios_host_spec(cfg, config_cache, hostname, host_attrs)
    assert host_spec == result


@pytest.fixture(name="config_path")
def fixture_config_path() -> VersionedConfigPath:
    return VersionedConfigPath(42)


class TestHostCheckStore:
    def test_host_check_file_path(self, config_path: VersionedConfigPath) -> None:
        assert core_nagios.HostCheckStore.host_check_file_path(
            config_path, HostName("abc")
        ) == Path(
            Path(config_path),
            "host_checks",
            "abc",
        )

    def test_host_check_source_file_path(self, config_path: VersionedConfigPath) -> None:
        assert (
            core_nagios.HostCheckStore.host_check_source_file_path(
                config_path,
                HostName("abc"),
            )
            == Path(config_path) / "host_checks" / "abc.py"
        )

    def test_write(self, config_path: VersionedConfigPath) -> None:
        hostname = HostName("aaa")
        store = core_nagios.HostCheckStore()

        assert config.delay_precompile is False

        assert not store.host_check_source_file_path(config_path, hostname).exists()
        assert not store.host_check_file_path(config_path, hostname).exists()

        store.write(config_path, hostname, "xyz")

        assert store.host_check_source_file_path(config_path, hostname).exists()
        assert store.host_check_file_path(config_path, hostname).exists()

        with store.host_check_source_file_path(config_path, hostname).open() as s:
            assert s.read() == "xyz"

        with store.host_check_file_path(config_path, hostname).open("rb") as p:
            assert p.read().startswith(importlib.util.MAGIC_NUMBER)

        assert os.access(store.host_check_file_path(config_path, hostname), os.X_OK)


def test_dump_precompiled_hostcheck(
    monkeypatch: MonkeyPatch, config_path: VersionedConfigPath
) -> None:
    hostname = HostName("localhost")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)

    # Ensure a host check is created
    monkeypatch.setattr(
        core_nagios,
        "_get_needed_plugin_names",
        lambda c: (set(), {CheckPluginName("uptime")}, set()),
    )

    host_check = core_nagios._dump_precompiled_hostcheck(
        config_cache,
        config_path,
        hostname,
    )
    assert host_check is not None
    assert host_check.startswith("#!/usr/bin/env python3")


def test_dump_precompiled_hostcheck_without_check_mk_service(
    monkeypatch: MonkeyPatch, config_path: VersionedConfigPath
) -> None:
    hostname = HostName("localhost")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    host_check = core_nagios._dump_precompiled_hostcheck(
        config_cache,
        config_path,
        hostname,
    )
    assert host_check is None


def test_dump_precompiled_hostcheck_not_existing_host(
    monkeypatch: MonkeyPatch, config_path: VersionedConfigPath
) -> None:
    config_cache = Scenario().apply(monkeypatch)
    host_check = core_nagios._dump_precompiled_hostcheck(
        config_cache,
        config_path,
        HostName("not-existing"),
    )
    assert host_check is None


def test_compile_delayed_host_check(
    monkeypatch: MonkeyPatch, config_path: VersionedConfigPath
) -> None:
    hostname = HostName("localhost")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("delay_precompile", True)
    config_cache = ts.apply(monkeypatch)

    # Ensure a host check is created
    monkeypatch.setattr(
        core_nagios,
        "_get_needed_plugin_names",
        lambda c: (set(), {CheckPluginName("uptime")}, set()),
    )

    source_file = core_nagios.HostCheckStore.host_check_source_file_path(
        config_path,
        hostname,
    )
    compiled_file = core_nagios.HostCheckStore.host_check_file_path(config_path, hostname)

    assert config.delay_precompile is True
    assert not source_file.exists()
    assert not compiled_file.exists()

    # Write the host check source file
    host_check = core_nagios._dump_precompiled_hostcheck(
        config_cache,
        config_path,
        hostname,
        verify_site_python=False,
    )
    assert host_check is not None
    core_nagios.HostCheckStore().write(config_path, hostname, host_check)

    # The compiled file path links to the source file until it has been executed for the first
    # time. Then the symlink is replaced with the compiled file
    assert source_file.exists()
    assert compiled_file.exists()
    assert compiled_file.resolve() == source_file

    # Expect the command to fail: We don't have the correct environment to execute it.
    # But this is no problem for our test, we only want to see the result of the compilation.
    assert (
        subprocess.run(
            ["python3", str(compiled_file)],
            shell=False,
            close_fds=True,
            check=False,
        ).returncode
        == 1
    )
    assert compiled_file.resolve() != source_file
    with compiled_file.open("rb") as f:
        assert f.read().startswith(importlib.util.MAGIC_NUMBER)


def mock_argument_function(params: Mapping[str, str]) -> str:
    return "--arg1 arument1 --host_alias $HOSTALIAS$"


def mock_service_description(params: Mapping[str, str]) -> str:
    return "Active check of $HOSTNAME$"


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
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
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--arg1 arument1 --host_alias $HOSTALIAS$\n"
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n",
            id="active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
                    "argument_function": mock_argument_function,
                    "service_description": mock_service_description,
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "0.0.0.0",
                "address": "0.0.0.0",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            '  check_command                 check-mk-custom!echo "CRIT - Failed to lookup IP address and no explicit IP address configured" && exit 2\n'
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n",
            id="offline_active_check",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
                    "argument_function": lambda _: [
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
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!'--arg1' 'arument1' '--host_alias' '$HOSTALIAS$'\n"
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n",
            id="arguments_list",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
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
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--arg1 arument1 --host_alias $HOSTALIAS$\n"
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n",
            id="duplicate_active_checks",
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
                    "command_line": "some_command $ARG1$",
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
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-http!--arg1 arument1 --host_alias $HOSTALIAS$\n"
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           HTTP my special HTTP\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n",
            id="old_service_description",
        ),
    ],
)
def test_create_nagios_servicedefs_active_check(
    active_checks: Tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Dict[str, Any],
    expected_result: str,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.HostConfig, "active_checks", active_checks)
    monkeypatch.setattr(config, "active_check_info", active_check_info)

    cache = config.get_config_cache()
    cache.initialize()

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])
    core_nagios._create_nagios_servicedefs(cfg, cache, "my_host", host_attrs)

    assert outfile.getvalue() == expected_result


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, expected_result, expected_warning",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
                ("my_active_check2", [{"description": "My active check", "param2": "param2"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
                    "argument_function": mock_argument_function,
                    "service_description": lambda e: "My description",
                },
                "my_active_check2": {
                    "command_line": "some_command $ARG1$",
                    "argument_function": mock_argument_function,
                    "service_description": lambda e: "My description",
                },
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
            "  check_command                 check_mk_active-my_active_check!--arg1 arument1 --host_alias $HOSTALIAS$\n"
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           My description\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n",
            "\n"
            "WARNING: ERROR: Duplicate service description (active check) 'My description' for host 'my_host'!\n"
            " - 1st occurrence: check plugin / item: active(my_active_check) / 'My description'\n"
            " - 2nd occurrence: check plugin / item: active(my_active_check2) / None\n"
            "\n",
            id="duplicate_descriptions",
        ),
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
                    "argument_function": mock_argument_function,
                    "service_description": lambda _: "",
                }
            },
            {
                "alias": "my_host_alias",
                "_ADDRESS_4": "127.0.0.1",
                "address": "127.0.0.1",
                "_ADDRESS_FAMILY": "4",
                "display_name": "my_host",
            },
            "\n" "\n" "# Active checks\n",
            "\n"
            "WARNING: Skipping invalid service with empty description (active check: my_active_check) on host my_host\n",
            id="empty_description",
        ),
    ],
)
def test_create_nagios_servicedefs_with_warnings(
    active_checks: Tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Dict[str, Any],
    expected_result: str,
    expected_warning: str,
    monkeypatch: MonkeyPatch,
    capsys,
) -> None:
    monkeypatch.setattr(config.HostConfig, "active_checks", active_checks)
    monkeypatch.setattr(config, "active_check_info", active_check_info)

    cache = config.get_config_cache()
    cache.initialize()

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])
    core_nagios._create_nagios_servicedefs(cfg, cache, "my_host", host_attrs)

    assert outfile.getvalue() == expected_result

    captured = capsys.readouterr()
    assert captured.out == expected_warning


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
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
            "\n" "\n" "# Active checks\n",
            id="omitted_service",
        ),
    ],
)
def test_create_nagios_servicedefs_omit_service(
    active_checks: Tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Dict[str, Any],
    expected_result: str,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.HostConfig, "active_checks", active_checks)
    monkeypatch.setattr(config, "active_check_info", active_check_info)
    monkeypatch.setattr(config, "service_ignored", lambda *_: True)

    cache = config.get_config_cache()
    cache.initialize()

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])
    core_nagios._create_nagios_servicedefs(cfg, cache, "my_host", host_attrs)

    assert outfile.getvalue() == expected_result


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, error_message",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
                    "argument_function": lambda _: 12,
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
            r"The check argument function needs to return either a list of arguments or a string of the concatenated arguments \(Host: my_host, Service: Active check of my_host\).",
            id="invalid_args",
        ),
    ],
)
def test_create_nagios_servicedefs_invalid_args(
    active_checks: Tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Dict[str, Any],
    error_message: str,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.HostConfig, "active_checks", active_checks)
    monkeypatch.setattr(config, "active_check_info", active_check_info)

    cache = config.get_config_cache()
    cache.initialize()

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])

    with pytest.raises(exceptions.MKGeneralException, match=error_message):
        core_nagios._create_nagios_servicedefs(cfg, cache, "my_host", host_attrs)


@pytest.mark.parametrize(
    "active_checks, active_check_info, host_attrs, expected_result",
    [
        pytest.param(
            [
                ("my_active_check", [{"description": "My active check", "param1": "param1"}]),
            ],
            {
                "my_active_check": {
                    "command_line": "some_command $ARG1$",
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
            "\n"
            "\n"
            "# Active checks\n"
            "define service {\n"
            "  active_checks_enabled         1\n"
            "  check_command                 check_mk_active-my_active_check!--arg1 arument1 --host_alias $HOSTALIAS$\n"
            "  check_interval                1.0\n"
            "  contact_groups                \n"
            "  host_name                     my_host\n"
            "  service_description           Active check of my_host\n"
            "  use                           check_mk_default\n"
            "}\n"
            "\n"
            "\n"
            "# ------------------------------------------------------------\n"
            "# Dummy check commands and active check commands\n"
            "# ------------------------------------------------------------\n"
            "\n"
            "define command {\n"
            "  command_line                  some_command $ARG1$\n"
            "  command_name                  check_mk_active-my_active_check\n"
            "}\n"
            "\n",
            id="active_check",
        ),
    ],
)
def test_create_nagios_config_commands(
    active_checks: Tuple[str, Sequence[Mapping[str, str]]],
    active_check_info: Mapping[str, Mapping[str, str]],
    host_attrs: Dict[str, Any],
    expected_result: str,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.HostConfig, "active_checks", active_checks)
    monkeypatch.setattr(config, "active_check_info", active_check_info)

    cache = config.get_config_cache()
    cache.initialize()

    hostname = HostName("my_host")
    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])
    core_nagios._create_nagios_servicedefs(cfg, cache, "my_host", host_attrs)
    core_nagios._create_nagios_config_commands(cfg)

    assert outfile.getvalue() == expected_result
