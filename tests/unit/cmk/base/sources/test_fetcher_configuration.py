#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.core_helpers import FetcherType

import cmk.base.config as config
from cmk.base.sources import fetcher_configuration


def make_scenario(hostname, tags) -> Scenario:
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    return ts


@pytest.mark.parametrize(
    "hostname, tags, fetchers",
    [
        ("agent-host", {}, [FetcherType.TCP, FetcherType.PIGGYBACK]),
        (
            "ping-host",
            {"agent": "no-agent"},
            [FetcherType.PIGGYBACK],
        ),
        (
            "snmp-host",
            {"agent": "no-agent", "snmp_ds": "snmp-v2"},
            [FetcherType.SNMP, FetcherType.PIGGYBACK],
        ),
        (
            "dual-host",
            {"agent": "cmk-agent", "snmp_ds": "snmp-v2"},
            [FetcherType.TCP, FetcherType.SNMP, FetcherType.PIGGYBACK],
        ),
        (
            "all-agents-host",
            {"agent": "all-agents"},
            [FetcherType.TCP, FetcherType.PIGGYBACK],
        ),
        (
            "all-special-host",
            {"agent": "special-agents"},
            [FetcherType.PIGGYBACK],
        ),
    ],
)
def test_generates_correct_sections(hostname, tags, fetchers, monkeypatch, fixup_ip_lookup) -> None:
    make_scenario(hostname, tags).apply(monkeypatch)
    conf = fetcher_configuration.fetchers(config.HostConfig.make_host_config(hostname))
    assert [FetcherType[f["fetcher_type"]] for f in conf["fetchers"]] == fetchers
