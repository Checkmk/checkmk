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
from typing import Dict

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

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
