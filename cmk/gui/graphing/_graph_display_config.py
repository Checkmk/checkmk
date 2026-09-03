#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container
from typing import Literal, Self

from pydantic import BaseModel

from cmk.gui.type_defs import (
    GraphRenderOptionsVS,
    GraphTitleFormatVS,
    SizeMM,
    SizePT,
    VerticalAxisWidth,
)

# Pixels per "ex" graph-size unit: graph sizes are configured/stored in ex, this scales them to the
# CSS pixel dimensions used by both the legacy HTML renderer and the engine (Vue) graph group.
#
# TODO: This is not acurate! Rendering of the graphs is wrong especially when the font size is changed
# this does not lead to correct results. We should find a way to fix this. Otherwise the font size
# chaning of the graph rendering options won't work as expected.
HTML_SIZE_PER_EX = 11.0


def get_mm_per_ex(font_size: float) -> SizeMM:
    return font_size / 3.0


class GraphTitleFormat(BaseModel):
    plain: bool
    add_host_name: bool
    add_host_alias: bool
    add_service_description: bool

    @classmethod
    def from_vs(cls, title_format_vs: Container[GraphTitleFormatVS]) -> Self:
        return cls(
            plain="plain" in title_format_vs,
            add_host_name="add_host_name" in title_format_vs,
            add_host_alias="add_host_alias" in title_format_vs,
            add_service_description="add_service_description" in title_format_vs,
        )


class GraphRenderOptions(BaseModel):
    border_width: SizeMM | None = None
    # TODO CMK-33320
    # Kept for API/valuespec compatibility. The gradient rendering in the PDF backend was
    # deliberately disabled (linearGradient increased PDF size ~23×) and the field is no
    # longer consumed by any rendering path.
    color_gradient: float | None = None
    fixed_timerange: bool | None = None
    font_size: SizePT | None = None
    preview: bool | None = None
    resizable: bool | None = None
    show_controls: bool | None = None
    show_graph_time: bool | None = None
    show_legend: bool | None = None
    show_margin: bool | None = None
    show_pin: bool | None = None
    show_time_axis: bool | None = None
    show_time_range_previews: bool | None = None
    show_title: bool | Literal["inline"] | None = None
    show_vertical_axis: bool | None = None
    size: tuple[int, int] | None = None
    title_format: GraphTitleFormat | None = None
    vertical_axis_width: VerticalAxisWidth | None = None

    @classmethod
    def from_graph_render_options_vs(cls, render_options_vs: GraphRenderOptionsVS) -> Self:
        return cls.model_validate(
            render_options_vs
            | (
                {"title_format": GraphTitleFormat.from_vs(title_format_vs)}
                if (title_format_vs := render_options_vs.get("title_format"))
                else {}
            )
        )

    def dump_set_fields(self) -> dict[str, object]:
        return self.model_dump(exclude_none=True)


_DEFAULT_TITLE_FORMAT = GraphTitleFormat(
    plain=True,
    add_host_name=False,
    add_host_alias=False,
    add_service_description=False,
)


class _GraphDisplayConfigBase(BaseModel):
    font_size: SizePT = SizePT(8.0)
    show_graph_time: bool = True
    show_legend: bool = True
    show_margin: bool = True
    show_time_axis: bool = True
    show_vertical_axis: bool = True
    title_format: GraphTitleFormat = _DEFAULT_TITLE_FORMAT
    vertical_axis_width: VerticalAxisWidth = "fixed"

    def update_from_options(self, options: GraphRenderOptions) -> Self:
        return self.model_copy(
            update={
                k: v for k, v in options.dump_set_fields().items() if k in type(self).model_fields
            },
        )


class GraphDisplayConfigHTML(_GraphDisplayConfigBase):
    fixed_timerange: bool = False
    foreground_color: str = "#000000"
    preview: bool = False
    resizable: bool = True
    show_controls: bool = True
    show_pin: bool = True
    show_time_range_previews: bool = True
    show_title: bool | Literal["inline"] = True

    @classmethod
    def from_options(
        cls,
        theme_id: str,
        options: GraphRenderOptions,
    ) -> Self:
        return cls.model_validate(
            options.dump_set_fields()
            | {"foreground_color": "#ffffff" if theme_id == "modern-dark" else "#000000"},
        )


class GraphDisplayConfigImage(_GraphDisplayConfigBase):
    size: tuple[float, float] = (70, 16)
    border_width: SizeMM = 0.05
    show_title: bool = True
    background_color: str = "#f8f4f0"
    canvas_color: str = "#ffffff"
    foreground_color: str = "#000000"

    @classmethod
    def from_options(cls, options: GraphRenderOptions) -> Self:
        return cls.model_validate(options.dump_set_fields())


_DEFAULT_GRAPH_SIZE: tuple[float, float] = (70.0, 16.0)


def resolve_size(options: GraphRenderOptions) -> tuple[float, float]:
    """Determine the initial canvas size for a new interaction state.

    Priority: GraphRenderOptions.size → (70, 16) default. The per-user "graph_size"
    profile entry is gone with the renderer that was its only writer.
    """
    if options.size:
        return (float(options.size[0]), float(options.size[1]))
    return _DEFAULT_GRAPH_SIZE
