#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import drawn_curves, EvaluatedGraph

from ._wire import PngOptions

MM_PER_INCH = 25.4


def ex_to_inches(size_ex: float, font_size_pt: float) -> float:
    # one "ex" is half the font size in points, and 1 point = 1/72 inch
    return size_ex * font_size_pt / 72


def mm_per_ex(font_size_pt: float) -> float:
    """The inverse of the renderer's ex-to-mm conversion. get_mm_per_ex uses a different ex,
    so an image sized with it comes out a few percent off."""
    return ex_to_inches(1.0, font_size_pt) * MM_PER_INCH


def legend_height_ex(graph: EvaluatedGraph, options: PngOptions) -> float:
    n_curves = sum(1 for _drawn in drawn_curves(graph.stacks, graph.lines))
    n_legend_rows = n_curves + len(graph.rules) + len(graph.regions)
    return 2.0 * (n_legend_rows + 1) if options.show_legend and n_legend_rows else 0.0


def compute_png_size_mm(graph: EvaluatedGraph, options: PngOptions) -> tuple[float, float]:
    width_in = ex_to_inches(options.size[0], options.font_size)
    height_in = ex_to_inches(options.size[1] + legend_height_ex(graph, options), options.font_size)
    return width_in * MM_PER_INCH, height_in * MM_PER_INCH
