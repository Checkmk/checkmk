#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import replace

import pytest

import cmk.ccc.resulttype as result
from cmk.base import config
from cmk.base.modes import check_mk
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.fetchers import Fetcher, FetcherTrigger, Mode, PiggybackFetcher
from cmk.utils.tags import TagGroupID, TagID
from tests.testlib.unit.base_configuration_scenario import Scenario
from tests.unit.cmk.base.empty_config import EMPTY_CONFIG


class _MockFetcherTrigger(FetcherTrigger):
    def __init__(self, payload: bytes) -> None:
        super().__init__()
        self._payload = payload

    def _trigger(self, fetcher: Fetcher, mode: Mode) -> result.Result:
        if isinstance(fetcher, PiggybackFetcher):
            return result.OK(b"")
        return result.OK(self._payload)


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
    def patch_config_load(
        self, monkeypatch: pytest.MonkeyPatch, hostname: HostName, ipaddress: HostAddress
    ) -> None:
        loaded_config = replace(
            EMPTY_CONFIG,
            ipaddresses={hostname: ipaddress},
            host_tags={
                hostname: {
                    TagGroupID("checkmk-agent"): TagID("checkmk-agent"),
                    TagGroupID("piggyback"): TagID("auto-piggyback"),
                    TagGroupID("networking"): TagID("lan"),
                    TagGroupID("agent"): TagID("cmk-agent"),
                    TagGroupID("criticality"): TagID("prod"),
                    TagGroupID("snmp_ds"): TagID("no-snmp"),
                    TagGroupID("site"): TagID("unit"),
                    TagGroupID("address_family"): TagID("ip-v4-only"),
                    TagGroupID("tcp"): TagID("tcp"),
                    TagGroupID("ip-v4"): TagID("ip-v4"),
                }
            },
        )
        monkeypatch.setattr(
            config,
            config.load.__name__,
            lambda *a, **kw: config.LoadingResult(
                loaded_config=loaded_config,
                config_cache=config.ConfigCache(loaded_config),
            ),
        )

    @pytest.fixture
    def patch_fetch(self, raw_data, monkeypatch):
        monkeypatch.setattr(
            check_mk.config,  # type: ignore[attr-defined]
            "make_fetcher_trigger",
            lambda *args: _MockFetcherTrigger(raw_data),
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
    @pytest.mark.usefixtures("patch_config_load")
    def test_success(
        self, hostname: HostName, raw_data: bytes, capsys: pytest.CaptureFixture[str]
    ) -> None:
        check_mk.mode_dump_agent({}, hostname)
        assert capsys.readouterr().out == raw_data.decode()
