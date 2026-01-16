#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Annotated, assert_never, Literal, override, Self

from annotated_types import Ge
from pydantic_core import ErrorDetails

from cmk.gui.dashboard import dashlet_registry, GROW, MAX
from cmk.gui.dashboard.type_defs import DashletConfig, DashletPosition, DashletSize
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.type_defs import DashboardEmbeddedViewSpec, VisualContext

from .type_defs import AnnotatedInfoName
from .widget_content import content_from_internal, WidgetContent

type ApiRenderMode = Literal["hidden", "with_background", "without_background"]


@api_model
class WidgetTitle:
    text: str = api_field(description="The title of the widget.")
    url: str | ApiOmitted = api_field(
        description="Optional URL the title should link to.",
        default_factory=ApiOmitted,
    )
    render_mode: ApiRenderMode = api_field(
        description="How the title should be rendered.",
        # default="with_background",
    )

    @staticmethod
    def _render_mode_from_internal(show_title: bool | Literal["transparent"]) -> ApiRenderMode:
        if isinstance(show_title, bool):
            return "with_background" if show_title else "hidden"
        if show_title == "transparent":
            return "without_background"
        raise ValueError(f"Invalid show_title value: {show_title}")

    @staticmethod
    def render_mode_to_internal(render_mode: ApiRenderMode) -> bool | Literal["transparent"]:
        match render_mode:
            case "hidden":
                return False
            case "with_background":
                return True
            case "without_background":
                return "transparent"
            case x:
                assert_never(x)

    @classmethod
    def from_internal(cls, config: DashletConfig) -> Self:
        return cls(
            text=config.get("title", "$DEFAULT_TITLE$"),
            url=config.get("title_url", ApiOmitted()),
            render_mode=cls._render_mode_from_internal(config.get("show_title", True)),
        )


@api_model
class WidgetRelativeGridPosition:
    # if x & y > 0, anchor top left
    # if x <= 0, y <= 0, anchor bottom right
    # if x <= 0, anchor top right
    # if y <= 0, anchor bottom left
    x: int = api_field(description="X position of the widget.")
    y: int = api_field(description="Y position of the widget.")

    @classmethod
    def from_internal(cls, size: DashletPosition) -> Self:
        return cls(x=size[0], y=size[1])

    def to_internal(self) -> DashletPosition:
        return self.x, self.y


# NOTE: mypy can't handle a union of Literal and Annotated, unless they are split up like this
type _PositiveInt = Annotated[int, Ge(1)]
type WidgetSizeValue = Literal["auto", "max"] | _PositiveInt


@api_model
class WidgetRelativeGridSize:
    width: WidgetSizeValue = api_field(description="Width of the widget.")
    height: WidgetSizeValue = api_field(description="Height of the widget.")

    @staticmethod
    def _size_value_from_internal(value: int) -> WidgetSizeValue:
        if value == GROW:
            return "auto"
        if value == MAX:
            return "max"
        if value < 1:
            raise ValueError(f"Invalid size value: {value}, must be >= 1, 'auto' or 'max'.")
        return value

    @staticmethod
    def _size_value_to_internal(value: WidgetSizeValue) -> int:
        if value == "auto":
            return GROW
        if value == "max":
            return MAX
        return value

    @classmethod
    def from_internal(cls, size: DashletSize) -> Self:
        return cls(
            width=cls._size_value_from_internal(size[0]),
            height=cls._size_value_from_internal(size[1]),
        )

    def to_internal(self) -> DashletSize:
        return (
            self._size_value_to_internal(self.width),
            self._size_value_to_internal(self.height),
        )


@api_model
class WidgetRelativeGridLayout:
    type: Literal["relative_grid"] = api_field(
        description="This setting must be in sync with the dashboards layout.",
    )
    position: WidgetRelativeGridPosition = api_field(description="Position of the widget.")
    size: WidgetRelativeGridSize = api_field(description="Size of the widget.")

    @classmethod
    def from_internal(cls, config: DashletConfig) -> Self:
        return cls(
            type="relative_grid",
            position=WidgetRelativeGridPosition.from_internal(config["position"]),
            size=WidgetRelativeGridSize.from_internal(config["size"]),
        )


