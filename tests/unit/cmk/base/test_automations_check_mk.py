#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.type_defs import result

from cmk.automations.results import DiagHostResult

import cmk.base.automations.check_mk as check_mk
from cmk.base.sources.tcp import TCPSource


class TestAutomationDiagHost:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def ipaddress(self):
        return "1.2.3.4"

    @pytest.fixture
    def raw_data(self):
        return "<<<check_mk>>>\nraw data"

    @pytest.fixture
    def scenario(self, hostname, ipaddress, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("ipaddresses", {hostname: ipaddress})
        ts.apply(monkeypatch)
        return ts

    @pytest.fixture
    def patch_fetch(self, raw_data, monkeypatch):
        monkeypatch.setattr(TCPSource, "fetch", lambda self, mode: result.OK(raw_data))

    @pytest.mark.usefixtures("scenario")
    @pytest.mark.usefixtures("patch_fetch")
    def test_execute(self, hostname, ipaddress, raw_data):
        args = [hostname, "agent", ipaddress, "", "6557", "10", "5", "5", ""]
        assert check_mk.AutomationDiagHost().execute(args) == DiagHostResult(
            0,
            raw_data,
        )
