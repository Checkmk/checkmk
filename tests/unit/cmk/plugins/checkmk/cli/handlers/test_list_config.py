#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.list_config import (
    _DSType,
    _ListChecksCommand,
    _ListHostsCommand,
    _ListTagCommand,
    _TableRow,
)
from cmk.plugins.checkmk.cli.list_config import ListHostsRequest
from cmk.ruleset_matcher.tags import TagID


def _context() -> CLIContext:
    return CLIContext(
        omd_root=Path("/omd/sites/mysite"),
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )


_CONTEXT = _context()

_REQUEST = ListHostsRequest(all_sites=False, include_offline=False, host_groups=("linux",))


class _FakeListHosts:
    def __init__(self, error: MKGeneralException | None = None) -> None:
        self.asked: list[tuple[ListHostsRequest, bool]] = []
        self._error = error

    def __call__(self, request: ListHostsRequest, *, debug: bool) -> Sequence[HostName]:
        self.asked.append((request, debug))
        if self._error is not None:
            raise self._error
        return [HostName("host1"), HostName("host2")]


def test_the_requested_hosts_are_listed() -> None:
    list_hosts = _FakeListHosts()

    _ListHostsCommand(list_hosts=list_hosts).run(_CONTEXT, _REQUEST)

    assert list_hosts.asked == [(_REQUEST, False)]


def test_the_hosts_are_written_one_per_line(capsys: pytest.CaptureFixture[str]) -> None:
    _ListHostsCommand(list_hosts=_FakeListHosts()).run(_context(), _REQUEST)

    assert capsys.readouterr().out == "host1\nhost2\n"


def test_a_failed_host_listing_exits_three() -> None:
    list_hosts = _FakeListHosts(error=MKGeneralException("Cannot load the configuration"))

    assert _ListHostsCommand(list_hosts=list_hosts).run(_CONTEXT, _REQUEST) == CLIExitCode.UNKNOWN


class _FakeListHostsWithTags:
    def __init__(self, hosts: Sequence[HostName]) -> None:
        self.asked: list[tuple[Sequence[TagID], bool]] = []
        self._hosts = hosts

    def __call__(self, tags: Sequence[TagID], *, debug: bool) -> Sequence[HostName]:
        self.asked.append((tags, debug))
        return self._hosts


def test_the_hosts_with_the_tags_are_written_sorted(capsys: pytest.CaptureFixture[str]) -> None:
    list_hosts = _FakeListHostsWithTags([HostName("zeta"), HostName("alpha")])

    _ListTagCommand(list_hosts_with_tags=list_hosts).run(_context(), (TagID("lan"),))

    assert capsys.readouterr().out == "alpha\nzeta\n"


def test_no_host_with_the_tags_writes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    _ListTagCommand(list_hosts_with_tags=_FakeListHostsWithTags([])).run(
        _context(), (TagID("lan"),)
    )

    assert capsys.readouterr().out == ""


_MEM = _TableRow(name="mem", ds_type=_DSType.AGENT, title="Memory")

_DF = _TableRow(name="df", ds_type=_DSType.AGENT, title="Filesystems")


class _FakeCheckTable:
    def __init__(self) -> None:
        self.asked: list[bool] = []

    def __call__(self, *, debug: bool) -> Sequence[_TableRow]:
        self.asked.append(debug)
        return [_MEM, _DF]


def test_the_checks_are_listed_by_name(capsys: pytest.CaptureFixture[str]) -> None:
    _ListChecksCommand(check_table=_FakeCheckTable()).run(_context(), None)

    assert capsys.readouterr().out == f"{_DF.render_tty()}\n{_MEM.render_tty()}\n"
