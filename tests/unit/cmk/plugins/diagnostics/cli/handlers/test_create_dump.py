#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.base.config import ConfigFileLoadError
from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.diagnostics.engine import DumpSelection
from cmk.diagnostics.internal import DiagnosticsPlugin, Help, Sensitivity, Topic
from cmk.plugins.diagnostics.cli.create_dump import CliSelection
from cmk.plugins.diagnostics.cli.handlers.create_dump import _CreateDiagnosticsDumpCommand


def _make_cli_plugin(
    name: str, topic: Topic, sensitivity: Sensitivity, *, always: bool = False
) -> DiagnosticsPlugin:
    return DiagnosticsPlugin(
        name=name,
        description=Help("A test plugin"),
        sensitivity=sensitivity,
        topic=topic,
        always=always,
        handler=lambda _context: [],
    )


_CLI_TOPIC_A = Topic("Topic A")
_CLI_TOPIC_B = Topic("Topic B")

_CLI_CATALOGUE = {
    plugin.name: plugin
    for plugin in (
        _make_cli_plugin("always_one", _CLI_TOPIC_A, Sensitivity.LOW, always=True),
        _make_cli_plugin("a_low", _CLI_TOPIC_A, Sensitivity.LOW),
        _make_cli_plugin("a_medium", _CLI_TOPIC_A, Sensitivity.MEDIUM),
        _make_cli_plugin("b_high", _CLI_TOPIC_B, Sensitivity.HIGH),
    )
}


_OMD_ROOT = Path("/omd/sites/mysite")


class _FakeLoadCatalogue:
    def __init__(self, catalogue: Mapping[str, DiagnosticsPlugin]) -> None:
        self._catalogue = catalogue

    def __call__(self) -> Mapping[str, DiagnosticsPlugin]:
        return self._catalogue


class _FakeCreateDump:
    def __init__(self, error: Exception | None = None) -> None:
        self.asked: list[tuple[Path, DumpSelection]] = []
        self._error = error

    def __call__(self, omd_root: Path, selection: DumpSelection) -> Path | None:
        self.asked.append((omd_root, selection))
        if self._error is not None:
            raise self._error
        return omd_root / "var/check_mk/diagnostics/dump.tar.gz"


_UNREADABLE_CONFIG = ConfigFileLoadError(_OMD_ROOT / "etc/check_mk/main.mk", ValueError("broken"))


def _dump_command(
    create_dump: _FakeCreateDump,
    catalogue: Mapping[str, DiagnosticsPlugin] = _CLI_CATALOGUE,
) -> _CreateDiagnosticsDumpCommand:
    return _CreateDiagnosticsDumpCommand(
        load_catalogue=_FakeLoadCatalogue(catalogue), create_dump=create_dump
    )


def _context(*, debug: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=_OMD_ROOT,
        global_options=CLIGlobalOptions(debug=debug),
        logger=logging.getLogger(__name__),
    )


def _selection(*plugins: str, list_plugins: bool = False) -> CliSelection:
    return CliSelection(
        list_plugins=list_plugins, all_topics=None, plugins=plugins, checkmk_server_host=None
    )


def test_the_dump_is_created_with_the_selected_plugins() -> None:
    create_dump = _FakeCreateDump()

    _dump_command(create_dump).run(_context(), _selection("b_high"))

    assert create_dump.asked == [
        (_OMD_ROOT, DumpSelection(plugins=["b_high"], checkmk_server_host=""))
    ]


def test_without_a_selection_only_the_plugins_that_always_run_are_left() -> None:
    create_dump = _FakeCreateDump()

    _dump_command(create_dump).run(_context(), _selection())

    assert create_dump.asked == [(_OMD_ROOT, DumpSelection(plugins=[], checkmk_server_host=""))]


def test_all_topics_select_the_plugins_up_to_their_sensitivity() -> None:
    create_dump = _FakeCreateDump()
    selection = CliSelection(
        list_plugins=False,
        all_topics=Sensitivity.LOW,
        plugins=("b_high",),
        checkmk_server_host="my_server",
    )

    _dump_command(create_dump).run(_context(), selection)

    assert create_dump.asked == [
        (
            _OMD_ROOT,
            DumpSelection(plugins=["a_low", "b_high"], checkmk_server_host="my_server"),
        )
    ]


def test_listing_the_plugins_creates_no_dump() -> None:
    create_dump = _FakeCreateDump()

    _dump_command(create_dump).run(_context(), _selection(list_plugins=True))

    assert create_dump.asked == []


def test_the_plugins_are_listed_by_topic(capsys: pytest.CaptureFixture[str]) -> None:
    catalogue = {"a_low": _make_cli_plugin("a_low", _CLI_TOPIC_A, Sensitivity.LOW)}

    _dump_command(_FakeCreateDump(), catalogue).run(_context(), _selection(list_plugins=True))

    assert capsys.readouterr().out == "Topic A\n  a_low (low): A test plugin\n"


def test_an_unknown_plugin_exits_three() -> None:
    assert (
        _dump_command(_FakeCreateDump()).run(_context(), _selection("nope")) == CLIExitCode.UNKNOWN
    )


def test_an_unknown_plugin_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="Unknown plugin 'nope'"):
        _dump_command(_FakeCreateDump()).run(_context(debug=True), _selection("nope"))


def test_an_unreadable_config_file_exits_one() -> None:
    assert (
        _dump_command(_FakeCreateDump(_UNREADABLE_CONFIG)).run(_context(), _selection())
        == CLIExitCode.FAILURE
    )


def test_an_unreadable_config_file_is_raised_through_under_debug() -> None:
    with pytest.raises(ConfigFileLoadError):
        _dump_command(_FakeCreateDump(_UNREADABLE_CONFIG)).run(_context(debug=True), _selection())
