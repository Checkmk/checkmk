#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import functools
import json
from typing import Literal, Optional, Dict, Any, cast, List, NamedTuple, Type, TypeVar, Callable, \
    TypedDict
from urllib.parse import quote_plus

import docstring_parser  # type: ignore[import]
from marshmallow import Schema
from marshmallow.decorators import post_load
from marshmallow.exceptions import ValidationError
from werkzeug.exceptions import HTTPException

from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi import fields
from cmk.utils.livestatus_helpers.queries import Query
from cmk.gui.watolib.tags import load_tag_config
from cmk.gui.sites import sitenames
from cmk.utils.tags import BuiltinTagConfig, TagGroup
from livestatus import SiteId


def problem(
    status: int = 400,
    title: str = "A problem occured.",
    detail: Optional[str] = None,
    type_: Optional[str] = None,
    ext: Optional[Dict[str, Any]] = None,
):
    problem_dict = {
        'title': title,
        'status': status,
    }
    if detail is not None:
        problem_dict['detail'] = detail
    if type_ is not None:
        problem_dict['type'] = type_

    if isinstance(ext, dict):
        problem_dict.update(ext)
    else:
        if ext:
            problem_dict['ext'] = ext

    response = Response()
    response.status_code = status
    response.set_content_type("application/problem+json")
    response.set_data(json.dumps(problem_dict))
    return response


class ProblemException(HTTPException):
    def __init__(
        self,
        status: int = 400,
        title: str = "A problem occured.",
        detail: Optional[str] = None,
        type_: Optional[str] = None,
        ext: Optional[Dict[str, Any]] = None,
    ):
        """
        This exception is holds arguments that are going to be passed to the
        `problem` function to generate a proper response.
        """
        super().__init__(description=title)
        # These two are named as such for HTTPException compatibility.
        self.code: int = status
        self.description: str = title

        self.detail = detail
        self.type = type_
        self.ext = ext

    def __call__(self, environ, start_response):
        return self.to_problem()(environ, start_response)

    def to_problem(self):
        return problem(
            status=self.code,
            title=self.description,
            detail=self.detail,
            type_=self.type,
            ext=self.ext,
        )


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""
    class Meta:
        """Holds configuration for marshmallow"""
        ordered = True  # we want to have documentation in definition-order


def param_description(
    string: Optional[str],
    param_name: str,
    errors: Literal['raise', 'ignore'] = 'raise',
) -> Optional[str]:
    """Get a param description of a docstring.

    Args:
        string:
            The docstring from which to extract the parameter description.

        param_name:
            The name of the parameter.

        errors:
            Either 'raise' or 'ignore'.

    Examples:

        If a docstring is given, there are a few possibilities.

            >>> from cmk.gui import watolib
            >>> param_description(watolib.activate_changes_start.__doc__, 'force_foreign_changes')
            'Will activate changes even if the user who made those changes is not the currently logged in user.'

            >>> param_description(param_description.__doc__, 'string')
            'The docstring from which to extract the parameter description.'

            >>> param_description(param_description.__doc__, 'foo', errors='ignore')

            >>> param_description(param_description.__doc__, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: Parameter 'foo' not found in docstring.

        There are cases, when no docstring is assigned to a function.

            >>> param_description(None, 'foo', errors='ignore')

            >>> param_description(None, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: No docstring was given.

    Returns:
        The description of the parameter, if possible.

    """
    if string is None:
        if errors == 'raise':
            raise ValueError("No docstring was given.")
        return None

    docstring = docstring_parser.parse(string)
    for param in docstring.params:
        if param.arg_name == param_name:
            return param.description.replace("\n", " ")
    if errors == 'raise':
        raise ValueError(f"Parameter {param_name!r} not found in docstring.")
    return None


