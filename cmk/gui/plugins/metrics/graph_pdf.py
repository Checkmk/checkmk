#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render graphs in PDF. Is also used for PNG image rendering."""

from typing import Optional, Sequence, TypeGuard

from cmk.utils.type_defs import Timestamp

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.metrics.artwork import GraphArtwork, LayoutedCurve, LayoutedCurveArea
from cmk.gui.plugins.metrics.utils import (
    darken_color,
    GraphDataRange,
    GraphRenderOptions,
    lighten_color,
    parse_color,
    RGBColor,
)

SizeMM = float


def render_graph_pdf(  # pylint: disable=too-many-branches
    instance,
    graph_artwork: GraphArtwork,
    graph_data_range: GraphDataRange,
    graph_render_options: GraphRenderOptions,
    pos_left: Optional[SizeMM] = None,
    pos_top: Optional[SizeMM] = None,
    total_width: Optional[SizeMM] = None,
    total_height: Optional[SizeMM] = None,
) -> None:
    pdf_document = instance["document"]

    logger.debug("  Render graph %r", graph_artwork["definition"]["specification"])

    if pos_left is None:  # floating element
        pdf_document.margin(2.5)

    # Styling for PDF graphs. Note: We could make some of these
    # configurable
    font_size = graph_render_options["font_size"]
    mm_per_ex = mm_per_ex_by_render_options(graph_render_options)
    v_label_margin = 1.0  # mm
    t_label_margin = _graph_time_label_margin()
    left_border = _graph_vertical_axis_width(graph_render_options)
    left_margin = _graph_left_margin(graph_render_options)
    top_margin = _graph_top_margin(graph_render_options)
    right_margin = _graph_right_margin(graph_render_options)
    bottom_margin = _graph_bottom_margin(graph_render_options)
    axis_color = parse_color(graph_render_options["foreground_color"])
    zero_rule_color = parse_color(graph_render_options["foreground_color"])
    canvas_color = parse_color(graph_render_options["canvas_color"])
    background_color = parse_color(graph_render_options["background_color"])
    foreground_color = parse_color(graph_render_options["foreground_color"])
    axis_over_width = _graph_axis_over_width(graph_render_options)
    color_gradient = graph_render_options["color_gradient"] / 100.0
    curve_line_width = 0.1  # mm
    rule_line_width = 0.1  # mm
    label_line_width = 0.04  # mm
    v_line_color = tuple(
        map(parse_color, [graph_render_options["foreground_color"], "#a0a0a0", "#a0a0a0"])
    )
    v_line_dash = [None, [0.2, 0.4], None]
    t_line_color = tuple(
        map(parse_color, [graph_render_options["foreground_color"], "#a0a0a0", "#666666"])
    )
    t_line_dash = [None, [0.2, 0.2], None]
    legend_box_line_width = 0.1

    pdf_document.save_state()
    pdf_document.set_font_size(font_size)

    legend_box_size = mm_per_ex

    title_height = graph_title_height(graph_render_options)
    legend_height = graph_legend_height(graph_artwork, graph_render_options)

    if pos_left is not None:
        # Absolute placement of graph
        assert pos_top is not None
        assert total_width is not None
        assert total_height is not None
        height = total_height - title_height - legend_height
        width = total_width

    else:
        # Place graph in page flow
        width_ex, height_ex = graph_render_options["size"]
        width = width_ex * mm_per_ex
        height = height_ex * mm_per_ex

    left, top, width, total_height = pdf_document.add_canvas(
        width,
        height + title_height + legend_height,
        border_width=graph_render_options["border_width"],
        left_mm=pos_left,
    )

    # From here width, height, total_height, left and top are in "mm".

    right = left + width - right_margin
    total_bottom = top - total_height
    bottom = top - height - title_height

    # Fill canvas with background color
    pdf_document.render_rect(left, total_bottom, width, total_height, fill_color=background_color)

    # Regular title (above graph area)
    if graph_render_options["show_title"] is True:
        title_left_margin = left + right_margin
        if vertical_axis_label := graph_artwork.get("vertical_axis", {}).get("axis_label"):
            title_left_margin = left + left_border + left_margin

        pdf_document.render_aligned_text(
            title_left_margin,
            top - title_height,
            width,
            title_height,
            graph_artwork["title"],
            align="left",
            bold=True,
            color=foreground_color,
        )

    # The following code is inspired by htdocs/js/graphs.js:render_graph(). Whenever
    # you change something there, the change should also be reflected here!

    bottom_border = _graph_bottom_border(graph_render_options)

    # Prepare position and translation of origin
    t_range_from = graph_artwork["time_axis"]["range"][0]
    t_range_to = graph_artwork["time_axis"]["range"][1]
    t_range = t_range_to - t_range_from
    t_mm = width - left_border - left_margin - right_margin
    t_mm_per_second = 1.0 * t_mm / t_range

    v_range_from = graph_artwork["vertical_axis"]["range"][0]
    v_range_to = graph_artwork["vertical_axis"]["range"][1]
    v_range = v_range_to - v_range_from
    v_mm = height - top_margin - bottom_border - bottom_margin
    v_mm_per_unit = 1.0 * v_mm / v_range

    t_orig = left + left_border + left_margin
    v_orig = bottom + bottom_border + bottom_margin
    v_axis_orig = v_range_from

    # paint graph background
    pdf_document.render_rect(t_orig, v_orig, t_mm, v_mm, fill_color=canvas_color)

    # Now transform the whole chooridate system to our real t and v choords
    # so if we paint something at (0, 0) it will correctly represent a
    # value of 0 and a time point of time_start.
    def trans_t(t: float) -> float:
        return (t - t_range_from) * t_mm_per_second + t_orig

    def trans_v(v: float) -> float:
        return v_orig + ((v - v_axis_orig) * v_mm_per_unit)

    def trans(t: float, v: float) -> tuple[float, float]:
        return (trans_t(t), trans_v(v))

    # Paint curves
    pdf_document.save_state()
    pdf_document.add_clip_rect(t_orig, v_orig, t_mm, v_mm)
    step = graph_artwork["step"] // 2
    for curve in graph_artwork["curves"]:
        if curve.get("dont_paint"):
            continue

        t = graph_artwork["start_time"]
        color = parse_color(curve["color"])

        if is_area_layouted_curve(curve):
            points = curve["points"]
            prev_lower = None
            prev_upper = None

            gradient = (
                t_orig,
                v_orig,
                t_orig,
                v_orig + v_mm,
                (darken_color(color, color_gradient), color, lighten_color(color, color_gradient)),
                (0.0, 0.5, 1.0),
            )

            for lower, upper in points:
                if (
                    lower is not None
                    and upper is not None
                    and prev_lower is not None
                    and prev_upper is not None
                ):
                    pdf_document.begin_path()
                    pdf_document.move_to(trans_t(t - step) - 0.01, trans_v(prev_lower))
                    pdf_document.line_to(trans_t(t - step) - 0.01, trans_v(prev_upper))
                    pdf_document.line_to(trans_t(t), trans_v(upper))
                    pdf_document.line_to(trans_t(t), trans_v(lower))
                    pdf_document.line_to(trans_t(t - step) - 0.01, trans_v(prev_lower))
                    pdf_document.close_path()
                    pdf_document.fill_path(color, gradient=gradient)

                prev_lower = lower
                prev_upper = upper
                t += step

        else:  # "line"
            last_value = None
            pdf_document.begin_path()
            for value in curve["points"]:
                if value is not None:
                    p = trans(t, value)  # type: ignore[arg-type]  # TODO: what is going on here?
                    if last_value is not None:
                        pdf_document.line_to(p[0], p[1])
                    else:
                        pdf_document.move_to(p[0], p[1])
                last_value = value
                t += step
            pdf_document.stroke_path(color=color, width=curve_line_width)

    pdf_document.restore_state()  # Remove clipping

    # Now we use these four dimensions for drawing into the canvas using render_...
    # functions from pdf. Note: top > bottom.

    # Clear areas where values have been painted out of range. This is
    # At top and bottom
    pdf_document.render_rect(t_orig, v_orig + v_mm, t_mm, top_margin, fill_color=background_color)
    pdf_document.render_rect(t_orig, bottom, t_mm, v_orig - bottom, fill_color=background_color)

    # Paint axes and a strong line at 0, if that is in the range
    pdf_document.render_line(
        t_orig, v_orig - axis_over_width, t_orig, v_orig + v_mm, color=axis_color
    )
    pdf_document.render_line(t_orig - axis_over_width, v_orig, right, v_orig, color=axis_color)
    if v_range_from <= 0 <= v_range_to:
        pdf_document.render_line(t_orig, trans_v(0), right, trans_v(0), color=zero_rule_color)

    # Show the inline title
    if graph_render_options["show_title"] == "inline":
        title_top = top - (mm_per_ex_by_render_options(graph_render_options) * 2)
        pdf_document.render_aligned_text(
            left,
            title_top,
            width,
            mm_per_ex_by_render_options(graph_render_options) * 2,
            graph_artwork["title"],
            align="center",
            bold=True,
            color=foreground_color,
        )

    if graph_render_options["show_graph_time"]:
        title_top = top - (mm_per_ex_by_render_options(graph_render_options) * 2)
        pdf_document.render_aligned_text(
            left - right_margin,
            title_top,
            width,
            mm_per_ex_by_render_options(graph_render_options) * 2,
            graph_artwork["time_axis"]["title"],
            align="right",
            bold=True,
            color=foreground_color,
        )

    # Paint the vertical axis
    if graph_render_options["show_vertical_axis"]:
        # Render optional vertical axis label
        vertical_axis_label = graph_artwork["vertical_axis"]["axis_label"]
        if vertical_axis_label:
            pdf_document.render_aligned_text(
                left + left_margin,
                top - title_height,
                left_border,
                title_height,
                vertical_axis_label,
                align="center",
                valign="middle",
                color=foreground_color,
            )

    for position, label, line_width in graph_artwork["vertical_axis"]["labels"]:
        if line_width > 0:
            pdf_document.render_line(
                t_orig,
                trans_v(position),
                right,
                trans_v(position),
                width=label_line_width,
                color=v_line_color[line_width],
                dashes=v_line_dash[line_width],
            )

        if graph_render_options["show_vertical_axis"] and label:
            pdf_document.render_aligned_text(
                t_orig - v_label_margin - left_border,
                trans_v(position),
                left_border,
                mm_per_ex,
                label,
                align="right",
                valign="middle",
                color=foreground_color,
            )

    # Paint time axis
    for position, label, line_width in graph_artwork["time_axis"]["labels"]:
        t_pos_mm = trans_t(position)
        if line_width > 0 and t_pos_mm > t_orig:
            pdf_document.render_line(
                t_pos_mm,
                v_orig,
                t_pos_mm,
                trans_v(v_range_to),
                width=label_line_width,
                color=t_line_color[line_width],
                dashes=t_line_dash[line_width],
            )

        if graph_render_options["show_time_axis"] and label:
            pdf_document.render_aligned_text(
                t_pos_mm,
                v_orig - t_label_margin - mm_per_ex,
                0,
                mm_per_ex,
                label,
                align="center",
                color=foreground_color,
            )

    # Paint horizontal rules like warn and crit
    rules = graph_artwork["horizontal_rules"]
    for position, label, color_from_rule, title in rules:
        if v_range_from <= position <= v_range_to:
            pdf_document.render_line(
                t_orig,
                trans_v(position),
                right,
                trans_v(position),
                width=rule_line_width,
                color=parse_color(color_from_rule),
            )

    # Paint legend
    if graph_render_options["show_legend"]:
        legend_lineskip = get_graph_legend_lineskip(graph_render_options)
        legend_top_margin = _graph_legend_top_margin()
        legend_top = bottom - legend_top_margin + bottom_margin
        legend_column_width = (width - left_margin - left_border - right_margin) / 7.0

        def paint_legend_line(color: Optional[RGBColor], texts: Sequence[Optional[str]]) -> None:
            l = t_orig
            if color:
                pdf_document.render_rect(
                    l,
                    legend_top + mm_per_ex * 0.2,
                    legend_box_size,
                    legend_box_size,
                    fill_color=color,
                    line_width=legend_box_line_width,
                )
            for nr, text in enumerate(texts):
                if text:
                    pdf_document.render_aligned_text(
                        l + (color and nr == 0 and legend_box_size + 0.8 or 0),
                        legend_top,
                        legend_column_width,
                        legend_lineskip,
                        text,
                        align=nr == 0 and "left" or "right",
                        color=foreground_color,
                    )
                if nr == 0:
                    l += legend_column_width * 3
                else:
                    l += legend_column_width

        scalars = [
            ("min", _("Minimum")),
            ("max", _("Maximum")),
            ("average", _("Average")),
            ("last", _("Last")),
        ]
        scalars_legend_line: list[Optional[str]] = [None]

        paint_legend_line(None, scalars_legend_line + [x[1] for x in scalars])
        pdf_document.render_line(t_orig, legend_top, t_orig + t_mm, legend_top)

        for curve in graph_artwork["curves"]:
            legend_top -= legend_lineskip
            texts = [str(curve["title"])]
            for scalar, title in scalars:
                texts.append(curve["scalars"][scalar][1])
            paint_legend_line(parse_color(curve["color"]), texts)

        if graph_artwork["horizontal_rules"]:
            pdf_document.render_line(t_orig, legend_top, t_orig + t_mm, legend_top)
            for value, readable, color_from_artwork, title in graph_artwork["horizontal_rules"]:
                legend_top -= legend_lineskip
                paint_legend_line(
                    parse_color(color_from_artwork), [str(title), None, None, None, readable]
                )

    if graph_artwork["definition"].get("is_forecast"):
        pin = trans_t(graph_artwork["requested_end_time"])
        pdf_document.render_line(pin, v_orig, pin, trans_v(v_range_to), color=(0.0, 1.0, 0.0))

    pdf_document.restore_state()
    if left is None:  # floating element
        pdf_document.margin(2.5)

    logger.debug("  Finished rendering graph")