@api_model
class WidgetGeneralSettings:
    title: WidgetTitle = api_field(description="Title settings for the widget.")
    render_background: bool = api_field(
        description="Whether the widget should render a gray background.",
        # default=True,
    )


@api_model
class _BaseWidget:
    general_settings: WidgetGeneralSettings = api_field(
        description="General settings for the widget.",
        example={
            "title": {
                "text": "My Widget",
                "url": "https://example.com",
                "render_mode": "with-background",
            },
            "render_background": True,
        },
    )
    content: WidgetContent = api_field(
        description="Content of the widget.",
        example={"type": "static_text", "text": "This is a static text widget."},
    )


@api_model
class BaseWidgetRequest(_BaseWidget, ABC):
    filters: VisualContext = api_field(
        description="Active filters in the format filter_id -> (variable -> value)",
    )

    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        embedded_views: Mapping[str, DashboardEmbeddedViewSpec],
    ) -> Iterable[ErrorDetails]:
        """Run additional validations that depends on the config."""
        yield from self.content.iter_validation_errors(
            location + ("content", self.content.type),
            context,
            embedded_views=embedded_views,
        )

    def _to_internal_without_layout(self) -> DashletConfig:
        config = self.content.to_internal()
        if not isinstance(self.general_settings.title, ApiOmitted):
            config["title"] = self.general_settings.title.text
            config["show_title"] = WidgetTitle.render_mode_to_internal(
                self.general_settings.title.render_mode
            )
            if not isinstance(self.general_settings.title.url, ApiOmitted):
                config["title_url"] = self.general_settings.title.url

        dashlet_type = dashlet_registry[config["type"]]
        config["single_infos"] = dashlet_type.single_infos()
        config["context"] = self.filters
        config.setdefault("reload_on_resize", False)
        config["background"] = self.general_settings.render_background
        return config

    @abstractmethod
    def to_internal(self) -> DashletConfig:
        pass


@api_model
class RelativeGridWidgetRequest(BaseWidgetRequest):
    layout: WidgetRelativeGridLayout = api_field(
        description="Layout of the widget.",
        example={
            "type": "relative_grid",
            "position": {"x": 0, "y": 0},
            "size": {"width": 2, "height": 1},
        },
    )

    @override
    def to_internal(self) -> DashletConfig:
        config = self._to_internal_without_layout()
        config["position"] = self.layout.position.to_internal()
        config["size"] = self.layout.size.to_internal()
        return config


@api_model
class WidgetFilterContext:
    uses_infos: list[AnnotatedInfoName] = api_field(
        description=(
            "A list of info names that this widget content uses. "
            "This is used to determine the available filters for the widget."
        )
    )
    filters: VisualContext = api_field(
        description="Active filters in the format filter_id -> (variable -> value)"
    )

    @classmethod
    def from_internal(cls, config: DashletConfig) -> Self:
        return cls(
            uses_infos=determine_widget_filter_used_infos(config),
            filters=config.get("context", {}),
        )


@api_model
class BaseWidgetResponse(_BaseWidget):
    filter_context: WidgetFilterContext = api_field(
        description="The filter context for the widget.",
    )


@api_model
class RelativeGridWidgetResponse(BaseWidgetResponse):
    layout: WidgetRelativeGridLayout = api_field(
        description="Layout of the widget.",
        example={
            "type": "relative_grid",
            "position": {"x": 0, "y": 0},
            "size": {"width": 2, "height": 1},
        },
    )

    @classmethod
    def from_internal(cls, config: DashletConfig) -> Self:
        return cls(
            general_settings=WidgetGeneralSettings(
                title=WidgetTitle.from_internal(config),
                render_background=config.get("background", True),
            ),
            content=content_from_internal(config),
            filter_context=WidgetFilterContext.from_internal(config),
            layout=WidgetRelativeGridLayout.from_internal(config),
        )


def determine_widget_filter_used_infos(
    widget_config: DashletConfig,
) -> list[AnnotatedInfoName]:
    dashlet_type = dashlet_registry[widget_config["type"]]
    dashlet = dashlet_type(widget_config)
    return list(dashlet.infos())
