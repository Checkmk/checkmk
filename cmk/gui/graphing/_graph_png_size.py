#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The physical size of the PNG graphs rendered by _graph_png.

Kept apart from the rendering, so that layout planning does not need matplotlib or numpy."""

from dataclasses import dataclass

from cmk.graphing_engine import drawn_curves, EvaluatedGraph

MM_PER_INCH = 25.4


@dataclass(frozen=True, kw_only=True)
class PngOptions:
    size: tuple[float, float]
    font_size: float
    show_title: bool
    show_legend: bool
    show_vertical_axis: bool
    show_time_axis: bool
    show_graph_time: bool


def ex_to_inches(size_ex: float, font_size_pt: float) -> float:
    # one "ex" is half the font size in points, and 1 point = 1/72 inch
    return size_ex * font_size_pt / 72


def mm_per_ex(font_size_pt: float) -> float:
    """The physical size (in mm) PngOptions.size grows by for each
    additional "ex", i.e. the exact inverse of the ex->inches->mm conversion render_png
    uses internally.

    A caller translating a target physical width/height into `size` (ex) before calling
    render_png() must use this - not cmk.gui.graphing._graph_display_config.get_mm_per_ex(), a
    differently-calibrated ex convention used to estimate a graph's step from its width -
    or the resulting image will come out a few percent off the intended physical size.
    """
    return ex_to_inches(1.0, font_size_pt) * MM_PER_INCH


def legend_height_ex(graph: EvaluatedGraph, options: PngOptions) -> float:
    """The "ex" height render_png() reserves below the plot for the scalar/rule legend table,
    e.g. 0.0 if there is nothing to show. Depends only on the graph's own curve/rule counts and
    options.show_legend - never on options.size - so it's safe to call before an actual render."""
    n_curves = sum(1 for _drawn in drawn_curves(graph.stacks, graph.lines))
    n_legend_rows = n_curves + len(graph.rules) + len(graph.regions)
    return 2.0 * (n_legend_rows + 1) if options.show_legend and n_legend_rows else 0.0


def compute_png_size_mm(graph: EvaluatedGraph, options: PngOptions) -> tuple[float, float]:
    """The (width_mm, height_mm) of the image render_png() draws for this graph/options, without
    paying for an actual matplotlib render.

    Useful for layout/pagination planning that only needs the size a graph will occupy, not its
    pixels yet - e.g. deciding how many graphs fit on a report page before rendering any of them.
    """
    width_in = ex_to_inches(options.size[0], options.font_size)
    height_in = ex_to_inches(options.size[1] + legend_height_ex(graph, options), options.font_size)
    return width_in * MM_PER_INCH, height_in * MM_PER_INCH
