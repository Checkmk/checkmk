#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.exceptions import MKIPAddressLookupError
from cmk.utils.hostaddress import HostName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.sectionparser import ParsedSectionName

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.api.agent_based.checking_classes import CheckPlugin


def test_snmp_ipaddress_from_mgmt_board_unresolvable(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_lookup_ip_address(*_a, **_kw):
        raise MKIPAddressLookupError("Failed to ...")

    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(
        config,
        "host_attributes",
        {
            "hostname": {"management_address": "lolo"},
        },
    )

    assert config.lookup_mgmt_board_ip_address(config_cache, hostname) is None


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
