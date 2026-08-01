#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.diagnostics.engine import resolve_selection
from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    Help,
    Sensitivity,
    Topic,
)

_TOPIC_A = Topic("Topic A")
_TOPIC_B = Topic("Topic B")


def _handler(_context: CollectContext) -> Iterable[DumpItem]:
    return ()


def _make_plugin(
    name: str,
    topic: Topic,
    sensitivity: Sensitivity,
    always: bool = False,
) -> DiagnosticsPlugin:
    return DiagnosticsPlugin(
        name=name,
        description=Help("Collects something."),
        sensitivity=sensitivity,
        topic=topic,
        always=always,
        handler=_handler,
    )


_PLUGINS = [
    _make_plugin("a_low", _TOPIC_A, Sensitivity.LOW),
    _make_plugin("a_medium", _TOPIC_A, Sensitivity.MEDIUM),
    _make_plugin("a_high", _TOPIC_A, Sensitivity.HIGH),
    _make_plugin("a_always", _TOPIC_A, Sensitivity.LOW, always=True),
    _make_plugin("b_medium", _TOPIC_B, Sensitivity.MEDIUM),
]


def test_resolve_selection_empty_thresholds_selects_nothing() -> None:
    assert resolve_selection(_PLUGINS, {}) == []


def test_resolve_selection_off_topic_selects_nothing() -> None:
    assert resolve_selection(_PLUGINS, {_TOPIC_A: None, _TOPIC_B: None}) == []


def test_resolve_selection_respects_thresholds_per_topic() -> None:
    assert resolve_selection(
        _PLUGINS,
        {_TOPIC_A: Sensitivity.MEDIUM, _TOPIC_B: Sensitivity.LOW},
    ) == ["a_low", "a_medium"]


def test_resolve_selection_high_selects_all_but_always() -> None:
    assert resolve_selection(
        _PLUGINS,
        {_TOPIC_A: Sensitivity.HIGH, _TOPIC_B: Sensitivity.HIGH},
    ) == ["a_high", "a_low", "a_medium", "b_medium"]


def test_resolve_selection_excludes_always_plugins() -> None:
    assert "a_always" not in resolve_selection(
        _PLUGINS, {_TOPIC_A: Sensitivity.HIGH, _TOPIC_B: Sensitivity.HIGH}
    )
