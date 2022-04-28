#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import functools
import typing
from typing import (
    Any,
    Callable,
    cast,
    List,
    Literal,
    NamedTuple,
    Optional,
    Type,
    TypedDict,
    TypeVar,
)

from marshmallow import ValidationError

from livestatus import SiteId

from cmk.utils.livestatus_helpers import tables
from cmk.utils.livestatus_helpers.expressions import (
    And,
    BinaryExpression,
    LiteralExpression,
    LIVESTATUS_OPERATORS,
    Not,
    Or,
    QueryExpression,
    UnaryExpression,
)
from cmk.utils.tags import BuiltinTagConfig, TagGroup

# There is an implicit dependency introduced by the collect_attributes call which is evaluated
# at import time. To make it work as expected we need to import
import cmk.gui.plugins.wato.builtin_attributes  # pylint: disable=unused-import
import cmk.gui.watolib.groups  # pylint: disable=unused-import
from cmk.gui import site_config
from cmk.gui.fields.base import BaseSchema
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib.host_attributes import (
    get_sorted_host_attribute_topics,
    get_sorted_host_attributes_by_topic,
)
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
    for topic_id, topic_title in get_sorted_host_attribute_topics("always", new=True):
        for attr in get_sorted_host_attributes_by_topic(topic_id):
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

        result.append(
            Attr(
                name=_ensure(f"tag_{tag_group.id}"),
                section=tag_group.topic or "No topic",
                mandatory=False,
                description="\n\n".join(description),
                enum=[tag.id for tag in tag_group.tags],
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
        if site_name not in site_config.sitenames():
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


def tree_to_expr(filter_dict, table: Any = None) -> QueryExpression:
    """Turn a filter-dict into a QueryExpression.

    Examples:

        >>> tree_to_expr({'op': '=', 'left': 'hosts.name', 'right': 'example.com'})
        Filter(name = example.com)

        >>> tree_to_expr({'op': '!=', 'left': 'hosts.name', 'right': 'example.com'})
        Filter(name != example.com)

        >>> tree_to_expr({'op': '!=', 'left': 'name', 'right': 'example.com'}, 'hosts')
        Filter(name != example.com)

        >>> tree_to_expr({'op': 'and', \
                          'expr': [{'op': '=', 'left': 'hosts.name', 'right': 'example.com'}, \
                          {'op': '=', 'left': 'hosts.state', 'right': 0}]})
        And(Filter(name = example.com), Filter(state = 0))

        >>> tree_to_expr({'op': 'or', \
                          'expr': [{'op': '=', 'left': 'hosts.name', 'right': 'example.com'}, \
                          {'op': '=', 'left': 'hosts.name', 'right': 'heute'}]})
        Or(Filter(name = example.com), Filter(name = heute))

        >>> tree_to_expr({'op': 'not', \
                          'expr': {'op': '=', 'left': 'hosts.name', 'right': 'example.com'}})
        Not(Filter(name = example.com))

        >>> tree_to_expr({'op': 'not', \
                          'expr': {'op': 'not', \
                                   'expr': {'op': '=', \
                                            'left': 'hosts.name', \
                                            'right': 'example.com'}}})
        Not(Not(Filter(name = example.com)))

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> tree_to_expr({'op': 'not', 'expr': Hosts.name == 'example.com'})
        Not(Filter(name = example.com))

        >>> tree_to_expr({'op': 'no_way', \
                          'expr': {'op': '=', 'left': 'hosts.name', 'right': 'example.com'}})
        Traceback (most recent call last):
        ...
        ValueError: Unknown operator: no_way

    Args:
        filter_dict:
            A filter-dict, which can either be persisted or passed over the wire.

        table:
            Optionally a table name. Only used when the columns are used in plain form
            (without table name prefixes).

    Returns:
        A valid LiveStatus query expression.

    Raises:
        ValueError: when unknown columns are queried

    """
    if not isinstance(filter_dict, dict):
        # FIXME
        #   Because of not having correct Python packages at the root-level, sometimes a
        #   locally defined class ends up having a relative dotted path, like for example
        #       <class 'expressions.BinaryExpression'>
        #   instead of
        #       <class 'cmk.utils.livestatus_helpers.expressions.BinaryExpression'>
        #   While these classes are actually the same, Python treats them distinct, so we can't
        #   just say `isinstance(filter_dict, BinaryExpression)` (or their super-type) here.
        return cast(QueryExpression, filter_dict)
    op = filter_dict["op"]
    if op in LIVESTATUS_OPERATORS:
        left = filter_dict["left"]
        if "." in left:
            _table, column = left.split(".")
            if table is not None and _table_name(table) != _table:
                raise ValueError(
                    f"This field can only query table {_table_name(table)!r}. ({left})"
                )
        else:
            if table is None:
                raise ValueError("Missing table parameter.")
            _table = _table_name(table)
            column = left
        return BinaryExpression(
            _lookup_column(_table, column),
            LiteralExpression(filter_dict["right"]),
            op,
        )

    if op == "and":
        return And(*[tree_to_expr(expr, table) for expr in filter_dict["expr"]])

    if op == "or":
        return Or(*[tree_to_expr(expr, table) for expr in filter_dict["expr"]])

    if op == "not":
        return Not(tree_to_expr(filter_dict["expr"], table))

    raise ValueError(f"Unknown operator: {op}")


def _lookup_column(table_name, column_name) -> UnaryExpression:
    if isinstance(table_name, str):
        table_class = getattr(tables, table_name.title())
    else:
        table_class = table_name
        table_name = table_class.__tablename__

    try:
        column = getattr(table_class, column_name)
    except AttributeError as e:
        raise ValueError(f"Table {table_name!r} has no column {column_name!r}.") from e
    return column.expr


def _table_name(table) -> str:
    if isinstance(table, str):
        return table

    return table.__tablename__
