#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Annotated, assert_never, Literal

from pydantic import Discriminator
from pydantic_core import ErrorDetails

from cmk.gui.dashboard.type_defs import (
    ContextualLinkConfig,
    ContextualLinkInheritedConfig,
    ContextualLinkNoneConfig,
    ContextualLinkTargetType,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import VisualName
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals.type import visual_type_registry


@api_model
class VisualLocation:
    type: ContextualLinkTargetType = api_field(description="The kind of the target visual.")
    name: VisualName = api_field(description="The name of the target visual.")


@api_model
class ContextualLinkNone:
    type: Literal["none"] = api_field(description="The widget links nowhere.")


@api_model
class ContextualLinkDefault:
    type: Literal["default"] = api_field(description="The widget links to its built-in target.")


@api_model
class ContextualLinkInherited:
    type: Literal["inherited"] = api_field(
        description="The widget links to one visual and carries only what its elements know."
    )
    location: VisualLocation = api_field(description="The target visual.")
    include_context: bool = api_field(
        description="Whether the link carries the widget's effective filter context."
    )
    include_time_range: bool = api_field(
        description="Whether the link carries the dashboard's time range."
    )
    show_filter_form: bool = api_field(
        description="Whether the target opens with its filter form shown."
    )


type ContextualLinkSpec = Annotated[
    ContextualLinkNone | ContextualLinkDefault | ContextualLinkInherited,
    Discriminator("type"),
]


def contextual_link_to_internal(link: ContextualLinkSpec) -> ContextualLinkConfig | None:
    """The stored form of a link configuration; None for a `default` link."""
    match link:
        case ContextualLinkNone():
            return ContextualLinkNoneConfig(type="none")
        case ContextualLinkInherited():
            return ContextualLinkInheritedConfig(
                type="inherited",
                location=(link.location.type, link.location.name),
                include_context=link.include_context,
                include_time_range=link.include_time_range,
                show_filter_form=link.show_filter_form,
            )
        case ContextualLinkDefault():
            return None
        case unreachable:
            assert_never(unreachable)


def contextual_link_from_internal(config: ContextualLinkConfig | None) -> ContextualLinkSpec:
    """The API form of a stored link configuration."""
    if config is None:
        return ContextualLinkDefault(type="default")
    if config["type"] == "none":
        return ContextualLinkNone(type="none")
    if config["type"] == "inherited":
        return ContextualLinkInherited(
            type="inherited",
            location=_location_from_internal(config["location"]),
            include_context=config["include_context"],
            include_time_range=config["include_time_range"],
            show_filter_form=config["show_filter_form"],
        )
    assert_never(config)


_TARGET_TITLES: Mapping[ContextualLinkTargetType, str] = {
    "views": "View",
    "dashboards": "Dashboard",
}


def iter_contextual_link_target_errors(
    link: ContextualLinkSpec,
    location: tuple[str | int, ...],
    user_permissions: UserPermissions,
) -> Iterator[ErrorDetails]:
    """The write-time errors of the link targets outside the writer's permitted visuals."""
    match link:
        case ContextualLinkInherited():
            targets = [(location + ("inherited", "location"), link.location)]
        case ContextualLinkNone() | ContextualLinkDefault():
            targets = []
        case unreachable:
            assert_never(unreachable)
    for target_location, target in targets:
        visual_type = visual_type_registry[target.type]()
        if target.name not in visual_type.permitted_visuals(
            visual_type.visuals(), user_permissions
        ):
            yield ErrorDetails(
                type="value_error",
                msg=(
                    f"{_TARGET_TITLES[target.type]} '{target.name}' does not exist or you don't"
                    " have permission to see it."
                ),
                loc=target_location,
                input=target.name,
            )


def _location_from_internal(
    location: tuple[ContextualLinkTargetType, VisualName],
) -> VisualLocation:
    return VisualLocation(type=location[0], name=location[1])
