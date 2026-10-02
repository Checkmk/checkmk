#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Annotated, assert_never, Literal

from annotated_types import MinLen
from pydantic import Discriminator, StringConstraints, WithJsonSchema
from pydantic_core import ErrorDetails

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.dashboard.type_defs import (
    ContextFilterConfig,
    ContextualLinkConfig,
    ContextualLinkCustomConfig,
    ContextualLinkEntryConfig,
    ContextualLinkInheritedConfig,
    ContextualLinkLocationConfig,
    ContextualLinkNoneConfig,
    ContextualLinkTargetType,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import AnnotatedUserId, Visual, VisualName
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals.type import visual_type_registry

from ...store import get_permitted_dashboards, get_permitted_dashboards_by_owners
from .context_filters import (
    AggregateHostContextFilter,
    AggregateServiceContextFilter,
    ObjectHostContextFilter,
    ObjectServiceContextFilter,
)

# The request and the response share this model, so both directions state the same schema.
_OwnerId = Annotated[AnnotatedUserId, WithJsonSchema({"type": "string"})]


@api_model
class VisualLocation:
    type: ContextualLinkTargetType = api_field(description="The kind of the target visual.")
    name: VisualName = api_field(description="The name of the target visual.")
    owner: _OwnerId | None = api_field(
        description=(
            "The owner of the target copy, an empty string for the built-in one. With null, each"
            " viewer opens the copy the name resolves to, as the target page does without an owner."
        )
    )


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


@api_model
class ContextualLink[F]:
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = api_field(
        description="The title of the link."
    )
    location: VisualLocation = api_field(description="The target visual.")
    filters: list[F] = api_field(
        description="The filters the link carries, each valued from the clicked element."
    )
    include_context: bool = api_field(
        description="Whether the link carries the widget's effective filter context."
    )
    include_time_range: bool = api_field(
        description="Whether the link carries the dashboard's time range."
    )
    show_filter_form: bool = api_field(
        description="Whether the target opens with its filter form shown."
    )


@api_model
class ContextualLinkCustom[F]:
    type: Literal["custom"] = api_field(
        description="The widget links to the configured visuals with the configured filters."
    )
    links: Annotated[list[ContextualLink[F]], MinLen(1)] = api_field(
        description="The links, in the order they are offered."
    )


type ContextualLinkSpec[F] = Annotated[
    ContextualLinkNone | ContextualLinkDefault | ContextualLinkInherited | ContextualLinkCustom[F],
    Discriminator("type"),
]

type AnyContextualLinkSpec = (
    ContextualLinkSpec[AggregateHostContextFilter]
    | ContextualLinkSpec[AggregateServiceContextFilter]
    | ContextualLinkSpec[ObjectHostContextFilter]
    | ContextualLinkSpec[ObjectServiceContextFilter]
)


def contextual_link_to_internal(
    link: AnyContextualLinkSpec,
) -> ContextualLinkConfig | None:
    """The stored form of a link configuration; None for a `default` link."""
    match link:
        case ContextualLinkNone():
            return ContextualLinkNoneConfig(type="none")
        case ContextualLinkInherited():
            return ContextualLinkInheritedConfig(
                type="inherited",
                location=_location_to_internal(link.location),
                include_context=link.include_context,
                include_time_range=link.include_time_range,
                show_filter_form=link.show_filter_form,
            )
        case ContextualLinkCustom():
            return ContextualLinkCustomConfig(
                type="custom",
                links=[
                    ContextualLinkEntryConfig(
                        title=entry.title,
                        location=_location_to_internal(entry.location),
                        filters=[ContextFilterConfig(filter_id=f.filter_id) for f in entry.filters],
                        include_context=entry.include_context,
                        include_time_range=entry.include_time_range,
                        show_filter_form=entry.show_filter_form,
                    )
                    for entry in link.links
                ],
            )
        case ContextualLinkDefault():
            return None
        case unreachable:
            assert_never(unreachable)


def contextual_link_from_internal[F](
    config: ContextualLinkConfig | None, filter_from_internal: Callable[[ContextFilterConfig], F]
) -> ContextualLinkSpec[F]:
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
    if config["type"] == "custom":
        return ContextualLinkCustom(
            type="custom",
            links=[
                ContextualLink(
                    title=entry["title"],
                    location=_location_from_internal(entry["location"]),
                    filters=[filter_from_internal(f) for f in entry["filters"]],
                    include_context=entry["include_context"],
                    include_time_range=entry["include_time_range"],
                    show_filter_form=entry["show_filter_form"],
                )
                for entry in config["links"]
            ],
        )
    assert_never(config)


_TARGET_TITLES: Mapping[ContextualLinkTargetType, str] = {
    "views": "View",
    "dashboards": "Dashboard",
}


def iter_contextual_link_errors(
    link: AnyContextualLinkSpec,
    location: tuple[str | int, ...],
    user_permissions: UserPermissions,
) -> Iterator[ErrorDetails]:
    """The write-time errors of a link: targets outside the writer's permitted visuals, and
    filters a custom link carries twice."""
    targets: list[tuple[tuple[str | int, ...], VisualLocation]]
    match link:
        case ContextualLinkInherited():
            targets = [(location + ("inherited", "location"), link.location)]
        case ContextualLinkCustom():
            targets = []
            entries: Sequence[
                ContextualLink[AggregateHostContextFilter]
                | ContextualLink[AggregateServiceContextFilter]
                | ContextualLink[ObjectHostContextFilter]
                | ContextualLink[ObjectServiceContextFilter]
            ] = link.links
            for index, entry in enumerate(entries):
                entry_location = location + ("custom", "links", index)
                targets.append((entry_location + ("location",), entry.location))
                yield from _iter_duplicate_filter_errors(
                    [f.filter_id for f in entry.filters], entry_location + ("filters",)
                )
        case ContextualLinkNone() | ContextualLinkDefault():
            targets = []
        case unreachable:
            assert_never(unreachable)
    for target_location, target in targets:
        if not _is_permitted(target, user_permissions):
            of_owner = "" if target.owner is None else f" of '{target.owner}'"
            yield ErrorDetails(
                type="value_error",
                msg=(
                    f"{_TARGET_TITLES[target.type]} '{target.name}'{of_owner} does not exist or"
                    " you don't have permission to see it."
                ),
                loc=target_location,
                input=target.name,
            )


def _iter_duplicate_filter_errors(
    filter_ids: Sequence[str], location: tuple[str | int, ...]
) -> Iterator[ErrorDetails]:
    for index, filter_id in enumerate(filter_ids):
        if filter_id in filter_ids[:index]:
            yield ErrorDetails(
                type="value_error",
                msg=f"The filter '{filter_id}' is listed more than once.",
                loc=location + (index,),
                input=filter_id,
            )


def permitted_copies(
    location: VisualLocation, user_permissions: UserPermissions
) -> Mapping[UserId, Visual]:
    """The copies of the target visual the user may pick, by owner.

    For dashboards, this is the set the dashboard metadata lists. It comes from the logged-in
    user's dashboard store, not from `user_permissions`, and holds every user's copy for a user
    who may edit foreign dashboards.
    """
    copies: Mapping[UserId, Visual]
    if location.type == "dashboards":
        copies = get_permitted_dashboards_by_owners().get(location.name, {})
    else:
        copies = visuals.available_by_owner(
            location.type, visual_type_registry[location.type]().visuals(), user_permissions
        ).get(location.name, {})
    return copies


def resolved_copy(location: VisualLocation, user_permissions: UserPermissions) -> Visual | None:
    """The copy the name resolves to for the logged-in user, which a link without owner opens."""
    if location.type == "dashboards":
        return get_permitted_dashboards().get(location.name)
    return visuals.available(
        location.type, visual_type_registry[location.type]().visuals(), user_permissions
    ).get(location.name)


def _is_permitted(location: VisualLocation, user_permissions: UserPermissions) -> bool:
    if location.owner is None:
        return resolved_copy(location, user_permissions) is not None
    return location.owner in permitted_copies(location, user_permissions)


def _location_to_internal(location: VisualLocation) -> ContextualLinkLocationConfig:
    if location.owner is None:
        return location.type, location.name
    return location.type, location.name, location.owner


def _location_from_internal(location: ContextualLinkLocationConfig) -> VisualLocation:
    match location:
        case (target_type, name):
            return VisualLocation(type=target_type, name=name, owner=None)
        case (target_type, name, owner):
            return VisualLocation(type=target_type, name=name, owner=owner)
