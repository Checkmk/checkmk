#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.cli.engine.commands import bind as cli_bind
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.diagnostics.internal import DiagnosticsPlugin, Help, Sensitivity, Topic
from cmk.plugins.diagnostics.cli.create_dump import (
    _cli_selection,
    _CliSelection,
    _resolve_cli_selection,
    cli_command_create_diagnostics_dump,
)


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


def test_create_diagnostics_dump_declares_its_options_in_help_order() -> None:
    recorded = CLIRecordedOptions()
    cli_command_create_diagnostics_dump.request(recorded)

    assert [option.long for option in recorded.options] == [
        "list",
        "all-topics",
        "plugins",
        "checkmk-server-host",
    ]


def test_the_selection_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions(
        [
            ("--all-topics", "low"),
            ("--plugins", "b_high,a_low"),
            ("--checkmk-server-host", "my_server"),
        ],
        logging.getLogger(__name__),
    )

    assert _cli_selection(options) == _CliSelection(
        list_plugins=False,
        all_topics=Sensitivity.LOW,
        plugins=("b_high", "a_low"),
        checkmk_server_host="my_server",
    )


def test_an_unknown_threshold_is_rejected_before_the_command_runs() -> None:
    with pytest.raises(ValueError, match="--all-topics: Invalid argument"):
        cli_bind(
            cli_command_create_diagnostics_dump,
            CLIParsedOptions([("--all-topics", "extreme")], logging.getLogger(__name__)),
        )


def test_without_a_selection_only_always_plugins_run() -> None:
    selection = _CliSelection(
        list_plugins=False, all_topics=None, plugins=(), checkmk_server_host=None
    )

    assert _resolve_cli_selection(_CLI_CATALOGUE, selection).plugins == []


def test_resolve_cli_selection() -> None:
    selection = _resolve_cli_selection(
        _CLI_CATALOGUE,
        _CliSelection(
            list_plugins=False,
            all_topics=Sensitivity.LOW,
            plugins=("b_high",),
            checkmk_server_host="my_server",
        ),
    )
    assert selection.checkmk_server_host == "my_server"
    assert "a_low" in selection.plugins  # low via --all-topics
    assert "a_medium" not in selection.plugins  # medium exceeds the threshold
    assert "b_high" in selection.plugins  # explicitly selected
    assert "always_one" not in selection.plugins  # runs anyway, needs no selection


def test_resolve_cli_selection_rejects_unknown() -> None:
    with pytest.raises(Exception, match="Unknown plugin"):
        _resolve_cli_selection(
            _CLI_CATALOGUE,
            _CliSelection(
                list_plugins=False, all_topics=None, plugins=("nope",), checkmk_server_host=None
            ),
        )
