#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Final

import pytest

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.dump import (
    DumpAgentRequest,
    DumpHostsRequest,
)
from cmk.plugins.checkmk.cli.handlers.dump import (
    _AgentDump,
    _DumpAgentCommand,
    _DumpHostsCommand,
    _source_dump,
)
from cmk.plugins.checkmk.cli.options import FileCacheRequest

_OMD_ROOT: Final = Path("/omd/sites/mysite")


class _FakeDumpAgent:
    def __init__(self, dump: _AgentDump) -> None:
        self.asked: list[tuple[HostAddress, DumpAgentRequest, Path, bool]] = []
        self._dump = dump

    def __call__(
        self, host: HostAddress, request: DumpAgentRequest, *, omd_root: Path, debug: bool
    ) -> _AgentDump:
        self.asked.append((host, request, omd_root, debug))
        return self._dump


def _agent_request(host: HostAddress) -> DumpAgentRequest:
    return DumpAgentRequest(
        file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=False),
        snmp_backend=None,
        fake_dns=None,
        host=host,
    )


_CONTEXT: Final = CLIContext(
    omd_root=_OMD_ROOT,
    global_options=CLIGlobalOptions(),
    logger=logging.getLogger(__name__),
)


def test_the_agent_output_of_the_requested_host_is_dumped() -> None:
    dump_agent = _FakeDumpAgent(_AgentDump(b"", (), ()))

    _DumpAgentCommand(dump_agent=dump_agent).run(_CONTEXT, _agent_request(HostAddress("myhost")))

    assert dump_agent.asked == [
        (HostAddress("myhost"), _agent_request(HostAddress("myhost")), _OMD_ROOT, False)
    ]


def test_the_agent_output_is_written(capsys: pytest.CaptureFixture[str]) -> None:
    context = CLIContext(
        omd_root=_OMD_ROOT,
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )
    dump_agent = _FakeDumpAgent(_AgentDump(b"<<<check_mk>>>\n", (), ()))

    _DumpAgentCommand(dump_agent=dump_agent).run(context, _agent_request(HostAddress("myhost")))

    assert capsys.readouterr().out == "<<<check_mk>>>\n"


def test_an_agent_dump_with_errors_exits_one() -> None:
    dump_agent = _FakeDumpAgent(_AgentDump(b"", (), ("ERROR [agent]: refused",)))

    assert (
        _DumpAgentCommand(dump_agent=dump_agent).run(
            _CONTEXT, _agent_request(HostAddress("myhost"))
        )
        == CLIExitCode.FAILURE
    )


def test_the_warnings_and_errors_are_reported(capsys: pytest.CaptureFixture[str]) -> None:
    dump_agent = _FakeDumpAgent(
        _AgentDump(b"", ("WARNING [agent]: denied",), ("ERROR [agent]: refused",))
    )

    _DumpAgentCommand(dump_agent=dump_agent).run(_CONTEXT, _agent_request(HostAddress("myhost")))

    assert capsys.readouterr().err == "WARNING [agent]: denied\nERROR [agent]: refused\n"


class _FakeDumpHosts:
    def __init__(self) -> None:
        self.asked: list[tuple[DumpHostsRequest, bool]] = []

    def __call__(self, request: DumpHostsRequest, *, debug: bool) -> None:
        self.asked.append((request, debug))


def test_the_requested_hosts_are_dumped() -> None:
    dump_hosts = _FakeDumpHosts()
    request = DumpHostsRequest(fake_dns=None, hosts=(HostAddress("myhost"),))

    _DumpHostsCommand(dump_hosts=dump_hosts).run(_CONTEXT, request)

    assert dump_hosts.asked == [(request, False)]


def test_a_source_with_a_warning_reports_it() -> None:
    results = [
        ActiveCheckResult(state=0, summary="Success"),
        ActiveCheckResult(state=1, summary="Section foo denied"),
    ]

    assert _source_dump("agent", b"", results).warnings == (
        "WARNING [agent]: Success, Section foo denied",
    )


def test_a_source_with_a_failure_reports_an_error() -> None:
    results = [ActiveCheckResult(state=2, summary="Something broke")]

    assert _source_dump("agent", b"", results).errors == ("ERROR [agent]: Something broke",)


def test_an_error_outranks_a_warning() -> None:
    results = [
        ActiveCheckResult(state=1, summary="denied"),
        ActiveCheckResult(state=3, summary="unknown"),
    ]

    assert _source_dump("agent", b"", results) == _AgentDump(
        b"", (), ("ERROR [agent]: denied, unknown",)
    )


def test_a_successful_source_reports_nothing() -> None:
    assert _source_dump(
        "agent", b"<<<check_mk>>>\n", [ActiveCheckResult(state=0, summary="Success")]
    ) == _AgentDump(b"<<<check_mk>>>\n", (), ())
