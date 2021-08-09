#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.type_defs import result

from cmk.core_helpers.agent import AgentHostSections
from cmk.core_helpers.type_defs import Mode

from cmk.base.sources.piggyback import PiggybackSource


@pytest.fixture(name="mode", params=(mode for mode in Mode if mode is not Mode.NONE))
def mode_fixture(request):
    return request.param


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_attribute_defaults(monkeypatch, ipaddress, mode):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)

    source = PiggybackSource(hostname, ipaddress)
    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.description.startswith("Process piggyback data from")
    assert source.summarize(result.OK(AgentHostSections()), mode=mode) == (0, "")
    assert source.id == "piggyback"
