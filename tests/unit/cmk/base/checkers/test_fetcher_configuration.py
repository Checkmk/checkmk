#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.fetchers import FetcherType

from cmk.base.checkers import fetcher_configuration


def make_scenario(hostname, tags):
    return Scenario().add_host(hostname, tags=tags)


@pytest.fixture(name="file")
def file_fixture():
    return io.StringIO()


@pytest.mark.parametrize("hostname, tags, fetchers", [
    ("agent-host", {}, [FetcherType.TCP, FetcherType.PIGGYBACK]),
    (
        "ping-host",
        {
            "agent": "no-agent"
        },
        [FetcherType.PIGGYBACK],
    ),
    (
        "snmp-host",
        {
            "agent": "no-agent",
            "snmp_ds": "snmp-v2"
        },
        [FetcherType.SNMP, FetcherType.PIGGYBACK],
    ),
    (
        "dual-host",
        {
            "agent": "cmk-agent",
            "snmp_ds": "snmp-v2"
        },
        [FetcherType.TCP, FetcherType.SNMP, FetcherType.PIGGYBACK],
    ),
    (
        "all-agents-host",
        {
            "agent": "all-agents"
        },
        [FetcherType.TCP, FetcherType.PIGGYBACK],
    ),
    (
        "all-special-host",
        {
            "agent": "special-agents"
        },
        [FetcherType.PIGGYBACK],
    ),
])
def test_generates_correct_sections(file, hostname, tags, fetchers, monkeypatch):
    make_scenario(hostname, tags).apply(monkeypatch)
    fetcher_configuration.dump(hostname, "1.2.3.4", file)
    file.seek(0)
    assert [FetcherType[f["fetcher_type"]] for f in json.load(file)["fetchers"]] == fetchers
