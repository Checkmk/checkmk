#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from pydantic import field_validator

from cmk.gui.graphing import (
    compute_graph_ranges_for_width,
    GraphDisplayConfigBase,
    GraphRanges,
    GraphRenderOptions,
    GraphTitleFormat,
)
from cmk.gui.i18n import _
from cmk.gui.type_defs import SizeMM, SizePT

from ._wire import PngOptions, PngTexts


def get_mm_per_ex(font_size: float) -> SizeMM:
    return font_size / 3.0


class GraphDisplayConfigImage(GraphDisplayConfigBase):
    size: tuple[float, float] = (70, 16)
    show_title: bool = True

    @field_validator("show_title", mode="before")
    @classmethod
    def _show_inline_title_above_the_graph(cls, value: object) -> object:
        # An image has no title on the graph area, so a report's "inline" title is shown
        # above it as usual.
        return True if value == "inline" else value


def png_options(config: GraphDisplayConfigImage) -> PngOptions:
    return PngOptions(
        size=config.size,
        font_size=config.font_size,
        show_title=config.show_title,
        show_legend=config.show_legend,
        show_vertical_axis=config.show_vertical_axis,
        show_time_axis=config.show_time_axis,
        show_graph_time=config.show_graph_time,
    )


def png_texts() -> PngTexts:
    return PngTexts(
        minimum=_("Min"),
        maximum=_("Max"),
        average=_("Average"),
        last=_("Last"),
        # xgettext: no-python-format
        # astrein: disable=localization-named-placeholder
        date_format=_("%Y-%m-%d"),
        caption=_("for %(date_range)s, resolution: %(resolution)s"),
    )


def compute_image_graph_ranges(
    display_config: GraphDisplayConfigImage, start_time: int, end_time: int
) -> GraphRanges:
    mm_per_ex = get_mm_per_ex(display_config.font_size)
    width_mm = display_config.size[0] * mm_per_ex
    return compute_graph_ranges_for_width(width_mm, start_time, end_time)


def graph_image_render_options(
    api_request: Mapping[str, object] | None = None,
) -> GraphRenderOptions:
    graph_render_options = GraphRenderOptions(
        font_size=SizePT(8.0),
        resizable=False,
        show_controls=False,
        title_format=GraphTitleFormat(
            plain=True,
            add_host_name=False,
            add_host_alias=False,
            add_service_description=True,
        ),
        size=(80, 30),
        show_title=True,
        border_width=0.05,
    )
    if api_request and (render_opts := api_request.get("render_options")):
        if not isinstance(render_opts, dict):
            raise TypeError(f"render_options must be a dict, got {type(render_opts)}")
        graph_render_options = graph_render_options.model_copy(update=render_opts)

    return graph_render_options
