#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

import logging
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from typing import Any, Final, NoReturn, override

import pytest

import cmk.ccc.resulttype as result
import cmk.checkengine.fetchers.snmp._fetcher as _snmp_module
import cmk.utils.paths as cmk_paths
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.version import Edition
from cmk.checkengine.fetcher_abc import Fetcher, Mode
from cmk.checkengine.fetcher_utils.secrets import FetcherSecrets
from cmk.checkengine.fetcher_utils.trigger import PlainFetcherTrigger
from cmk.checkengine.fetchers.piggyback import PiggybackFetcher
from cmk.checkengine.snmp_backend_builder import make_backend
from cmk.checkengine.snmp_backends.classic import ClassicSNMPBackend
from cmk.checkengine.snmp_backends.stored_walk import StoredWalkSNMPBackend
from cmk.checkengine.sources._sources import SNMPSource
from cmk.cli.engine.call import call
from cmk.cli.engine.commands import make_command
from cmk.cli.internal import CommandContext as CLICommandContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Options
from cmk.plugins.checkmk.cli import dump
from cmk.plugins.checkmk.cli.dump import cli_command_dump_agent
from cmk.ruleset_matcher.tags import TagGroupID, TagID
from tests.testlib.unit.base_configuration_scenario import Scenario
from tests.testlib.unit.empty_config import EMPTY_CONFIG


class _MockFetcherTrigger(PlainFetcherTrigger):
    def __init__(self, fetched: bytes | Exception) -> None:
        super().__init__(omd_root=Path("/"))
        self._fetched = fetched

    @override
    def _trigger(self, fetcher: Fetcher, mode: Mode, secret: FetcherSecrets) -> result.Result:
        if isinstance(fetcher, PiggybackFetcher):
            return result.OK(b"")
        if isinstance(self._fetched, Exception):
            return result.Error(self._fetched)
        return result.OK(self._fetched)


_OMD_ROOT: Final = Path("/omd/sites/mysite")


def _patch_fetcher_trigger(monkeypatch: pytest.MonkeyPatch, fetched: bytes | Exception) -> None:
    """Make the command build an application that fetches the given data.

    The command builds its own application, so the fake has to go in where it
    does that.
    """

    def _not_called(*_a: object) -> NoReturn:
        raise AssertionError("call not expected here")

    monkeypatch.setattr(
        dump,
        "make_app",
        lambda _omd_root: CheckmkBaseApp(
            edition=Edition.COMMUNITY,
            create_core=_not_called,
            licensing_handler_factory=_not_called,
            make_fetcher_trigger=lambda *_a: _MockFetcherTrigger(fetched),
        ),
    )