def create_url(site: SiteId, query: Query) -> str:
    """Create a REST-API query URL.

    Examples:

        >>> create_url('heute',
        ...            Query.from_string("GET hosts\\nColumns: name\\nFilter: name = heute"))
        '/heute/check_mk/api/1.0/domain-types/host/collections/all?query=%7B%22op%22%3A+%22%3D%22%2C+%22left%22%3A+%22hosts.name%22%2C+%22right%22%3A+%22heute%22%7D'

    Args:
        site:
            A valid site-name.

        query:
            The Query() instance which the endpoint shall create again.

    Returns:
        The URL.

    Raises:
        A ValueError when no URL could be created.

    """
    table = cast(str, query.table.__tablename__)
    try:
        domain_type = {
            'hosts': 'host',
            'services': 'service',
        }[table]
    except KeyError:
        raise ValueError(f"Could not find a domain-type for table {table}.")
    url = f"/{site}/check_mk/api/1.0/domain-types/{domain_type}/collections/all"
    query_dict = query.dict_repr()
    if query_dict:
        query_string_value = quote_plus(json.dumps(query_dict))
        url += f"?query={query_string_value}"

    return url


class Attr(NamedTuple):
    name: str
    mandatory: bool
    section: str
    description: str
    enum: Optional[List[Optional[str]]] = None


ObjectType = Literal['host', 'folder', 'cluster']
ObjectContext = Literal['create', 'update']


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
        >>> assert len(attrs) > 10

        >>> attrs = collect_attributes('host', 'update')
        >>> assert len(attrs) > 10

        >>> attrs = collect_attributes('cluster', 'create')
        >>> assert len(attrs) > 10

        >>> attrs = collect_attributes('cluster', 'update')
        >>> assert len(attrs) > 10

        >>> attrs = collect_attributes('folder', 'create')
        >>> assert len(attrs) > 10

        >>> attrs = collect_attributes('folder', 'update')
        >>> assert len(attrs) > 10

    To check the content of the list, uncomment this one.

        # >>> import pprint
        # >>> pprint.pprint(attrs)

    """
    something = TypeVar('something')

    def _ensure(optional: Optional[something]) -> something:
        if optional is None:
            raise ValueError
        return optional

    result = []
    new = context == 'create'
    for topic_id, topic_title in watolib.get_sorted_host_attribute_topics(object_type, new):
        for attr in watolib.get_sorted_host_attributes_by_topic(topic_id):
            if not attr.is_visible(object_type, new):
                continue
            help_text: str = attr.help() or ""
            # TODO: what to do with attr.depends_on_tags()?
            attr_entry = Attr(
                name=attr.name(),
                description=help_text,
                section=topic_title,
                mandatory=attr.is_mandatory(),
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
            ))

    return result


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
    def site_exists(site_name: SiteId) -> None:
        if site_name not in sitenames():
            raise ValidationError(f"Site {site_name!r} does not exist.")

    validators = {
        'site': site_exists,
    }

    class FieldParams(TypedDict, total=False):
        description: str
        mandatory: bool
        enum: List[Optional[str]]
        validate: Callable[[Any], Any]
        allow_none: bool

    schema = collections.OrderedDict()
    for attr in collect_attributes(object_type, context):
        kwargs: FieldParams = {
            'description': attr.description,
            'mandatory': attr.mandatory,
        }
        # If we would assign enum=None, this would lead to a broken OpenApi specification!
        if attr.enum is not None:
            kwargs['enum'] = attr.enum
            if None in attr.enum:
                kwargs['allow_none'] = True

        if attr.name in validators:
            kwargs['validate'] = validators[attr.name]

        schema[attr.name] = fields.String(**kwargs)

    # This is a post-load hook to cast the OrderedDict instances to normal dicts. This would lead
    # to problems with the *.mk file persisting logic otherwise.
    def cast_to_dict(self, data, **kwargs):
        return dict(data)

    schema['remove_ordered_dict'] = post_load(cast_to_dict)
    class_name = f'{object_type.title()}{context.title()}Attribute'
    return type(class_name, (BaseSchema,), schema)
