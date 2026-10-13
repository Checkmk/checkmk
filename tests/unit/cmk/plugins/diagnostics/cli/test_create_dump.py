#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.diagnostics.internal import DiagnosticsPlugin, Help, Sensitivity, Topic
from cmk.plugins.diagnostics.cli import create_dump


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


def test_resolve_cli_selection() -> None:
    # no options: only 'always' plugins run (empty explicit selection)
    assert (
        create_dump._resolve_cli_selection(  # noqa: SLF001
            _CLI_CATALOGUE,
            create_dump._cli_selection({}),  # noqa: SLF001
        ).plugins
        == []
    )

    selection = create_dump._resolve_cli_selection(  # noqa: SLF001
        _CLI_CATALOGUE,
        create_dump._cli_selection(  # noqa: SLF001
            {
                "all-topics": "low",
                "plugins": "b_high",
                "checkmk-server-host": "my_server",
            }
        ),
    )
    assert selection.checkmk_server_host == "my_server"
    assert "a_low" in selection.plugins  # low via --all-topics
    assert "a_medium" not in selection.plugins  # medium exceeds the threshold
    assert "b_high" in selection.plugins  # explicitly selected
    assert "always_one" not in selection.plugins  # runs anyway, needs no selection


def test_resolve_cli_selection_rejects_unknown() -> None:
    with pytest.raises(Exception, match="Unknown plugin"):
        create_dump._resolve_cli_selection(  # noqa: SLF001
            _CLI_CATALOGUE,
            create_dump._cli_selection({"plugins": "nope"}),  # noqa: SLF001
        )
    with pytest.raises(Exception, match="Invalid sensitivity"):
        create_dump._resolve_cli_selection(  # noqa: SLF001
            _CLI_CATALOGUE,
            create_dump._cli_selection({"all-topics": "extreme"}),  # noqa: SLF001
        )
