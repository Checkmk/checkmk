#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.specs.checkresults import ServiceState
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.check import CheckingRequest
from cmk.plugins.checkmk.cli.handlers.check import _CheckCommand
from cmk.plugins.checkmk.cli.options import FileCacheRequest, PluginSelectionRequest

_OMD_ROOT = Path("/omd/sites/mysite")


class _FakeCheckHost:
    def __init__(self, state: ServiceState = 0, error: MKGeneralException | None = None) -> None:
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


def _context() -> CLIContext:
    return CLIContext(
        omd_root=_OMD_ROOT,
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )


def _request() -> CheckingRequest:
    return CheckingRequest(
        file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=False),
        usewalk=False,
        snmp_backend=None,
        no_submit=False,
        perfdata=False,
        plugin_selection=PluginSelectionRequest(
            detect_sections=None, plugins=None, detect_plugins=None
        ),
        fake_dns=None,
        host=HostName("myhost"),
        address=None,
    )


def test_the_requested_host_is_checked() -> None:
    check_host = _FakeCheckHost()

    _CheckCommand(check_host=check_host).run(_context(), _request())

    assert check_host.checked == [(HostName("myhost"), _request(), _OMD_ROOT, False)]


def test_the_check_exits_with_the_hosts_state() -> None:
    assert (
        _CheckCommand(check_host=_FakeCheckHost(state=2)).run(_context(), _request())
        == CLIExitCode.ERROR
    )


def test_a_failed_check_exits_three() -> None:
    check_host = _FakeCheckHost(error=MKGeneralException("Unknown host"))

    assert _CheckCommand(check_host=check_host).run(_context(), _request()) == CLIExitCode.UNKNOWN
