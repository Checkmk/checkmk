#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import os
import io
import itertools
import importlib
import subprocess
from pathlib import Path

import pytest  # type: ignore[import]

from testlib.base import Scenario

import cmk.utils.version as cmk_version
import cmk.utils.paths as paths
from cmk.utils.type_defs import CheckPluginName, ConfigSerial

import cmk.base.core_config as core_config
import cmk.base.core_nagios as core_nagios
import cmk.base.config as config


def test_format_nagios_object():
    spec = {
        "use": "ding",
        "bla": u"däng",
        "check_interval": u"hüch",
        u"_HÄÄÄÄ": "XXXXXX_YYYY",
    }
    cfg = core_nagios._format_nagios_object("service", spec)
    assert isinstance(cfg, str)
    assert cfg == """define service {
  %-29s %s
  %-29s %s
  %-29s %s
  %-29s %s
}

""" % tuple(itertools.chain(*sorted(spec.items(), key=lambda x: x[0])))


@pytest.mark.parametrize("hostname,result", [
    ("localhost", {
        '_ADDRESSES_4': '',
        '_ADDRESSES_6': '',
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        '_FILENAME': '/wato/hosts.mk',
        'address': '127.0.0.1',
        'alias': 'localhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'localhost',
        'hostgroups': 'check_mk',
        'use': 'check_mk_host',
    }),
    ("host2", {
        '_ADDRESSES_4': '',
        '_ADDRESSES_6': '',
        '_ADDRESS_4': '0.0.0.0',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '0.0.0.0',
        'alias': u'lOCALhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'host2',
        'hostgroups': 'check_mk',
        'use': 'check_mk_host',
    }),
    ("cluster1", {
        '_ADDRESSES_4': '',
        '_ADDRESSES_6': '',
        '_ADDRESS_4': '',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_NODEIPS': '',
        '_NODEIPS_4': '',
        '_NODEIPS_6': '',
        '_NODENAMES': '',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '0.0.0.0',
        'alias': 'cluster1',
        'check_command': 'check-mk-host-ping-cluster!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'cluster1',
        'hostgroups': 'check_mk',
        'parents': '',
        'use': 'check_mk_cluster',
    }),
    ("cluster2", {
        '_ADDRESSES_4': '',
        '_ADDRESSES_6': '',
        '_ADDRESS_4': '',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_NODEIPS': '127.0.0.1 127.0.0.2',
        '_NODEIPS_4': '127.0.0.1 127.0.0.2',
        '_NODEIPS_6': '',
        '_NODENAMES': 'node1 node2',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '0.0.0.0',
        'alias': u'CLUSTer',
        'check_command': 'check-mk-host-ping-cluster!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'cluster2',
        'hostgroups': 'check_mk',
        'parents': 'node1,node2',
        'use': 'check_mk_cluster',
    }),
    ("node1", {
        '_ADDRESSES_4': '',
        '_ADDRESSES_6': '',
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '127.0.0.1',
        'alias': 'node1',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'node1',
        'hostgroups': 'check_mk',
        'parents': 'switch',
        'use': 'check_mk_host',
    }),
])
def test_create_nagios_host_spec(hostname, result, monkeypatch):
    if cmk_version.is_managed_edition():
        result = result.copy()
        result['_CUSTOMER'] = 'provider'

    ts = Scenario().add_host("localhost")
    ts.add_host("host2")
    ts.add_cluster("cluster1")

    ts.add_cluster("cluster2", nodes=["node1", "node2"])
    ts.add_host("node1")
    ts.add_host("node2")
    ts.add_host("switch")
    ts.set_option("ipaddresses", {
        "node1": "127.0.0.1",
        "node2": "127.0.0.2",
    })

    ts.set_option("extra_host_conf", {
        "alias": [(u'lOCALhost', ['localhost']),],
    })

    ts.set_option(
        "extra_host_conf", {
            "alias": [
                (u'lOCALhost', ['host2']),
                (u'CLUSTer', ['cluster2']),
            ],
            "parents": [('switch', ['node1', 'node2']),],
        })

    outfile = io.StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])

    config_cache = ts.apply(monkeypatch)
    host_attrs = core_config.get_host_attributes(hostname, config_cache)

    host_spec = core_nagios._create_nagios_host_spec(cfg, config_cache, hostname, host_attrs)
    assert host_spec == result


