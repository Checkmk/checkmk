#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    entry_point_prefixes,
    GeneratedContent,
    Help,
    Sensitivity,
    Topic,
    VerbatimCopy,
)

_TOPIC = Topic("Test topic")


def _make_plugin(
    name: str = "my_plugin",
    topic: Topic = _TOPIC,
    sensitivity: Sensitivity = Sensitivity.LOW,
) -> DiagnosticsPlugin:
    def _handler(_context: CollectContext) -> Iterable[DumpItem]:
        yield PurePosixPath("some/file.json"), GeneratedContent(b"{}")
        yield PurePosixPath("some/other_file"), VerbatimCopy(Path("/dev/null"))

    return DiagnosticsPlugin(
        name=name,
        description=Help("Collects something."),
        sensitivity=sensitivity,
        topic=topic,
        handler=_handler,
    )


def test_entry_point_prefixes() -> None:
    assert entry_point_prefixes() == {DiagnosticsPlugin: "diagnostics_plugin_"}


def test_plugin_defaults() -> None:
    plugin = _make_plugin()
    assert not plugin.always
    assert not plugin.needs_checkmk_server_host


def test_sensitivity_is_ordered() -> None:
    assert Sensitivity.LOW < Sensitivity.MEDIUM < Sensitivity.HIGH
    assert Sensitivity.HIGH >= Sensitivity.MEDIUM
    assert max(Sensitivity.MEDIUM, Sensitivity.LOW) is Sensitivity.MEDIUM


def test_localizables_localize() -> None:
    def _translate(string: str) -> str:
        return {"Test topic": "Testthema"}.get(string, string)

    assert _TOPIC.localize(_translate) == "Testthema"
    assert (Help("A. ") + Help("B.")).localize(str) == "A. B."
