#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]
from pyfakefs.fake_filesystem_unittest import patchfs  # type: ignore[import]

# No stub
from testlib.base import Scenario  # type: ignore[import]

import cmk.utils.store as store
from cmk.utils.type_defs import SectionName, SourceType

from cmk.snmplib.type_defs import SNMPRawData, SNMPTable

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources import Mode
from cmk.base.data_sources.agent import AgentHostSections
from cmk.base.data_sources.snmp import SNMPConfigurator, SNMPDataSource
from cmk.base.exceptions import MKIPAddressLookupError


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


@pytest.fixture(name="hostname")
def hostname_fixture():
    return "hostname"


@pytest.fixture(name="ipaddress")
def ipaddress_fixture():
    return "1.2.3.4"


@pytest.fixture(name="source")
def source_fixture(hostname, ipaddress, mode, monkeypatch):
    Scenario().add_host(hostname).apply(monkeypatch)
    return SNMPDataSource(configurator=SNMPConfigurator.snmp(
        hostname,
        ipaddress,
        mode=mode,
    ),)


def test_data_source_cache_default(source):
    assert not source.is_agent_cache_disabled()


def test_disable_data_source_cache(source):
    assert not source.is_agent_cache_disabled()

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()


@patchfs
def test_disable_read_to_file_cache(source, monkeypatch, fs):
    # Beginning of setup.
    source.set_max_cachefile_age(999)
    source.set_may_use_cache_file()

    # Patch I/O: It is good enough to patch `store.save_file()`
    # as pyfakefs takes care of the rest.
    monkeypatch.setattr(
        store,
        "save_file",
        lambda path, contents: fs.create_file(path, contents=contents),
    )

    table: SNMPTable = []
    raw_data: SNMPRawData = {SectionName("X"): table}
    # End of setup.

    assert not source.is_agent_cache_disabled()

    source._file_cache.write(raw_data)

    assert source._file_cache.path.exists()
    assert source._file_cache.read() == raw_data

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()

    assert source._file_cache.read() is None


@patchfs
def test_disable_write_to_file_cache(source, monkeypatch, fs):
    # Beginning of setup.
    source.set_max_cachefile_age(999)
    source.set_may_use_cache_file()

    # Patch I/O: It is good enough to patch `store.save_file()`
    # as pyfakefs takes care of the rest.
    monkeypatch.setattr(
        store,
        "save_file",
        lambda path, contents: fs.create_file(path, contents=contents),
    )

    table: SNMPTable = []
    raw_data: SNMPRawData = {SectionName("X"): table}
    # End of setup.

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()

    # Another one bites the dust.
    source._file_cache.write(raw_data)

    assert not source._file_cache.path.exists()
    assert source._file_cache.read() is None


@patchfs
def test_write_and_read_file_cache(source, monkeypatch, fs):
    # Beginning of setup.
    source.set_max_cachefile_age(999)
    source.set_may_use_cache_file()

    # Patch I/O: It is good enough to patch `store.save_file()`
    # as pyfakefs takes care of the rest.
    monkeypatch.setattr(
        store,
        "save_file",
        lambda path, contents: fs.create_file(path, contents=contents),
    )

    table: SNMPTable = []
    raw_data: SNMPRawData = {SectionName("X"): table}
    # End of setup.

    assert not source.is_agent_cache_disabled()
    assert not source._file_cache.path.exists()

    source._file_cache.write(raw_data)

    assert source._file_cache.path.exists()
    assert source._file_cache.read() == raw_data

    # Another one bites the dust.
    assert source._file_cache.read() == raw_data


def test_snmp_ipaddress_from_mgmt_board_unresolvable(hostname, monkeypatch):
    def fake_lookup_ip_address(host_config, family=None, for_mgmt_board=True):
        raise MKIPAddressLookupError("Failed to ...")

    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(config, "host_attributes", {
        "hostname": {
            "management_address": "lolo"
        },
    })
    host_config = config.get_config_cache().get_host_config(hostname)
    assert ip_lookup.lookup_mgmt_board_ip_address(host_config) is None


def test_attribute_defaults(source, hostname, ipaddress, monkeypatch):
    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.id == "snmp"
    assert source._cpu_tracking_id == "snmp"

    configurator = source.configurator
    assert configurator.hostname == hostname
    assert configurator.ipaddress == ipaddress
    assert configurator.id == "snmp"
    assert configurator.cpu_tracking_id == "snmp"

    assert configurator.on_snmp_scan_error == "raise"
    assert configurator.do_snmp_scan is False

    # From the base class
    assert source.is_agent_cache_disabled() is False
    assert source.get_may_use_cache_file() is False
    assert source.exception() is None


def test_source_requires_ipaddress(hostname, mode, monkeypatch):
    Scenario().add_host(hostname).apply(monkeypatch)
    with pytest.raises(TypeError):
        SNMPConfigurator.snmp(hostname, None, mode=mode)


def test_description_with_ipaddress(source, monkeypatch):
    default = "SNMP (Community: 'public', Bulk walk: no, Port: 161, Inline: no)"
    assert source.description == default


class TestSNMPConfigurator_SNMP:
    def test_attribute_defaults(self, mode, monkeypatch):
        hostname = "testhost"
        ipaddress = "1.2.3.4"

        Scenario().add_host(hostname).apply(monkeypatch)

        configurator = SNMPConfigurator.snmp(hostname, ipaddress, mode=mode)
        assert configurator.description == (
            "SNMP (Community: 'public', Bulk walk: no, Port: 161, Inline: no)")


class TestSNMPConfigurator_MGMT:
    def test_attribute_defaults(self, mode, monkeypatch):
        hostname = "testhost"
        ipaddress = "1.2.3.4"

        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("management_protocol", {hostname: "snmp"})
        ts.set_option(
            "host_attributes",
            {
                hostname: {
                    "management_address": ipaddress
                },
            },
        )
        ts.apply(monkeypatch)

        configurator = SNMPConfigurator.management_board(
            hostname,
            ipaddress,
            mode=mode,
        )
        assert configurator.description == (
            "Management board - SNMP "
            "(Community: 'public', Bulk walk: no, Port: 161, Inline: no)")


class TestSNMPSummaryResult:
    @pytest.fixture(params=(mode for mode in Mode if mode is not Mode.NONE))
    def mode(self, request):
        return request.param

    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def scenario(self, hostname, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)
        return ts

    @pytest.fixture
    def source(self, hostname, mode):
        return SNMPDataSource(configurator=SNMPConfigurator(
            hostname,
            "1.2.3.4",
            mode=mode,
            source_type=SourceType.HOST,
            id_="snmp_id",
            cpu_tracking_id="snmp_cpu_id",
            title="snmp title",
        ))

    @pytest.mark.usefixtures("scenario")
    def test_defaults(self, source):
        summarizer = source.summarizer
        assert summarizer.summarize(AgentHostSections()) == (0, "Success", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_exception(self, source):
        source._exception = Exception()
        assert source.exception()

        assert source.get_summary_result() == (3, "(?)", [])
