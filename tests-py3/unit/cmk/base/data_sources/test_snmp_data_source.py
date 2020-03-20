#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.snmp import SNMPDataSource, SNMPManagementBoardDataSource
from cmk.base.exceptions import MKIPAddressLookupError
from testlib.base import Scenario


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
    assert source._write_cache_file("X") is None
    disabled_checker.assert_called_once()


@pytest.mark.parametrize("result,address,resolvable", [
    (None, None, True),
    ("127.0.0.1", "127.0.0.1", True),
    ("127.0.1.1", "lolo", True),
    (None, "lolo", False),
])
def test_mgmt_board_data_source_management_board_ipaddress(monkeypatch, result, address,
                                                           resolvable):
    Scenario().add_host("hostname").apply(monkeypatch)
    # TODO: Extremely obscure code belwo: The class seems to be abstract??!!
    source = SNMPManagementBoardDataSource("hostname", "ipaddress")  # pylint: disable=abstract-class-instantiated

    if resolvable:
        monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: "127.0.1.1")
    else:

        def raise_exc(h):
            raise MKIPAddressLookupError("Failed to...")

        monkeypatch.setattr(ip_lookup, "lookup_ip_address", raise_exc)

    monkeypatch.setattr(config, "host_attributes", {
        "hostname": {
            "management_address": address
        },
    })

    assert source._management_board_ipaddress("hostname") == result
