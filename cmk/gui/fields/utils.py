#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import functools
import typing
from typing import Any, Callable, List, Literal, NamedTuple, Optional, Type, TypedDict, TypeVar

from marshmallow import ValidationError

from livestatus import SiteId

from cmk.utils.tags import BuiltinTagConfig, TagGroup

# There is an implicit dependency introduced by the collect_attributes call which is evaluated
# at import time. To make it work as expected we need to import
# TODO: Clean this dependency on the plugins up by moving the plugins to cmk.gui.watolib
import cmk.gui.plugins.wato.builtin_attributes  # pylint: disable=unused-import
import cmk.gui.watolib.groups  # pylint: disable=unused-import
from cmk.gui import sites, watolib
from cmk.gui.fields.base import BaseSchema
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib.tags import load_tag_config

from cmk import fields


class Attr(NamedTuple):
    name: str
    mandatory: bool
    section: str
    description: str
    enum: Optional[List[Optional[str]]] = None
    field: Optional[fields.Field] = None


ObjectType = Literal["host", "folder", "cluster"]
ObjectContext = Literal["create", "update", "view"]


def collect_attributes(
    object_type: ObjectType,
    context: ObjectContext,
) -> List[Attr]:
    """Collect all attributes for a specific use case

    Use cases can be host or folder creation or updating.

    Args:
        object_type:
            Either 'host', 'folder' or 'cluster'

        context:
            Either 'create' or 'update'

    Returns:
        A list of attribute describing named-tuples.

    Examples:

        >>> attrs = collect_attributes('host', 'create')
        >>> assert len(attrs) > 10, len(attrs)

        >>> attrs = collect_attributes('host', 'update')
        >>> assert len(attrs) > 10, len(attrs)

        >>> attrs = collect_attributes('cluster', 'create')
        >>> assert len(attrs) > 10, len(attrs)

        >>> attrs = collect_attributes('cluster', 'update')
        >>> assert len(attrs) > 10, len(attrs)

        >>> attrs = collect_attributes('folder', 'create')
        >>> assert len(attrs) > 10, len(attrs)

        >>> attrs = collect_attributes('folder', 'update')
        >>> assert len(attrs) > 10

    To check the content of the list, uncomment this one.

        # >>> import pprint
        # >>> pprint.pprint(attrs)

    """
    something = TypeVar("something")

    def _ensure(optional: Optional[something]) -> something:
        if optional is None:
            raise ValueError
        return optional

    T = typing.TypeVar("T")

    def maybe_call(func: Optional[Callable[[], T]]) -> Optional[T]:
        if func is None:
            return None
        return func()

    # NOTE:
    #   We want to get all the topics, so we don't miss any attributes. We filter them later.
    #   new=True may also be new=False, it doesn't matter in this context.
    result = []
    for topic_id, topic_title in watolib.get_sorted_host_attribute_topics("always", new=True):
        for attr in watolib.get_sorted_host_attributes_by_topic(topic_id):
            if object_type == "folder" and not attr.show_in_folder():
                continue

            if context in ["create", "update"] and not attr.openapi_editable():
                continue

            help_text: str = strip_tags(attr.help()) or ""
            # TODO: what to do with attr.depends_on_tags()?
            attr_entry = Attr(
                name=attr.name(),
                description=help_text,
                section=topic_title,
                mandatory=attr.is_mandatory(),
                field=maybe_call(getattr(attr, "openapi_field", None)),
            )
            result.append(attr_entry)

    tag_config = load_tag_config()
    tag_config += BuiltinTagConfig()

    def _format(tag_id: Optional[str]) -> str:
        if tag_id is None:
            return "`null`"
        return f'`"{tag_id}"`'

    tag_group: TagGroup
    for tag_group in tag_config.tag_groups:
        description: List[str] = []
        if tag_group.help:
            description.append(tag_group.help)

        if tag_group.tags:
            description.append("Choices:")
            for tag in tag_group.tags:
                description.append(f" * {_format(tag.id)}: {tag.title}")

        allowed_ids = [tag.id for tag in tag_group.tags]
        if tag_group.is_checkbox_tag_group:
            allowed_ids.insert(0, None)

        result.append(
            Attr(
                name=_ensure(f"tag_{tag_group.id}"),
                section=tag_group.topic or "No topic",
                mandatory=False,
                description="\n\n".join(description),
                enum=allowed_ids,
                field=None,
            )
        )

    return result


