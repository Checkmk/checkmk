#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container
from typing import Literal, Self, Unpack

from pydantic import BaseModel, TypeAdapter

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import (
    GraphRenderOptionsBase,
    GraphRenderOptionsVS,
    GraphTitleFormatVS,
    SizeMM,
    SizePT,
)


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


class GraphRenderOptions(GraphRenderOptionsBase, total=False):
    title_format: GraphTitleFormat


def graph_grender_options_from_vs(options_vs: GraphRenderOptionsVS) -> GraphRenderOptions:
    # no assignment expressions due to https://github.com/pylint-dev/pylint/issues/8486
    title_format_vs = options_vs.get("title_format")
    return TypeAdapter(GraphRenderOptions).validate_python(
        options_vs
        | (
            {"title_format": GraphTitleFormat.from_vs(title_format_vs)}
            if title_format_vs is not None
            else {}
        )
    )


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
    size: tuple[int, int] = (70, 16)
    title_format: GraphTitleFormat = GraphTitleFormat(
        plain=True,
        add_host_name=False,
        add_host_alias=False,
        add_service_description=False,
    )
    vertical_axis_width: Literal["fixed"] | tuple[Literal["explicit"], SizePT] = "fixed"


class GraphRenderConfig(GraphRenderConfigBase):
    explicit_title: str | None = None
    foreground_color: str
    onclick: str | None = None

    @classmethod
    def from_user_context_and_options(
        cls,
        user: LoggedInUser,
        theme_id: str,
        **options: Unpack[GraphRenderOptions],
    ) -> Self:
        return cls(
            foreground_color="#ffffff" if theme_id == "modern-dark" else "#000000",
            **_set_user_specific_size(options, user),
        )


class GraphRenderConfigImage(GraphRenderConfigBase):
    background_color: str = "#f8f4f0"
    canvas_color: str = "#ffffff"
    foreground_color: str = "#000000"

    @classmethod
    def from_user_context_and_options(
        cls,
        user: LoggedInUser,
        **options: Unpack[GraphRenderOptions],
    ) -> Self:
        return cls(**_set_user_specific_size(options, user))


def _set_user_specific_size(options: GraphRenderOptions, user: LoggedInUser) -> GraphRenderOptions:
    if "size" in options:
        return options
    if user_specific_size := user.load_file("graph_size", None):
        return options | GraphRenderOptions(size=user_specific_size)
    return options
