#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.snmp as snmp
import cmk.base.snmp_utils as snmp_utils
from cmk.base.api.agent_based.section_types import (
    SNMPTree,
    OIDEnd,
)
from cmk.base.data_sources.snmp import SNMPDataSource, SNMPManagementBoardDataSource
from cmk.base.exceptions import MKIPAddressLookupError
from cmk.base.snmp_utils import SNMPTable
from testlib.base import Scenario


def test_data_source_cache_default(monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")

    assert source.is_agent_cache_disabled() is False


def test_disable_data_source_cache(monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")

    assert source.is_agent_cache_disabled() is False

    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled() is True


def test_disable_data_source_cache_no_read(mocker, monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.disable_data_source_cache()

    mocker.patch.object(os.path, "exists", return_value=True)

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._read_cache_file() is None
    disabled_checker.assert_called_once()


def test_disable_data_source_cache_no_write(mocker, monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = SNMPDataSource("hostname", "ipaddress")
    source.disable_data_source_cache()

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    table = []  # type: SNMPTable
    source._write_cache_file({"X": table})
    disabled_checker.assert_called_once()


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

    source = SNMPManagementBoardDataSource(hostname, "unused")

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
    source = SNMPManagementBoardDataSource("hostname", "ipaddress")

    assert source._ipaddress is None


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
    assert source.is_agent_cache_disabled() is True
    assert source.get_may_use_cache_file() is False
    assert source.exception() is None


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_get_check_plugin_names_requires_type_filter_function_and_ipaddress(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = SNMPDataSource(hostname, ipaddress)

    with pytest.raises(Exception):
        source.get_check_plugin_names()

    # One filter function is defined in cmk.base.inventory and another one in snmp_scan.
    def dummy_filter_func(host_config, on_error, do_snmp_scan, for_mgmt_board=False):
        return set()

    source.set_check_plugin_name_filter(dummy_filter_func)
    if ipaddress is None:
        with pytest.raises(NotImplementedError):
            source.get_check_plugin_names()
    else:
        assert source.get_check_plugin_names() == set()


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


def test_execute_with_canned_responses(monkeypatch):
    # Beginning of setup.
    tree = SNMPTree(
        base='.1.3.6.1.4.1.13595.2.2.3.1',
        oids=[
            OIDEnd(),
            snmp_utils.OIDBytes("16"),
        ],
    )
    name = "acme_agent_sessions"  # Must be in config.registered_snmp_sections

    # Replace I/O with canned responses.
    monkeypatch.setattr(SNMPDataSource, "get_check_plugin_names", lambda *args, **kwargs: {name})
    monkeypatch.setattr(snmp, "get_snmp_table_cached", lambda *args: tree)

    hostname = "testhost"
    ipaddress = "127.0.0.1"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = SNMPDataSource(hostname, ipaddress)
    # End of setup.

    assert source._execute() == {name: [tree]}
