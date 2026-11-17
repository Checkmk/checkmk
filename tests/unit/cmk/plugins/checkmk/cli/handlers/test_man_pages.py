#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKBailOut
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.man_pages import _BrowseManCommand, _ManCommand
from cmk.plugins.checkmk.cli.man_pages import ManRequest
from cmk.utils.man_pages import ManPage

_DF_PATH = Path("/omd/sites/mysite/share/check_mk/checkman/df")

_DF = ManPage(
    name="df",
    path=_DF_PATH,
    title="Filesystems",
    agents=["linux"],
    catalog=["os", "storage"],
    license="GPL",
    distribution="check_mk",
    description="Checks the usage of filesystems.",
    item=None,
    discovery=None,
    cluster=None,
)


def _context(*, debug: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=Path("/omd/sites/mysite"),
        global_options=CLIGlobalOptions(debug=debug),
        logger=logging.getLogger(__name__),
    )


class _FakeManPagePaths:
    def __init__(self) -> None:
        self.asked: list[bool] = []

    def __call__(self, *, debug: bool) -> Mapping[str, Path]:
        self.asked.append(debug)
        return {"df": _DF_PATH}


class _FakePrintManPageTable:
    def __init__(self) -> None:
        self.printed: list[Mapping[str, Path]] = []

    def __call__(self, man_page_path_map: Mapping[str, Path]) -> None:
        self.printed.append(man_page_path_map)


class _FakeParseManPage:
    def __init__(self) -> None:
        self.parsed: list[tuple[str, Path, bool]] = []

    def __call__(self, name: str, path: Path, *, debug: bool) -> ManPage:
        self.parsed.append((name, path, debug))
        return _DF


def _man_command(
    *,
    print_table: _FakePrintManPageTable | None = None,
    parse: _FakeParseManPage | None = None,
) -> _ManCommand:
    return _ManCommand(
        paths=_FakeManPagePaths(),
        print_table=print_table or _FakePrintManPageTable(),
        parse=parse or _FakeParseManPage(),
    )


def _request(check_type: str | None) -> ManRequest:
    return ManRequest(renderer=None, check_type=check_type)


def test_without_a_check_type_the_table_of_all_man_pages_is_printed() -> None:
    print_table = _FakePrintManPageTable()

    _man_command(print_table=print_table).run(_context(), _request(None))

    assert print_table.printed == [{"df": _DF_PATH}]


def test_the_man_page_of_the_check_type_is_parsed() -> None:
    parse = _FakeParseManPage()

    _man_command(parse=parse).run(_context(), _request("df"))

    assert parse.parsed == [("df", _DF_PATH, False)]


def test_the_rendered_man_page_is_written(capsys: pytest.CaptureFixture[str]) -> None:
    _man_command().run(_context(), _request("df"))

    assert "Filesystems" in capsys.readouterr().out


def test_an_unknown_check_type_exits_three() -> None:
    assert _man_command().run(_context(), _request("nope")) == CLIExitCode.UNKNOWN


def test_an_unknown_check_type_is_raised_through_under_debug() -> None:
    with pytest.raises(MKBailOut, match="No manpage for nope"):
        _man_command().run(_context(debug=True), _request("nope"))


class _FakeBrowseManPages:
    def __init__(self) -> None:
        self.browsed: list[bool] = []

    def __call__(self, *, debug: bool) -> None:
        self.browsed.append(debug)


def test_the_man_pages_are_browsed() -> None:
    browse = _FakeBrowseManPages()

    _BrowseManCommand(browse=browse).run(_context(), None)

    assert browse.browsed == [False]
