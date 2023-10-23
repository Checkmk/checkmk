#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, Self

from pydantic import BaseModel

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import GraphRenderOptions, GraphTitleFormat, SizeMM, SizePT


class GraphRenderConfigBase(BaseModel):
    border_width: SizeMM = 0.05
    color_gradient: float = 20.0
    editing: bool = False
    fixed_timerange: bool = False
    font_size: SizePT = SizePT(8.0)
    interaction: bool = True
    preview: bool = False
    resizable: bool = True
    show_controls: bool = True
    show_graph_time: bool = True
    show_legend: bool = True
    show_margin: bool = True
    show_pin: bool = True
    show_time_axis: bool = True
    show_time_range_previews: bool = True
    show_title: bool | Literal["inline"] = True
    show_vertical_axis: bool = True
    title_format: Sequence[GraphTitleFormat] = ("plain",)
    vertical_axis_width: Literal["fixed"] | tuple[Literal["explicit"], SizePT] = "fixed"


class GraphRenderConfig(GraphRenderConfigBase):
    explicit_title: str | None = None
    foreground_color: str
    onclick: str | None = None
    size: tuple[int, int]

    @classmethod
    def from_render_options_and_context(
        cls,
        options: GraphRenderOptions,
        user: LoggedInUser,
        theme_id: str,
    ) -> Self:
        return cls(
            foreground_color="#ffffff" if theme_id == "modern-dark" else "#000000",
            **_set_user_specific_size(options, user),
        )


class GraphRenderConfigImage(GraphRenderConfigBase):
    background_color: str = "#f8f4f0"
    canvas_color: str = "#ffffff"
    foreground_color: str = "#000000"
    size: tuple[int, int]

    @classmethod
    def from_render_options_and_context(
        cls,
        options: GraphRenderOptions,
        user: LoggedInUser,
    ) -> Self:
        return cls(**_set_user_specific_size(options, user))


def _set_user_specific_size(options: GraphRenderOptions, user: LoggedInUser) -> GraphRenderOptions:
    if "size" in options:
        return options
    return options | GraphRenderOptions(size=user.load_file("graph_size", (70, 16)))
