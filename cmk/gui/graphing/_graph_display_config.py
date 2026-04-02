#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container
from typing import Literal, Self

from pydantic import BaseModel

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import (
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


class GraphRenderOptions(BaseModel):
    border_width: SizeMM | None = None
    color_gradient: float | None = None
    editing: bool | None = None
    fixed_timerange: bool | None = None
    font_size: SizePT | None = None
    interaction: bool | None = None
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
    vertical_axis_width: Literal["fixed"] | tuple[Literal["explicit"], SizePT] | None = None

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
    size: tuple[float, float] = (70, 16)

    def update_from_options(self, options: GraphRenderOptions) -> Self:
        return self.model_copy(
            update={
                k: v for k, v in options.dump_set_fields().items() if k in type(self).model_fields
            },
        )


class GraphDisplayConfigHTML(_GraphDisplayConfigBase):
    color_gradient: float = 20.0
    editing: bool = False
    explicit_title: str | None = None
    fixed_timerange: bool = False
    foreground_color: str = "#000000"
    interaction: bool = True
    legend_max_height_px: int | None = None
    preview: bool = False
    resizable: bool = True
    show_controls: bool = True
    show_pin: bool = True
    show_time_range_previews: bool = True
    show_title: bool | Literal["inline"] = True
    title_format: GraphTitleFormat = _DEFAULT_TITLE_FORMAT

    @classmethod
    def from_user_context_and_options(
        cls,
        user: LoggedInUser,
        theme_id: str,
        options: GraphRenderOptions,
    ) -> Self:
        return cls.model_validate(
            _set_user_specific_size(options, user).dump_set_fields()
            | {"foreground_color": "#ffffff" if theme_id == "modern-dark" else "#000000"},
        )


class GraphDisplayConfigImage(_GraphDisplayConfigBase):
    border_width: SizeMM = 0.05
    show_title: bool = True
    title_format: GraphTitleFormat = _DEFAULT_TITLE_FORMAT
    vertical_axis_width: Literal["fixed"] | tuple[Literal["explicit"], SizePT] = "fixed"
    background_color: str = "#f8f4f0"
    canvas_color: str = "#ffffff"
    foreground_color: str = "#000000"

    @classmethod
    def from_user_context_and_options(
        cls,
        user: LoggedInUser,
        options: GraphRenderOptions,
    ) -> Self:
        return cls.model_validate(_set_user_specific_size(options, user).dump_set_fields())


def _set_user_specific_size(
    options: GraphRenderOptions,
    user: LoggedInUser,
) -> GraphRenderOptions:
    if options.size:
        return options
    if user_specific_size := user.load_file("graph_size", None):
        options_with_updated_size = options.model_copy()
        options_with_updated_size.size = user_specific_size
        return options_with_updated_size
    return options
