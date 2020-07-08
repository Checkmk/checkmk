#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.data_sources.piggyback import PiggyBackDataSource
from testlib.base import Scenario


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_attribute_defaults(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = PiggyBackDataSource(hostname, ipaddress)

    assert source.id() == "piggyback"
    assert source.describe().startswith("Process piggyback data from")
    assert source._summary_result(False) == (0, "", [])
