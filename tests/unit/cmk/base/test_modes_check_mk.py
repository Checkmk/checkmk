#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from dataclasses import replace
from pathlib import Path

import pytest

import cmk.base.sources._sources as _sources_module
import cmk.ccc.resulttype as result
import cmk.fetchers._snmp as _snmp_module
import cmk.utils.paths as cmk_paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.modes import check_mk
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.version import Edition
from cmk.fetchers import (
    Fetcher,
    FetcherSecrets,
    Mode,
    PiggybackFetcher,
    PlainFetcherTrigger,
)
from cmk.fetchers.snmp import make_backend
from cmk.fetchers.snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend
from cmk.utils.tags import TagGroupID, TagID
from tests.testlib.common.empty_config import EMPTY_CONFIG
from tests.testlib.unit.base_configuration_scenario import Scenario


class _MockFetcherTrigger(PlainFetcherTrigger):
    def __init__(self, payload: bytes) -> None:
        super().__init__(omd_root=Path("/"))
        self._payload = payload

    def _trigger(self, fetcher: Fetcher, mode: Mode, secret: FetcherSecrets) -> result.Result:
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
                config_cache=config.ConfigCache(
                    loaded_config,
                    make_app(Edition.COMMUNITY).get_builtin_host_labels,
                    Edition.COMMUNITY,
                ),
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
    @pytest.mark.usefixtures("patch_config_load")
    def test_success(
        self, hostname: HostName, raw_data: bytes, capsys: pytest.CaptureFixture[str]
    ) -> None:
        app = make_app(Edition.COMMUNITY)
        app.make_fetcher_trigger = lambda *args: _MockFetcherTrigger(raw_data)
        check_mk.mode_dump_agent(app, {}, hostname)
        assert capsys.readouterr().out == raw_data.decode()


class TestModeDumpAgentUseWalk:
    """Test that the --usewalk CLI option causes make_backend to create a
    StoredWalkSNMPBackend.

    mode_dump_agent skips SNMP sources in its source loop (they are only used
    by other modes), so make_backend is never invoked directly by the mode.
    We capture the SNMPSource that make_sources creates and open its fetcher
    manually to drive make_backend and assert the returned backend type.
    """

    @pytest.fixture
    def hostname(self) -> HostName:
        return HostName("snmphost")

    @pytest.fixture
    def ipaddress(self) -> HostAddress:
        return HostAddress("1.2.3.4")

    @pytest.fixture
    def patch_config_load(
        self, monkeypatch: pytest.MonkeyPatch, hostname: HostName, ipaddress: HostAddress
    ) -> None:
        loaded_config = replace(
            EMPTY_CONFIG,
            ipaddresses={hostname: ipaddress},
            host_tags={
                hostname: {
                    TagGroupID("snmp_ds"): TagID("snmp-v2"),
                    TagGroupID("piggyback"): TagID("auto-piggyback"),
                    TagGroupID("networking"): TagID("lan"),
                    TagGroupID("criticality"): TagID("prod"),
                    TagGroupID("site"): TagID("unit"),
                    TagGroupID("address_family"): TagID("ip-v4-only"),
                    TagGroupID("ip-v4"): TagID("ip-v4"),
                }
            },
        )
        monkeypatch.setattr(
            config,
            config.load.__name__,
            lambda *a, **kw: config.LoadingResult(
                loaded_config=loaded_config,
                config_cache=config.ConfigCache(
                    loaded_config,
                    make_app(Edition.COMMUNITY).get_builtin_host_labels,
                    Edition.COMMUNITY,
                ),
            ),
        )

    @pytest.fixture
    def scenario(
        self,
        hostname: HostName,
        ipaddress: HostAddress,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ts = Scenario()
        ts.add_host(hostname, tags={TagGroupID("snmp_ds"): TagID("snmp-v2")})
        ts.set_option("ipaddresses", {hostname: ipaddress})
        ts.apply(monkeypatch)

    @pytest.mark.usefixtures("scenario", "patch_config_load")
    @pytest.mark.parametrize(
        ["options", "expected_backend_type"],
        [
            pytest.param({}, ClassicSNMPBackend, id="default"),
            pytest.param({"usewalk": True}, StoredWalkSNMPBackend, id="walk=True"),
            pytest.param({"usewalk": False}, ClassicSNMPBackend, id="walk=False"),
        ],
    )
    def test_usewalk_creates_expected_backend(
        self,
        hostname: HostName,
        options: dict,
        expected_backend_type: type,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Spy on make_backend to capture the backend it returns
        captured_backends: list = []

        def spy_make_backend(*args, **kwargs):
            backend = make_backend(*args, **kwargs)
            captured_backends.append(backend)
            return backend

        monkeypatch.setattr(_snmp_module, "make_backend", spy_make_backend)

        # Capture the SNMPSource that make_sources creates during mode_dump_agent
        captured_sources: list = []
        original_snmp_source_init = _sources_module.SNMPSource.__init__

        def capturing_snmp_source_init(self, *args, **kwargs):
            original_snmp_source_init(self, *args, **kwargs)
            captured_sources.append(self)

        monkeypatch.setattr(_sources_module.SNMPSource, "__init__", capturing_snmp_source_init)

        app = make_app(Edition.COMMUNITY)
        app.make_fetcher_trigger = lambda *args: _MockFetcherTrigger(b"")
        check_mk.mode_dump_agent(app, options, hostname)

        # Open the SNMP fetcher manually to drive make_backend
        assert len(captured_sources) == 1
        # StoredWalkSNMPBackend requires the walk file to exist; create an empty one
        walk_file = cmk_paths.snmpwalks_dir / str(hostname)
        walk_file.parent.mkdir(parents=True, exist_ok=True)
        walk_file.touch()
        fetcher = captured_sources[0].fetcher()
        fetcher.open()
        try:
            assert len(captured_backends) == 1
            assert isinstance(captured_backends[0], expected_backend_type)
        finally:
            fetcher.close()