def _field_from_attr(attr):
    """
    >>> field = _field_from_attr(
    ...     Attr(
    ...         name='simple_text',
    ...         mandatory=False,
    ...         description='Hurz!',
    ...         section='',
    ...         field=None,
    ...     )
    ... )
    >>> field.required
    False

    >>> field.metadata
    {'description': 'Hurz!'}

    >>> _attr = Attr(
    ...     name='time',
    ...     mandatory=True,
    ...     description='Hello World',
    ...     section='',
    ...     field=None,
    ... )
    >>> _field_from_attr(_attr)  # doctest: +ELLIPSIS
    <fields.String(...)>

    >>> _attr = Attr(
    ...     name='time',
    ...     mandatory=True,
    ...     description='Hello World',
    ...     section='',
    ...     field=None,
    ... )
    >>> schema = _field_from_attr(_attr)
    >>> schema  # doctest: +ELLIPSIS
    <fields.String(...)>

    Returns:

    """
    if attr.field is not None:
        return attr.field

    def site_exists(site_name: SiteId) -> None:
        if site_name not in sites.sitenames():
            raise ValidationError(f"Site {site_name!r} does not exist.")

    validators = {
        "site": site_exists,
    }

    class FieldParams(TypedDict, total=False):
        description: str
        required: bool
        enum: List[Optional[str]]
        validate: Callable[[Any], Any]
        allow_none: bool

    kwargs: FieldParams = {
        "required": attr.mandatory,
        "description": attr.description,
    }
    # If we assigned None to enum, this would lead to a broken OpenApi specification!
    if attr.enum is not None:
        kwargs["enum"] = attr.enum
        if None in attr.enum:
            kwargs["allow_none"] = True

    if attr.name in validators:
        kwargs["validate"] = validators[attr.name]

    return fields.String(**kwargs)


def _schema_from_dict(name, schema_dict) -> Type[BaseSchema]:
    dict_ = schema_dict.copy()
    dict_["cast_to_dict"] = True
    return type(name, (BaseSchema,), dict_)


@functools.lru_cache
def attr_openapi_schema(
    object_type: ObjectType,
    context: ObjectContext,
) -> Type[BaseSchema]:
    """

    Examples:

        Known attributes are allowed through:

            >>> schema_class = attr_openapi_schema("host", "create")
            >>> schema_obj = schema_class()
            >>> schema_obj.load({'tag_address_family': 'ip-v4-only'})
            {'tag_address_family': 'ip-v4-only'}

            >>> schema_class = attr_openapi_schema("folder", "update")
            >>> schema_obj = schema_class()
            >>> schema_obj.load({'tag_address_family': 'ip-v4-only'})
            {'tag_address_family': 'ip-v4-only'}

            >>> schema_class = attr_openapi_schema("cluster", "create")
            >>> schema_obj = schema_class()
            >>> schema_obj.load({'tag_address_family': 'ip-v4-only'})
            {'tag_address_family': 'ip-v4-only'}

        Unknown attributes lead to an error:

            >>> import pytest
            >>> with pytest.raises(ValidationError):
            ...     schema_obj.load({'foo': 'bar'})

        Wrong values on tag groups also lead to an error:

            >>> with pytest.raises(ValidationError):
            ...     schema_obj.load({'tag_address_family': 'ip-v5-only'})

    Args:
        object_type:
            Either "host", "folder" or "cluster".

        context:
            Either "create" or "update"

    Returns:
        A marshmallow schema with the attributes as fields.

    """
    schema = collections.OrderedDict()
    for attr in collect_attributes(object_type, context):
        schema[attr.name] = _field_from_attr(attr)

    class_name = f"{object_type.title()}{context.title()}Attribute"
    return _schema_from_dict(class_name, schema)
