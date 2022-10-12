#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import os
from pathlib import Path

import pytest

from tests.testlib.base import Scenario

from cmk.utils.exceptions import MKIPAddressLookupError, OnError
from cmk.utils.type_defs import CheckPluginName, HostName, ParsedSectionName, SourceType

from cmk.snmplib.type_defs import SNMPBackendEnum, SNMPHostConfig

from cmk.core_helpers import FetcherType
from cmk.core_helpers.cache import FileCacheMode, MaxAge
from cmk.core_helpers.snmp import SNMPFileCache

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.sources.snmp import SNMPSource


@pytest.fixture(name="source")
def source_fixture():
    hostname = HostName("hostname")
    return SNMPSource(
        hostname,
        "1.2.3.4",
        source_type=SourceType.HOST,
        fetcher_type=FetcherType.SNMP,
        id_="snmp",
        persisted_section_dir=Path(os.devnull),
        on_scan_error=OnError.RAISE,
        missing_sys_description=False,
        sections={},
        keep_outdated=False,
        snmp_config=SNMPHostConfig(
            hostname=hostname,
            ipaddress="1.2.3.4",
            is_ipv6_primary=False,
            credentials=(),
            port=0,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=0,
            timing={},
            oid_range_limits={},
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend=SNMPBackendEnum.CLASSIC,
        ),
        do_status_data_inventory=False,
        cache=SNMPFileCache(
            hostname=hostname,
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=True,
            use_only_cache=True,
            file_cache_mode=FileCacheMode.DISABLED,
        ),
    )


def test_snmp_ipaddress_from_mgmt_board_unresolvable(  # type:ignore[no-untyped-def]
    monkeypatch,
) -> None:
    def fake_lookup_ip_address(*_a, **_kw):
        raise MKIPAddressLookupError("Failed to ...")

    hostname = "hostname"
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
