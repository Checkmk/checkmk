#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from tests.testlib.base import Scenario

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.type_defs import HostName, result, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType
from cmk.core_helpers.host_sections import HostSections

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import HostConfig
from cmk.base.sources.agent import AgentRawDataSection
from cmk.base.sources.ipmi import IPMISource


def test_attribute_defaults(monkeypatch) -> None:  # type:ignore[no-untyped-def]
    hostname = HostName("testhost")
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    host_config = HostConfig.make_host_config(hostname)
    ipaddress = config.lookup_mgmt_board_ip_address(host_config)

    source = IPMISource(
        hostname,
        ipaddress,
        source_type=SourceType.MANAGEMENT,
        fetcher_type=FetcherType.IPMI,
        id_="mgmt_ipmi",
        persisted_section_dir=Path(os.devnull),
        cache_dir=Path(os.devnull),
        keep_outdated=False,
        simulation_mode=True,
        agent_simulator=True,
        translation={},
        encoding_fallback="ascii",
        check_interval=0,
        management_credentials={},
        file_cache_max_age=file_cache.MaxAge.none(),
    )
    assert source.source_type is SourceType.MANAGEMENT
    assert source.summarize(
        result.OK(HostSections[AgentRawDataSection]()),
        exit_spec_cb=host_config.exit_code_spec,
    ) == [ActiveCheckResult(0, "Success")]
    assert source.id == "mgmt_ipmi"


def test_ipmi_ipaddress_from_mgmt_board(monkeypatch) -> None:  # type:ignore[no-untyped-def]
    hostname = HostName("testhost")
    ipaddress = "127.0.0.1"

    def fake_lookup_ip_address(host_config, *, family, for_mgmt_board=True):
        return ipaddress

    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(
        config,
        "host_attributes",
        {
            hostname: {"management_address": ipaddress},
        },
    )

    host_config = HostConfig.make_host_config(hostname)
    assert host_config.management_address == ipaddress