def is_area_layouted_curve(curve: LayoutedCurve) -> TypeGuard[LayoutedCurveArea]:
    return curve["type"] == "area"


def compute_pdf_graph_data_range(
    width: SizeMM, start_time: Timestamp, end_time: Timestamp
) -> GraphDataRange:
    """Estimate step. It is depended on width of the graph in mm."""
    graph_offcut_width = 20.0  # total width - this = width of canvas in mm
    mm_per_step = 0.5  # approx. one datapoint per 0.5 mm

    available_width = width - graph_offcut_width
    number_of_steps = int(available_width / mm_per_step)  # fixed: true-division
    step = int((end_time - start_time) / number_of_steps / 2)
    return GraphDataRange(
        {
            "time_range": (start_time, end_time),
            "step": step,
        }
    )


def get_mm_per_ex(font_size: float) -> SizeMM:
    return font_size / 3.0


def mm_per_ex_by_render_options(graph_render_options: GraphRenderOptions) -> SizeMM:
    return get_mm_per_ex(graph_render_options["font_size"])


def _graph_bottom_border(graph_render_options: GraphRenderOptions) -> SizeMM:
    mm_per_ex = get_mm_per_ex(graph_render_options["font_size"])
    t_label_margin = _graph_time_label_margin()

    if graph_render_options["show_time_axis"]:
        return mm_per_ex + t_label_margin
    return 0


