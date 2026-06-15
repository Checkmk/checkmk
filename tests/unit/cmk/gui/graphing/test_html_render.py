#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.graphing import MKGraphWidgetTooSmallError
from cmk.gui.graphing._html_render import (
    _legend_height_ex,
    _MIN_LEGEND_HEIGHT_EX,
    _render_title_elements_plain,
    min_widget_height_ex,
)


@pytest.mark.parametrize(
    "elements, result",
    [
        (
            ["first", "second"],
            "first / second",
        ),
        (
            ["", "second"],
            "second",
        ),
    ],
)
def test_render_title_elements_plain(elements: Sequence[str], result: str) -> None:
    assert _render_title_elements_plain(elements) == result


@pytest.mark.parametrize("usable_height_ex", [11.0, 15.0, 16.0])
def test__legend_height_ex_raises_when_widget_too_small(usable_height_ex: float) -> None:
    # The widget must fit the graph floor plus a useful legend, else the caller surfaces
    # the "increase height or disable legend" error.
    with pytest.raises(MKGraphWidgetTooSmallError):
        _legend_height_ex(usable_height_ex, curve_count=10, horizontal_rule_count=0)


def test__legend_height_ex_enforces_minimum_when_legend_scrolls() -> None:
    # Many curves on a near-minimum widget: the legend is clipped and would collapse, so
    # it is kept at the useful minimum while the graph still keeps its floor.
    height = 17.0
    legend = _legend_height_ex(height, curve_count=20, horizontal_rule_count=0)
    assert legend == _MIN_LEGEND_HEIGHT_EX
    assert height - legend >= min_widget_height_ex


def test__legend_height_ex_uses_estimate_when_it_fits() -> None:
    # Few curves: reserve only what the legend needs, without forcing the minimum or
    # wasting graph space.
    assert _legend_height_ex(60.0, curve_count=1, horizontal_rule_count=0) == int(3.0 + 1.5)


def test__legend_height_ex_never_exceeds_a_third_or_the_graph() -> None:
    height = 60.0
    legend = _legend_height_ex(height, curve_count=50, horizontal_rule_count=0)
    assert legend <= height // 3
    assert legend < height - legend  # legend never larger than the graph
