#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
    Union,
)

from marshmallow import Schema, fields

URL = str

DomainType = Literal[
    'acknowledge',
    'agent',
    'activation_run',
    'bi_rule',
    'bi_aggregation',
    'bi_pack',
    'contact_group_config',
    'folder_config',
    'downtime',
    'host',
    'hostgroup',
    'host_config',
    'host_group_config',
    'host_tag_group',
    'password',
    'user_config',
    'service',
    'servicegroup',
    'service_discovery',
    'service_group_config',
    'time_period',
    'user',
]  # yapf: disable

DomainObject = Dict[str, Any]

CmkEndpointName = Literal[
    'cmk/run',
    'cmk/activate',
    'cmk/bake',
    'cmk/bake_and_sign',
    'cmk/cancel',
    'cmk/bulk_create',
    'cmk/bulk_update',
    'cmk/create',
    'cmk/create_host',
    'cmk/create_service',
    'cmk/create_cluster',
    'cmk/download',
    'cmk/list',
    'cmk/move',
    'cmk/rename',
    'cmk/show',
    'cmk/sign',
    'cmk/start',
    'cmk/delete_bi_rule',
    'cmk/delete_bi_aggregation',
    'cmk/delete_bi_pack',
    'cmk/put_bi_rule',
    'cmk/put_bi_aggregation',
    'cmk/put_bi_pack',
    'cmk/put_bi_packs',
    'cmk/get_bi_rule',
    'cmk/get_bi_aggregation',
    'cmk/get_bi_pack',
    'cmk/get_bi_packs',
    'cmk/wait-for-completion',
    'cmk/baking-status',
    'cmk/bakery-status',
    'cmk/service.move-monitored',
    'cmk/service.move-undecided',
    'cmk/service.move-ignored',
    'cmk/service.bulk-acknowledge',
]  # yapf: disable

RestfulEndpointName = Literal[
    "describedby",  # sic
    "help",
    "icon",
    "previous",
    "next",
    "self",
    "up",
    ".../action",
    ".../action-param",
    ".../add-to",  # takes params
    ".../attachment",  # takes params
    ".../choice",  # takes params
    ".../clear",
    ".../collection",
    ".../default",
    ".../delete",
    ".../details",  # takes params
    ".../domain-type",
    ".../domain-types",
    ".../element",
    ".../element-type",
    ".../invoke",
    ".../modify",
    ".../persist",
    ".../property",
    ".../remove-from",  # takes params
    ".../return-type",
    ".../services",
    ".../service",  # takes params
    ".../update",
    ".../user",
    ".../value",  # takes params
    ".../version",
]  # yapf: disable

EndpointName = Union[CmkEndpointName, RestfulEndpointName]

HTTPMethod = Literal["get", "put", "post", "delete"]

PropertyFormat = Literal[
    # String values
    'string',
    # The value should simply be interpreted as a string. This is also the default if
    # the "format" json-property is omitted (or if no domain metadata is available)
    'date-time',  # A date in ISO 8601 format of YYYY-MM-DDThh:mm:ssZ in UTC time
    'date',  # A date in the format of YYYY-MM-DD.
    'time',  # A time in the format of hh:mm:ss.
    'utc-millisec',  # The difference, measured in milliseconds, between the
    # specified time and midnight, 00:00 of January 1, 1970 UTC.
    'big-integer(n)',  # The value should be parsed as an integer, scale n.
    'big-integer(s,p)',  # The value should be parsed as a big decimal, scale n,
    # precision p.
    'blob',  # base-64 encoded byte-sequence
    'clob',  # character large object: the string is a large array of
    # characters, for example an HTML resource
    # Non-string values
    'decimal',  # the number should be interpreted as a float-point decimal.
    'int',  # the number should be interpreted as an integer.
]  # yapf: disable
CollectionItem = Dict[str, str]
LocationType = Literal['path', 'query', 'header', 'cookie']
ResultType = Literal["object", "list", "scalar", "void"]
LinkType = Dict[str, str]
CollectionObject = TypedDict('CollectionObject', {
    'id': str,
    'domainType': str,
    'links': List[LinkType],
    'value': Any,
    'extensions': Dict[str, str]
})
ObjectProperty = TypedDict(
    'ObjectProperty',
    {
        'id': str,
        'value': Any,
        'disabledReason': str,
        'choices': List[Any],
        'links': List[LinkType],
        'extensions': Dict[str, Any],
    },
    total=False,
)
Serializable = Union[Dict[str, Any], CollectionObject, ObjectProperty]
ETagBehaviour = Literal["input", "output", "both"]