class TestDumpAgent:
    @pytest.fixture
    def hostname(self) -> HostName:
        return HostName("testhost")

    @pytest.fixture
    def ipaddress(self) -> HostAddress:
        return HostAddress("1.2.3.4")

    @pytest.fixture
    def raw_data(self, hostname: HostName) -> bytes:  # noqa: ARG002
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
            lambda *a, **kw: config.LoadingResult(  # noqa: ARG005
                loaded_config=loaded_config,
                hosts_config=config.make_hosts_config(loaded_config),
                host_tags=config.make_host_tags(
                    loaded_config, config.make_hosts_config(loaded_config)
                ),
                config_cache=config.ConfigCache(
                    loaded_config,
                    config.make_hosts_config(loaded_config),
                    config.make_host_tags(loaded_config, config.make_hosts_config(loaded_config)),
                    autochecks_dir=cmk_paths.autochecks_dir,
                    discovered_host_labels_dir=cmk_paths.discovered_host_labels_dir,
                    builtin_host_labels_file=cmk_paths.builtin_host_labels_file,
                    debug=False,
                ),
            ),
        )

    @pytest.fixture
    def scenario(
        self, hostname: HostName, ipaddress: HostAddress, monkeypatch: pytest.MonkeyPatch
    ) -> Scenario:
        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("ipaddresses", {hostname: ipaddress})
        ts.apply(monkeypatch)
        return ts

    @pytest.mark.usefixtures("scenario")
    @pytest.mark.usefixtures("patch_config_load")
    def test_success(
        self,
        hostname: HostName,
        raw_data: bytes,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_fetcher_trigger(monkeypatch, raw_data)

        call(
            CLICommandContext(
                omd_root=_OMD_ROOT,
                global_options=CLIGlobalOptions(),
                logger=logging.getLogger(__name__),
            ),
            make_command(cli_command_dump_agent),
            hostname,
            {},
            [],
            lambda *_args: nullcontext(),
        )

        assert capsys.readouterr().out == raw_data.decode()

    @pytest.mark.usefixtures("scenario")
    @pytest.mark.usefixtures("patch_config_load")
    def test_agent_warning_does_not_fail(
        self,
        hostname: HostName,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_fetcher_trigger(
            monkeypatch,
            b"<<<check_mk>>>\nraw data\n"
            b"<<<<>>>>\n<<<cmk_agent_messages:sep(0)>>>\n"
            b'{"level": "warning", "message": "Section foo denied"}\n',
        )

        exit_code = call(
            CLICommandContext(
                omd_root=_OMD_ROOT,
                global_options=CLIGlobalOptions(),
                logger=logging.getLogger(__name__),
            ),
            make_command(cli_command_dump_agent),
            hostname,
            {},
            [],
            lambda *_args: nullcontext(),
        )

        assert exit_code == CLIExitCode.SUCCESS
        assert capsys.readouterr().err == "WARNING [agent]: Success, Section foo denied\n"

    @pytest.mark.usefixtures("scenario")
    @pytest.mark.usefixtures("patch_config_load")
    def test_unknown_fetch_failure_fails(
        self,
        hostname: HostName,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_fetcher_trigger(monkeypatch, Exception("Something broke"))

        exit_code = call(
            CLICommandContext(
                omd_root=_OMD_ROOT,
                global_options=CLIGlobalOptions(),
                logger=logging.getLogger(__name__),
            ),
            make_command(cli_command_dump_agent),
            hostname,
            {},
            [],
            lambda *_args: nullcontext(),
        )

        assert exit_code == CLIExitCode.FAILURE
        assert capsys.readouterr().err == "ERROR [agent]: Something broke\n"


class TestDumpAgentSnmpBackend:
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
            lambda *a, **kw: config.LoadingResult(  # noqa: ARG005
                loaded_config=loaded_config,
                hosts_config=config.make_hosts_config(loaded_config),
                host_tags=config.make_host_tags(
                    loaded_config, config.make_hosts_config(loaded_config)
                ),
                config_cache=config.ConfigCache(
                    loaded_config,
                    config.make_hosts_config(loaded_config),
                    config.make_host_tags(loaded_config, config.make_hosts_config(loaded_config)),
                    autochecks_dir=cmk_paths.autochecks_dir,
                    discovered_host_labels_dir=cmk_paths.discovered_host_labels_dir,
                    builtin_host_labels_file=cmk_paths.builtin_host_labels_file,
                    debug=False,
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
            pytest.param({"snmp-backend": "stored-walk"}, StoredWalkSNMPBackend, id="stored-walk"),
        ],
    )
    def test_the_snmp_backend_option_selects_the_backend(
        self,
        hostname: HostName,
        options: Options,
        expected_backend_type: type,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Spy on make_backend to capture the backend it returns
        captured_backends: list = []

        def spy_make_backend(*args: Any, **kwargs: Any) -> object:
            backend = make_backend(*args, **kwargs)
            captured_backends.append(backend)
            return backend

        monkeypatch.setattr(_snmp_module, "make_backend", spy_make_backend)

        # Capture the SNMPSource that make_sources creates during mode_dump_agent
        captured_sources: list = []
        original_snmp_source_init = SNMPSource.__init__

        def capturing_snmp_source_init(self: SNMPSource, *args: Any, **kwargs: Any) -> None:
            original_snmp_source_init(self, *args, **kwargs)
            captured_sources.append(self)

        monkeypatch.setattr(SNMPSource, "__init__", capturing_snmp_source_init)

        _patch_fetcher_trigger(monkeypatch, b"")
        call(
            CLICommandContext(
                omd_root=_OMD_ROOT,
                global_options=CLIGlobalOptions(),
                logger=logging.getLogger(__name__),
            ),
            make_command(cli_command_dump_agent),
            hostname,
            options,
            [],
            lambda *_args: nullcontext(),
        )

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
