#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest

from tests.testlib.base import Scenario

from cmk.utils.exceptions import MKIPAddressLookupError
from cmk.utils.type_defs import CheckPluginName, HostName, ParsedSectionName

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.api.agent_based.checking_classes import CheckPlugin


def test_snmp_ipaddress_from_mgmt_board_unresolvable(  # type:ignore[no-untyped-def]
    monkeypatch,
) -> None:
    def fake_lookup_ip_address(*_a, **_kw):
        raise MKIPAddressLookupError("Failed to ...")

    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(
        config,
        "host_attributes",
        {
            "hostname": {"management_address": "lolo"},
        },
    )

    host_config = config.get_config_cache().get_host_config(hostname)
    assert config.lookup_mgmt_board_ip_address(host_config) is None


@pytest.fixture(name="check_plugin")
def fixture_check_plugin():
    return CheckPlugin(
        CheckPluginName("unit_test_check_plugin"),
        [ParsedSectionName("norris")],
        "Unit Test",
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,
        None,
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,
        None,
        None,
        None,
    )
