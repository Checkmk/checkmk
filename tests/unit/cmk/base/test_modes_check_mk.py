#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostName

from cmk.fetchers import PiggybackFetcher

from cmk.base.modes import check_mk


class TestModeDumpAgent:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def ipaddress(self):
        return "1.2.3.4"

    @pytest.fixture
    def raw_data(self, hostname):
        return b"<<<check_mk>>>\nraw data"

    @pytest.fixture
    def patch_fetch(self, raw_data, monkeypatch):
        monkeypatch.setattr(
            check_mk,
            "get_raw_data",
            lambda _file_cache, fetcher, _mode: (
                result.OK(b"") if isinstance(fetcher, PiggybackFetcher) else result.OK(raw_data)
            ),
        )

    @pytest.fixture
    def scenario(self, hostname, ipaddress, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("ipaddresses", {hostname: ipaddress})
        ts.apply(monkeypatch)
        return ts

    @pytest.mark.usefixtures("scenario")
    @pytest.mark.usefixtures("patch_fetch")
    def test_success(
        self, hostname: HostName, raw_data: bytes, capsys: pytest.CaptureFixture[str]
    ) -> None:
        check_mk.mode_dump_agent({}, hostname)
        assert capsys.readouterr().out == raw_data.decode()