def _graph_legend_top_margin() -> SizeMM:
    return 4.0  # mm


def _graph_time_label_margin() -> SizeMM:
    return 1.0  # mm


def get_graph_legend_lineskip(graph_render_options: GraphRenderOptions) -> SizeMM:
    return mm_per_ex_by_render_options(graph_render_options) * 1.5


def _graph_vertical_axis_width(graph_render_options: GraphRenderOptions) -> SizeMM:
    if not graph_render_options["show_vertical_axis"]:
        return 0.0  # mm

    if (
        isinstance(graph_render_options["vertical_axis_width"], tuple)
        and graph_render_options["vertical_axis_width"][0] == "explicit"
    ):
        return get_mm_per_ex(graph_render_options["vertical_axis_width"][1])

    return 5 * mm_per_ex_by_render_options(graph_render_options)


def _graph_top_margin(graph_render_options: GraphRenderOptions) -> SizeMM:
    if graph_render_options["show_margin"]:
        return 1.0  # mm
    return 0.0


def _graph_right_margin(graph_render_options: GraphRenderOptions) -> SizeMM:
    if graph_render_options["show_margin"]:
        return 2.5  # mm
    return 0.0


def _graph_bottom_margin(graph_render_options: GraphRenderOptions) -> SizeMM:
    if graph_render_options["show_margin"]:
        return 1.0  # mm
    return 0.0


def _graph_axis_over_width(graph_render_options: GraphRenderOptions) -> SizeMM:
    if graph_render_options["show_margin"]:
        return 0.5  # mm
    return 0.0


def _graph_left_margin(graph_render_options: GraphRenderOptions) -> SizeMM:
    if graph_render_options["show_margin"]:
        return 2.0  # mm
    return 0.0


def graph_title_height(graph_render_options: GraphRenderOptions) -> SizeMM:
    if graph_render_options["show_title"] in [False, "inline"]:
        return 0
    return mm_per_ex_by_render_options(graph_render_options) * 2


def graph_legend_height(
    graph_artwork: GraphArtwork, graph_render_options: GraphRenderOptions
) -> SizeMM:
    if not graph_render_options["show_legend"]:
        return 0

    legend_lineskip = get_graph_legend_lineskip(graph_render_options)
    legend_top_margin = _graph_legend_top_margin()

    num_painted_curves = 0
    for curve in graph_artwork["curves"]:
        if not curve.get("dont_paint"):
            num_painted_curves += 1

    return legend_top_margin + (
        legend_lineskip * (1 + num_painted_curves + len(graph_artwork["horizontal_rules"]))
    )