SchemaClass = Type[Schema]
SchemaInstanceOrClass = Union[Schema, SchemaClass]
OpenAPISchemaType = Literal['string', 'array', 'object', 'boolean', 'integer', 'number']


def translate_to_openapi_keys(
    name: str,
    location: LocationType,
    description: Optional[str] = None,
    required: bool = True,
    example: Optional[str] = None,
    allow_empty: Optional[bool] = False,
    schema_enum: Optional[List[str]] = None,
    schema_type: OpenAPISchemaType = 'string',
    schema_string_pattern: Optional[str] = None,
    schema_string_format: Optional[PropertyFormat] = None,
    schema_num_minimum: Optional[int] = None,
    schema_num_maximum: Optional[int] = None,
) -> 'OpenAPIParameter':
    """
    Args:
        name:
        location:
        description:
        required:
        example:
        allow_empty:
        schema_enum:
        schema_type:
        schema_string_pattern:
        schema_string_format:
        schema_num_minimum:
        schema_num_maximum:

    Returns:

    """
    schema: SchemaType = {'type': schema_type}
    if schema_type == 'string':
        if schema_string_format is not None:
            schema['format'] = schema_string_format
        if schema_string_pattern is not None:
            schema['pattern'] = schema_string_pattern
    if schema_enum:
        schema['enum'] = schema_enum
    if schema_type in ('number', 'integer'):
        if schema_num_minimum is not None:
            schema['minimum'] = schema_num_minimum
        if schema_num_maximum is not None:
            schema['maximum'] = schema_num_maximum
    raw_values: OpenAPIParameter = {
        'name': name,
        'in': location,
        'required': required,
    }
    if description is not None:
        raw_values['description'] = description
    if allow_empty is not None:
        raw_values['allowEmptyValue'] = allow_empty
    if example is not None:
        raw_values['example'] = example
    if schema:
        raw_values['schema'] = schema
    return raw_values


ValidatorType = Callable[[Any], Optional[Dict[str, List[str]]]]

MarshmallowFieldParams = Mapping[str, fields.Field]

SchemaType = TypedDict(
    "SchemaType",
    {
        'type': OpenAPISchemaType,
        'format': PropertyFormat,
        'pattern': str,
        'enum': List[Any],
        'minimum': Union[int, float],
        'maximum': Union[int, float],
    },
    total=False,
)

OpenAPIParameter = TypedDict(
    "OpenAPIParameter",
    {
        'name': str,
        'description': str,
        'in': LocationType,
        'required': bool,
        'allowEmptyValue': bool,
        'example': Any,
        'schema': Union[SchemaType, Type[Schema]],
    },
    total=False,
)

RawParameter = Union[MarshmallowFieldParams, Type[Schema]]

PathItem = TypedDict(
    "PathItem",
    {
        'content': Dict[str, Dict[str, Any]],
        'description': str,
        'headers': Dict[str, OpenAPIParameter],
    },
    total=False,
)

ResponseType = TypedDict(
    "ResponseType",
    {
        "default": PathItem,
        "200": PathItem,
        "204": PathItem,
        "301": PathItem,
        "302": PathItem,
    },
    total=False,
)

CodeSample = TypedDict(
    "CodeSample",
    {
        'label': str,
        'lang': str,
        'source': str,
    },
    total=True,
)

ParameterReference = str

SchemaParameter = TypedDict(
    'SchemaParameter',
    {
        'in': LocationType,
        'schema': Type[Schema],
    },
    total=True,
)

OperationSpecType = TypedDict(
    "OperationSpecType",
    {
        'x-codeSamples': List[CodeSample],
        'operationId': str,
        'tags': List[str],
        'description': str,
        'responses': ResponseType,
        'parameters': Sequence[SchemaParameter],
        'requestBody': Dict[str, Any],
        'summary': str,
    },
    total=False,
)

OpenAPITag = TypedDict(
    "OpenAPITag",
    {
        'name': str,
        'description': str,
        'externalDocs': str,
        'x-displayName': str,
    },
    total=False,
)

EndpointEntry = TypedDict(
    "EndpointEntry",
    {
        'endpoint': Any,
        'href': str,
        'method': HTTPMethod,
        'rel': EndpointName,
        'parameters': Sequence[OpenAPIParameter],
    },
    total=True,
)

EndpointKey = Tuple[str, EndpointName]
ParameterKey = Tuple[str, ...]
