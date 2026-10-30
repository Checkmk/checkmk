#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.graphing.v1 import graphs, metrics, perfometers, Title, translations
from cmk.graphing_engine import ApiGraphingPlugin, graphing_plugins_of

_METRIC = metrics.Metric(
    name="used",
    title=Title("Used"),
    unit=metrics.Unit(metrics.SINotation("B")),
    color=metrics.Color.BLUE,
)
_PERFOMETER = perfometers.Perfometer(
    name="used",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(100)),
    segments=["used"],
)
_TRANSLATION = translations.Translation(
    name="used",
    check_commands=[translations.PassiveCheck("df")],
    translations={"fs_used": translations.RenameTo("used")},
)
_DRAWN_FIRST = graphs.Graph(name="apache_status", title=Title("First"), simple_lines=["used"])
_DRAWN_SECOND = graphs.Graph(
    name="bufferpool_hitratios", title=Title("Second"), simple_lines=["used"]
)
_PLUGINS: Sequence[ApiGraphingPlugin] = [
    _DRAWN_SECOND,
    _TRANSLATION,
    _PERFOMETER,
    _METRIC,
    _DRAWN_FIRST,
]


def test_the_metrics_are_keyed_by_their_name() -> None:
    assert graphing_plugins_of(_PLUGINS).metrics == {"used": _METRIC}


def test_the_perfometers_are_indexed_by_their_name() -> None:
    assert graphing_plugins_of(_PLUGINS).perfometers.plugins == {"used": _PERFOMETER}


def test_the_graphs_come_in_drawing_order() -> None:
    assert graphing_plugins_of(_PLUGINS).graphs == [_DRAWN_FIRST, _DRAWN_SECOND]


def test_the_translations_are_kept() -> None:
    assert graphing_plugins_of(_PLUGINS).translations == [_TRANSLATION]
