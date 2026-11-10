#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.diagnostics.internal import DiagnosticsPlugin, Help, Sensitivity, Topic
from cmk.plugins.diagnostics.cli.create_dump import (
    _ALL_TOPICS_VALUE,
    _CHECKMK_SERVER_HOST_VALUE,
    _cli_selection,
    _CliSelection,
    _PLUGINS_VALUE,
    _resolve_cli_selection,
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


def test_the_selection_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _ALL_TOPICS_VALUE: ["low"],
        _PLUGINS_VALUE: ["b_high,a_low"],
        _CHECKMK_SERVER_HOST_VALUE: ["my_server"],
    }

    assert _cli_selection(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == _CliSelection(
        list_plugins=False,
        all_topics=Sensitivity.LOW,
        plugins=("b_high", "a_low"),
        checkmk_server_host="my_server",
    )


def test_an_unknown_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="extreme"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {_ALL_TOPICS_VALUE: ["extreme"]}

        _cli_selection(CLIReader(lambda declaration: given.get(declaration, ())))


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
