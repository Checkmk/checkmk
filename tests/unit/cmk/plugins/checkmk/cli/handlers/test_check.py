#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.specs.checkresults import ServiceState
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.check import CheckingRequest
from cmk.plugins.checkmk.cli.handlers.agent_based import PluginSelectionError
from cmk.plugins.checkmk.cli.handlers.check import _CheckCommand
from cmk.plugins.checkmk.cli.options import FetchRequest, FileCacheRequest, PluginSelectionRequest

from ._context import context, OMD_ROOT


class _FakeCheckHost:
    def __init__(self, state: ServiceState = 0, error: Exception | None = None) -> None:
        self.checked: list[tuple[HostName, CheckingRequest, Path, bool]] = []
        self._state = state
        self._error = error

    def __call__(
        self, host: HostName, request: CheckingRequest, *, omd_root: Path, debug: bool
    ) -> ServiceState:
        self.checked.append((host, request, omd_root, debug))
        if self._error is not None:
            raise self._error
        return self._state


def _request() -> CheckingRequest:
    return CheckingRequest(
        fetch=FetchRequest(
            file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=False),
            usewalk=False,
            snmp_backend=None,
            fake_dns=None,
        ),
        no_submit=False,
        perfdata=False,
        plugin_selection=PluginSelectionRequest(
            detect_sections=None, plugins=None, detect_plugins=None
        ),
        host=HostName("myhost"),
        address=None,
    )


def test_the_requested_host_is_checked() -> None:
    check_host = _FakeCheckHost()

    _CheckCommand(check_host=check_host).run(context(), _request())

    assert check_host.checked == [(HostName("myhost"), _request(), OMD_ROOT, False)]


@pytest.mark.parametrize(
    ["state", "expected"],
    [
        (0, CLIExitCode.SUCCESS),
        (1, CLIExitCode.FAILURE),
        (2, CLIExitCode.ERROR),
        (3, CLIExitCode.UNKNOWN),
        (4, CLIExitCode.UNKNOWN),
        (-1, CLIExitCode.UNKNOWN),
        (127, CLIExitCode.UNKNOWN),
    ],
)
def test_the_check_exits_with_the_monitoring_meaning_of_the_hosts_state(
    state: int, expected: CLIExitCode
) -> None:
    check_host = _FakeCheckHost(state=state)

    assert _CheckCommand(check_host=check_host).run(context(), _request()) == expected


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(MKGeneralException("Unknown host"), id="unknown-host"),
        pytest.param(PluginSelectionError("Unknown plug-in"), id="unknown-plugin"),
    ],
)
def test_a_failed_check_exits_three(error: Exception) -> None:
    check_host = _FakeCheckHost(error=error)

    assert _CheckCommand(check_host=check_host).run(context(), _request()) == CLIExitCode.UNKNOWN
