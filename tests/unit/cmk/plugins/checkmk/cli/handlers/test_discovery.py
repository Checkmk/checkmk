#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.discovery import CheckDiscoveryRequest, DiscoverRequest
from cmk.plugins.checkmk.cli.handlers.agent_based import PluginSelectionError
from cmk.plugins.checkmk.cli.handlers.discovery import _CheckDiscoveryCommand, _DiscoverCommand
from cmk.plugins.checkmk.cli.options import FetchRequest, FileCacheRequest, PluginSelectionRequest

from ._context import context, OMD_ROOT

_FILE_CACHE = FileCacheRequest(cache=False, no_cache=False, no_tcp=False)


def _check_discovery_request(host: HostAddress) -> CheckDiscoveryRequest:
    return CheckDiscoveryRequest(
        fetch=FetchRequest(file_cache=_FILE_CACHE, usewalk=False, snmp_backend=None, fake_dns=None),
        host=host,
    )


class _FakeCheckDiscovery:
    def __init__(self, result: ActiveCheckResult) -> None:
        self.asked: list[tuple[HostAddress, CheckDiscoveryRequest, Path, bool]] = []
        self._result = result

    def __call__(
        self, host: HostAddress, request: CheckDiscoveryRequest, *, omd_root: Path, debug: bool
    ) -> ActiveCheckResult:
        self.asked.append((host, request, omd_root, debug))
        return self._result


def test_the_discovery_of_the_requested_host_is_checked() -> None:
    check = _FakeCheckDiscovery(ActiveCheckResult(state=0, summary="All services monitored"))

    _CheckDiscoveryCommand(check_discovery=check).run(
        context(), _check_discovery_request(HostAddress("myhost"))
    )

    assert check.asked == [
        (
            HostAddress("myhost"),
            _check_discovery_request(HostAddress("myhost")),
            OMD_ROOT,
            False,
        )
    ]


def test_the_discovery_check_writes_its_result(capsys: pytest.CaptureFixture[str]) -> None:
    check = _FakeCheckDiscovery(ActiveCheckResult(state=0, summary="All services monitored"))

    _CheckDiscoveryCommand(check_discovery=check).run(
        context(), _check_discovery_request(HostAddress("myhost"))
    )

    assert capsys.readouterr().out == "All services monitored\n"


def test_the_discovery_check_exits_with_its_state() -> None:
    check = _FakeCheckDiscovery(ActiveCheckResult(state=1, summary="Unmonitored services"))

    assert (
        _CheckDiscoveryCommand(check_discovery=check).run(
            context(), _check_discovery_request(HostAddress("myhost"))
        )
        == CLIExitCode.FAILURE
    )


_DISCOVER_REQUEST = DiscoverRequest(
    fetch=FetchRequest(file_cache=_FILE_CACHE, usewalk=False, snmp_backend=None, fake_dns=None),
    discover=1,
    plugin_selection=PluginSelectionRequest(
        detect_sections=None, plugins=None, detect_plugins=None
    ),
    only_host_labels=False,
    hosts=("myhost",),
)


class _FakeDiscover:
    def __init__(self, *, succeeded: bool, error: Exception | None = None) -> None:
        self.asked: list[tuple[DiscoverRequest, Path, bool]] = []
        self._succeeded = succeeded
        self._error = error

    def __call__(self, request: DiscoverRequest, *, omd_root: Path, debug: bool) -> bool:
        self.asked.append((request, omd_root, debug))
        if self._error is not None:
            raise self._error
        return self._succeeded


def test_the_requested_hosts_are_discovered() -> None:
    discover = _FakeDiscover(succeeded=True)

    _DiscoverCommand(discover=discover).run(context(), _DISCOVER_REQUEST)

    assert discover.asked == [(_DISCOVER_REQUEST, OMD_ROOT, False)]


def test_a_failed_discovery_exits_one() -> None:
    assert (
        _DiscoverCommand(discover=_FakeDiscover(succeeded=False)).run(context(), _DISCOVER_REQUEST)
        == CLIExitCode.FAILURE
    )


@pytest.mark.parametrize(
    "error",
    [
        MKGeneralException("Cannot load the configuration"),
        PluginSelectionError("Unknown plug-in"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_an_aborted_discovery_exits_three(error: Exception) -> None:
    assert (
        _DiscoverCommand(discover=_FakeDiscover(succeeded=True, error=error)).run(
            context(), _DISCOVER_REQUEST
        )
        == CLIExitCode.UNKNOWN
    )
