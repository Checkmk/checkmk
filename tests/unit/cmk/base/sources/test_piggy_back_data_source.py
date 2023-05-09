#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.type_defs import HostAddress, HostName, result

from cmk.core_helpers.agent import AgentRawDataSection
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.type_defs import Mode

from cmk.base.sources.piggyback import PiggybackSource


@pytest.fixture(name="mode", params=(mode for mode in Mode if mode is not Mode.NONE))
def mode_fixture(request):
    return request.param


@pytest.mark.parametrize("ipaddress", [None, HostAddress("127.0.0.1")])
def test_attribute_defaults(monkeypatch: MonkeyPatch, ipaddress: HostAddress, mode: Mode) -> None:
    hostname = HostName("testhost")
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    source = PiggybackSource(hostname, ipaddress)
    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.description.startswith("Process piggyback data from")
    assert not source.summarize(result.OK(HostSections[AgentRawDataSection]()), mode=mode)
    assert source.id == "piggyback"
