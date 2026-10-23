#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from typing import (
    Annotated,
    assert_never,
    get_args,
    get_origin,
    get_type_hints,
    Literal,
    TypeAliasType,
)

from annotated_types import MinLen
from pydantic import Discriminator, StringConstraints, TypeAdapter, WithJsonSchema
from pydantic_core import ErrorDetails

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.dashboard.type_defs import (
    ContextFilterConfig,
    ContextualLinkConfig,
    ContextualLinkCustomConfig,
    ContextualLinkInheritedConfig,
    ContextualLinkNoneConfig,
    ContextualLinkTargetType,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import (
    AnnotatedUserId,
    ContextualLinkEntryConfig,
    ContextualLinkLocationConfig,
    FilterName,
    InfoName,
    Visual,
    VisualName,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.drilldown_filters import exceeded_aux_tag_limits, filter_key
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.filter.drilldowns import AuxTagKey, FilterKey, LabelKey, TagGroupKey
from cmk.gui.visuals.type import visual_type_registry
from cmk.ruleset_matcher.tags import TagConfig

from ...store import get_permitted_dashboards, get_permitted_dashboards_by_owners
from .context_filters import (
    AggregateHostContextFilter,
    AggregateServiceContextFilter,
    context_filter_to_internal,
    ObjectHostContextFilter,
    ObjectServiceContextFilter,
)

type ConfigurableLinkMode = Literal["default", "inherited", "custom"]
_MODES_ADAPTER: TypeAdapter[list[ConfigurableLinkMode]] = TypeAdapter(list[ConfigurableLinkMode])


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


@api_model
class LabelKeyOption:
    type: Literal["label"] = api_field(description="The filter takes a label key.")
    object_type: Literal["host", "service"] = api_field(
        description="Whose labels the key names: the host's or the service's."
    )


@api_model
class TagGroupKeyOption:
    type: Literal["tag_group"] = api_field(description="The filter takes a tag group.")


@api_model
class AuxTagKeyOption:
    type: Literal["aux_tag"] = api_field(description="The filter takes auxiliary tags.")
    max_count: int = api_field(description="How many auxiliary tags a link may carry.")


type FilterKeyOption = Annotated[
    LabelKeyOption | TagGroupKeyOption | AuxTagKeyOption, Discriminator("type")
]


@api_model
class ContextualLinkOptions:
    modes: list[ConfigurableLinkMode] = api_field(
        description="The modes the widget offers besides linking nowhere."
    )
    filters: list[FilterName] = api_field(
        description="The filters a custom link of the widget may carry."
    )
    filter_keys: dict[FilterName, FilterKeyOption] = api_field(
        description=(
            "The key each filter that needs one takes: a label key, a tag group or an auxiliary"
            " tag."
        )
    )
    single_infos: list[InfoName] = api_field(
        description=(
            "The objects a click on the widget names, such as the host. A target restricted to a "
            "single object only fits a widget whose clicks name that object."
        )
    )


def contextual_link_options(link_type: object) -> ContextualLinkOptions:
    """The options a widget's `contextual_link` type accepts, a spec parameterized with the
    filter set of its clicks.

    Read off the types, so the options cannot drift from what the API accepts.
    """
    spec = get_origin(link_type)
    if not isinstance(spec, TypeAliasType):
        raise TypeError(f"Not a contextual link type: {link_type!r}")
    accepted = [
        filter_id
        for filter_type in get_args(link_type)
        for member in _members(filter_type)
        for filter_id in _literals(member, "filter_id")
    ]
    modes = _MODES_ADAPTER.validate_python(
        [mode for arm in _members(spec) for mode in _literals(arm, "type") if mode != "none"]
    )
    offered = (
        [
            filter_id
            for filter_id in accepted
            if filter_id in filter_registry and filter_registry[filter_id].available()
        ]
        if "custom" in modes
        else []
    )
    return ContextualLinkOptions(
        modes=modes,
        filters=offered,
        filter_keys={
            filter_id: option
            for filter_id in offered
            if (option := _key_option(filter_key(filter_id))) is not None
        },
        # An object filter set holds the name filter of exactly the objects its click names.
        single_infos=[info for info in ("host", "service") if info in accepted],
    )


def _key_option(key: FilterKey | None) -> FilterKeyOption | None:
    match key:
        case LabelKey(object_type=object_type):
            return LabelKeyOption(type="label", object_type=object_type)
        case TagGroupKey():
            return TagGroupKeyOption(type="tag_group")
        case AuxTagKey(max_count=max_count):
            return AuxTagKeyOption(type="aux_tag", max_count=max_count)
        case None:
            return None


def _members(alias: TypeAliasType) -> tuple[object, ...]:
    """The members of an alias of the form `Annotated[A | B | ..., Discriminator(...)]`."""
    members: tuple[object, ...] = get_args(get_args(alias.__value__)[0])
    return members


def _literals(model: object, field: str) -> list[str]:
    return [str(value) for value in get_args(get_type_hints(get_origin(model) or model)[field])]


def contextual_link_to_internal(
    link: AnyContextualLinkSpec,
) -> ContextualLinkConfig | None:
    """The stored form of a link configuration; None for a `default` link."""
    match link:
        case ContextualLinkNone():
            return ContextualLinkNoneConfig(type="none")
        case ContextualLinkInherited():
            return _inherited_to_internal(link)
        case ContextualLinkCustom():
            return ContextualLinkCustomConfig(
                type="custom",
                links=[
                    ContextualLinkEntryConfig(
                        title=entry.title,
                        location=_location_to_internal(entry.location),
                        filters=[context_filter_to_internal(f) for f in entry.filters],
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


def _inherited_to_internal(link: ContextualLinkInherited) -> ContextualLinkInheritedConfig:
    return ContextualLinkInheritedConfig(
        type="inherited",
        location=_location_to_internal(link.location),
        include_context=link.include_context,
        include_time_range=link.include_time_range,
        show_filter_form=link.show_filter_form,
    )


def contextual_link_from_internal[F](
    config: ContextualLinkConfig | None, filter_adapter: TypeAdapter[F]
) -> ContextualLinkSpec[F]:
    """The API form of a stored link configuration."""
    if config is None:
        return ContextualLinkDefault(type="default")
    if config["type"] == "none":
        return ContextualLinkNone(type="none")
    if config["type"] == "inherited":
        return _inherited_from_internal(config)
    if config["type"] == "custom":
        return ContextualLinkCustom(
            type="custom",
            links=[
                ContextualLink(
                    title=entry["title"],
                    location=location_from_internal(entry["location"]),
                    filters=[filter_adapter.validate_python(f) for f in entry["filters"]],
                    include_context=entry["include_context"],
                    include_time_range=entry["include_time_range"],
                    show_filter_form=entry["show_filter_form"],
                )
                for entry in config["links"]
            ],
        )
    assert_never(config)


def _inherited_from_internal(config: ContextualLinkInheritedConfig) -> ContextualLinkInherited:
    return ContextualLinkInherited(
        type="inherited",
        location=location_from_internal(config["location"]),
        include_context=config["include_context"],
        include_time_range=config["include_time_range"],
        show_filter_form=config["show_filter_form"],
    )


_TARGET_TITLES: Mapping[ContextualLinkTargetType, str] = {
    "views": "View",
    "dashboards": "Dashboard",
}


def iter_contextual_link_errors(
    link: AnyContextualLinkSpec,
    location: tuple[str | int, ...],
    user_permissions: UserPermissions,
    tags: TagConfig,
) -> Iterator[ErrorDetails]:
    """The write-time errors of a link: a target the writer may not open, and a custom link's
    filter this edition lacks, listed twice, with a key the tag config lacks, or beyond what the
    target takes."""
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
                yield from _iter_filter_errors(
                    [context_filter_to_internal(f) for f in entry.filters],
                    entry_location + ("filters",),
                    tags,
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


def _iter_filter_errors(
    filters: Sequence[ContextFilterConfig], location: tuple[str | int, ...], tags: TagConfig
) -> Iterator[ErrorDetails]:
    for index, filter_config in enumerate(filters):
        filter_id, key = filter_config["filter_id"], filter_config.get("key")
        if filter_id not in filter_registry:
            msg = f"The filter '{filter_id}' does not exist in this edition."
        elif filter_config in filters[:index]:
            of_key = f" with the key '{key}'" if key else ""
            msg = f"The filter '{filter_id}' is listed more than once{of_key}."
        elif key is not None and (key_error := _key_error(filter_id, key, tags)) is not None:
            msg = key_error
        else:
            continue
        yield ErrorDetails(type="value_error", msg=msg, loc=location + (index,), input=filter_id)
    for max_count in exceeded_aux_tag_limits(f["filter_id"] for f in filters):
        yield ErrorDetails(
            type="value_error",
            msg=f"A link carries at most {max_count} auxiliary tags.",
            loc=location,
            input=[f["filter_id"] for f in filters],
        )


def _key_error(filter_id: FilterName, key: str, tags: TagConfig) -> str | None:
    """Why the key names nothing the filter takes, the way the view editor checks it."""
    match filter_key(filter_id):
        case LabelKey() if ":" in key:
            # A label is parsed as key:value, so a colon would end the key early.
            return f"The label key '{key}' must not contain a colon."
        case TagGroupKey() if key not in {group for group, _title in tags.get_tag_group_choices()}:
            return f"The tag group '{key}' does not exist."
        case AuxTagKey() if key not in {
            aux_tag for aux_tag, _title in tags.aux_tag_list.get_choices()
        }:
            return f"The auxiliary tag '{key}' does not exist."
        case _:
            return None


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


def location_from_internal(location: ContextualLinkLocationConfig) -> VisualLocation:
    match location:
        case (target_type, name):
            return VisualLocation(type=target_type, name=name, owner=None)
        case (target_type, name, owner):
            return VisualLocation(type=target_type, name=name, owner=owner)
