#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from contextlib import suppress

import pytest  # type: ignore[import]
from pyfakefs.fake_filesystem_unittest import patchfs  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.type_defs import SectionName, SourceType

from cmk.snmplib.type_defs import SNMPRawData, SNMPTable

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.abstract import DataSource, FileCache, management_board_ipaddress, store
from cmk.base.data_sources.snmp import SNMPDataSource, SNMPManagementBoardDataSource
from cmk.base.exceptions import MKIPAddressLookupError


@pytest.fixture(autouse=True)
def reset_mutable_global_state():
    def reset(cls, attr, value):
        # Make sure we are not *adding* any field.
        assert hasattr(cls, attr)
        setattr(cls, attr, value)

    def delete(cls, attr):
        with suppress(AttributeError):
            delattr(cls, attr)

    yield
    delete(SNMPDataSource, "_no_cache")
    delete(SNMPDataSource, "_use_outdated_persisted_sections")

    reset(DataSource, "source_type", SourceType.HOST)
    reset(DataSource, "_no_cache", False)
    reset(DataSource, "_may_use_cache_file", False)
    reset(DataSource, "_use_outdated_cache_file", False)
    reset(DataSource, "_use_outdated_persisted_sections", False)

    reset(SNMPDataSource, "source_type", SourceType.HOST)


def test_data_source_cache_default(monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")

    assert not source.is_agent_cache_disabled()


def test_disable_data_source_cache(monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")

    assert not source.is_agent_cache_disabled()

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()


@patchfs
def test_disable_read_to_file_cache(monkeypatch, fs):
    # Beginning of setup.
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.set_may_use_cache_file()

    # Patch I/O: It is good enough to patch `store.save_file()`
    # as pyfakefs takes care of the rest.
    monkeypatch.setattr(store, "save_file",
                        lambda path, contents: fs.create_file(path, contents=contents))

    file_cache = FileCache.from_source(source)
    table = []  # type: SNMPTable
    raw_data = {SectionName("X"): table}  # type: SNMPRawData
    # End of setup.

    assert not source.is_agent_cache_disabled()

    file_cache = FileCache.from_source(source)
    file_cache.write(raw_data)

    assert file_cache.path.exists()
    assert file_cache.read() == raw_data

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()

    file_cache = FileCache.from_source(source)
    assert file_cache.read() is None


@patchfs
def test_disable_write_to_file_cache(monkeypatch, fs):
    # Beginning of setup.
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.set_may_use_cache_file()

    # Patch I/O: It is good enough to patch `store.save_file()`
    # as pyfakefs takes care of the rest.
    monkeypatch.setattr(store, "save_file",
                        lambda path, contents: fs.create_file(path, contents=contents))

    file_cache = FileCache.from_source(source)
    table = []  # type: SNMPTable
    raw_data = {SectionName("X"): table}  # type: SNMPRawData
    # End of setup.

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()

    # Another one bites the dust.
    file_cache = FileCache.from_source(source)
    file_cache.write(raw_data)

    assert not file_cache.path.exists()
    assert file_cache.read() is None


@patchfs
def test_write_and_read_file_cache(monkeypatch, fs):
    # Beginning of setup.
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.set_may_use_cache_file()

    # Patch I/O: It is good enough to patch `store.save_file()`
    # as pyfakefs takes care of the rest.
    monkeypatch.setattr(store, "save_file",
                        lambda path, contents: fs.create_file(path, contents=contents))

    file_cache = FileCache.from_source(source)

    table = []  # type: SNMPTable
    raw_data = {SectionName("X"): table}  # type: SNMPRawData
    # End of setup.

    assert not source.is_agent_cache_disabled()
    assert not file_cache.path.exists()

    file_cache.write(raw_data)

    assert file_cache.path.exists()
    assert file_cache.read() == raw_data

    # Another one bites the dust.
    file_cache = FileCache.from_source(source)
    assert file_cache.read() == raw_data


def test_snmp_ipaddress_from_mgmt_board(monkeypatch):
    hostname = "testhost"
    ipaddress = "1.2.3.4"
    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: ipaddress)
    monkeypatch.setattr(config, "host_attributes", {
        hostname: {
            "management_address": ipaddress
        },
    })

    source = SNMPManagementBoardDataSource(
        hostname,
        management_board_ipaddress(hostname),
    )

    assert source._host_config.management_address == ipaddress
    assert source._ipaddress == ipaddress


def test_snmp_ipaddress_from_mgmt_board_unresolvable(monkeypatch):
    def failed_ip_lookup(h):
        raise MKIPAddressLookupError("Failed to ...")

    Scenario().add_host("hostname").apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", failed_ip_lookup)
    monkeypatch.setattr(config, "host_attributes", {
        "hostname": {
            "management_address": "lolo"
        },
    })
    assert management_board_ipaddress("hostname") is None


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_attribute_defaults(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = SNMPDataSource(hostname, ipaddress)

    assert source._hostname == hostname
    assert source._ipaddress == ipaddress
    assert source.id() == "snmp"
    assert source.title() == "SNMP"
    assert source._cpu_tracking_id() == "snmp"
    assert source.get_do_snmp_scan() is False
    # From the base class
    assert source.name() == ("snmp:%s:%s" % (hostname, ipaddress if ipaddress else ""))
    assert source.is_agent_cache_disabled() is False
    assert source.get_may_use_cache_file() is False
    assert source.exception() is None


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_detector_requires_type_filter_function_and_ipaddress(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = SNMPDataSource(hostname, ipaddress)

    with pytest.raises(Exception):
        source._get_raw_section_names_to_process()

    def dummy_filter_func(sections, on_error, do_snmp_scan, *, binary_host, backend):
        return set()

    source.set_check_plugin_name_filter(dummy_filter_func, inventory=False)
    if ipaddress is None:
        with pytest.raises(NotImplementedError):
            source._get_raw_section_names_to_process()
    else:
        assert source._get_raw_section_names_to_process() == set()


def test_describe_with_ipaddress(monkeypatch):
    hostname = "testhost"
    ipaddress = "127.0.0.1"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = SNMPDataSource(hostname, ipaddress)

    default = "SNMP (Community: 'public', Bulk walk: no, Port: 161, Inline: no)"
    assert source.describe() == default


def test_describe_without_ipaddress_raises_exception(monkeypatch):
    hostname = "testhost"
    ipaddress = None
    Scenario().add_host(hostname).apply(monkeypatch)
    source = SNMPDataSource(hostname, ipaddress)

    # TODO: This does not seem to be the expected exception.
    with pytest.raises(NotImplementedError):
        source.describe()