@pytest.fixture(name="serial")
def fixture_serial() -> ConfigSerial:
    return ConfigSerial("42")


class TestHostCheckStore:
    def test_host_check_file_path(self, serial):
        assert core_nagios.HostCheckStore.host_check_file_path(serial, "abc") == Path(
            paths.make_helper_config_path(serial), "host_checks", "abc")

    def test_host_check_source_file_path(self, serial):
        assert core_nagios.HostCheckStore.host_check_source_file_path(serial, "abc") == Path(
            paths.make_helper_config_path(serial), "host_checks", "abc.py")

    def test_write(self, serial):
        hostname = "aaa"
        store = core_nagios.HostCheckStore()

        assert config.delay_precompile is False

        assert not store.host_check_source_file_path(serial, hostname).exists()
        assert not store.host_check_file_path(serial, hostname).exists()

        store.write(serial, hostname, "xyz")

        assert store.host_check_source_file_path(serial, hostname).exists()
        assert store.host_check_file_path(serial, hostname).exists()

        with store.host_check_source_file_path(serial, hostname).open() as s:
            assert s.read() == "xyz"

        with store.host_check_file_path(serial, hostname).open("rb") as p:
            assert p.read().startswith(importlib.util.MAGIC_NUMBER)

        assert os.access(store.host_check_file_path(serial, hostname), os.X_OK)


def test_dump_precompiled_hostcheck(monkeypatch, serial):
    ts = Scenario().add_host("localhost")
    config_cache = ts.apply(monkeypatch)

    # Ensure a host check is created
    monkeypatch.setattr(
        core_nagios,
        "_get_needed_plugin_names",
        lambda c: (set(), {CheckPluginName("uptime")}, set()),
    )

    host_check = core_nagios._dump_precompiled_hostcheck(config_cache, serial, "localhost")
    assert host_check is not None
    assert host_check.startswith("#!/usr/bin/env python3")


def test_dump_precompiled_hostcheck_without_check_mk_service(monkeypatch, serial):
    ts = Scenario().add_host("localhost")
    config_cache = ts.apply(monkeypatch)
    host_check = core_nagios._dump_precompiled_hostcheck(config_cache, serial, "localhost")
    assert host_check is None


def test_dump_precompiled_hostcheck_not_existing_host(monkeypatch, serial):
    config_cache = Scenario().apply(monkeypatch)
    host_check = core_nagios._dump_precompiled_hostcheck(config_cache, serial, "not-existing")
    assert host_check is None


def test_compile_delayed_host_check(monkeypatch, serial):
    hostname = "localhost"
    ts = Scenario().add_host(hostname)
    ts.set_option("delay_precompile", True)
    config_cache = ts.apply(monkeypatch)

    # Ensure a host check is created
    monkeypatch.setattr(
        core_nagios,
        "_get_needed_plugin_names",
        lambda c: (set(), {CheckPluginName("uptime")}, set()),
    )

    source_file = core_nagios.HostCheckStore.host_check_source_file_path(serial, hostname)
    compiled_file = core_nagios.HostCheckStore.host_check_file_path(serial, hostname)

    assert config.delay_precompile is True
    assert not source_file.exists()
    assert not compiled_file.exists()

    # Write the host check source file
    host_check = core_nagios._dump_precompiled_hostcheck(config_cache,
                                                         serial,
                                                         hostname,
                                                         verify_site_python=False)
    assert host_check is not None
    core_nagios.HostCheckStore().write(serial, hostname, host_check)

    # The compiled file path links to the source file until it has been executed for the first
    # time. Then the symlink is replaced with the compiled file
    assert source_file.exists()
    assert compiled_file.exists()
    assert compiled_file.resolve() == source_file

    # Expect the command to fail: We don't have the correct environment to execute it.
    # But this is no problem for our test, we only want to see the result of the compilation.
    assert subprocess.Popen(["python3", str(compiled_file)], shell=False,
                            close_fds=True).wait() == 1

    assert compiled_file.resolve() != source_file
    with compiled_file.open("rb") as f:
        assert f.read().startswith(importlib.util.MAGIC_NUMBER)
