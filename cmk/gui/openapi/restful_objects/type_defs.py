#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, NotRequired, TypedDict

from marshmallow import fields, Schema

from cmk.gui.http import HTTPMethod

URL = str

DomainType = Literal[
    "acknowledge",
    "activation_run",
    "agent",
    "agent_binary",
    "audit_log",
    "background_job",
    "bi_aggregation",
    "bi_pack",
    "bi_rule",
    "broker_connection",
    "comment",
    "configuration_entity",
    "contact_group_config",
    "dcd",
    "discovery_run",
    "downtime",
    "event_console",
    "form_spec",
    "folder",
    "folder_config",
    "host",
    "host_config",
    "host_config_internal",
    "hostgroup",
    "host_group_config",
    "host_tag_group",
    "inventory",
    "ldap_connection",
    "licensing",
    "license_response",
    "license_usage",
    "license_request",
    "metric",
    "notification_rule",
    "notification_parameter",
    "otel_collector_config",
    "password",
    "parent_scan",
    "rule",
    "ruleset",
    "saml_connection",
    "service",
    "service_discovery",
    "service_discovery_run",
    "servicegroup",
    "service_group_config",
    "sign_key",
    "site_connection",
    "sla",
    "time_period",
    "user",
    "user_config",
    "user_role",
    "aux_tag",
    "autocomplete",
    "quick_setup",
    "quick_setup_action_result",
    "quick_setup_stage",
    "quick_setup_stage_action_result",
    "managed_robots",
    "onboarding",
]


CmkEndpointName = Literal[
    "cmk/run",
    "cmk/run_setup",
    "cmk/activate",
    "cmk/bake",
    "cmk/bake_and_sign",
    "cmk/cancel",
    "cmk/bulk_create",
    "cmk/bulk_discovery",
    "cmk/bulk_update",
    "cmk/compute",
    "cmk/configure",
    "cmk/create",
    "cmk/create_aux_tag",
    "cmk/create_host",
    "cmk/create_for_host",
    "cmk/create_service",
    "cmk/create_for_service",
    "cmk/create_cluster",
    "cmk/download",
    "cmk/download_by_hash",
    "cmk/download_by_host",
    "cmk/download_license_request",
    "cmk/fetch",
    "cmk/fetch_phase_one",
    "cmk/list",
    "cmk/move",
    "cmk/permalink",
    "cmk/rename",
    "cmk/show",
    "cmk/sign",
    "cmk/start",
    "cmk/host_config",
    "cmk/folder_config",
    "cmk/global_config",
    "cmk/delete_bi_rule",
    "cmk/delete_bi_aggregation",
    "cmk/delete_bi_pack",
    "cmk/put_bi_rule",
    "cmk/post_bi_rule",
    "cmk/bi_aggregation_state_post",
    "cmk/bi_aggregation_state_get",
    "cmk/put_bi_aggregation",
    "cmk/post_bi_aggregation",
    "cmk/put_bi_pack",
    "cmk/put_bi_packs",
    "cmk/get_bi_rule",
    "cmk/get_bi_aggregation",
    "cmk/get_bi_pack",
    "cmk/get_bi_packs",
    "cmk/pending-activation-changes",
    "cmk/put_bi_pack",
    "cmk/post_bi_pack",
    "cmk/wait-for-completion",
    "cmk/baking-status",
    "cmk/bakery-status",
    "cmk/service.move-monitored",
    "cmk/service.move-undecided",
    "cmk/service.move-ignored",
    "cmk/service.bulk-acknowledge",
    "cmk/link_uuid",
    "cmk/get_graph",
    "cmk/get_custom_graph",
    "cmk/filter_graph",
    "cmk/site_logout",
    "cmk/site_login",
    "cmk/update",
    "cmk/update_and_acknowledge",
    "cmk/upload_license_response",
    "cmk/change_state",
    "cmk/verify",
    "cmk/register",
    "cmk/quick_setup",
    "cmk/save_quick_setup",
    "cmk/edit_quick_setup",
]

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
    ".../collection_update_and_acknowledge",
    ".../collection_change_state",
    ".../default",
    ".../delete",
    ".../details",  # takes params
    ".../domain-type",
    ".../domain-types",
    ".../element",
    ".../element-type",
    ".../fetch",
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
]  # fmt: off

LinkRelation = CmkEndpointName | RestfulEndpointName
EndpointFamilyName = str
EndpointKey = tuple[EndpointFamilyName, LinkRelation]
TagGroup = Literal["Monitoring", "Setup", "Checkmk Internal", "Undocumented Endpoint"]

PropertyFormat = Literal[
    # String values
    "string",
    # The value should simply be interpreted as a string. This is also the default if
    # the "format" json-property is omitted (or if no domain metadata is available)
    "date-time",  # A date in ISO 8601 format of YYYY-MM-DDThh:mm:ssZ in UTC time
    "date",  # A date in the format of YYYY-MM-DD.
    "time",  # A time in the format of hh:mm:ss.
    "utc-millisec",  # The difference, measured in milliseconds, between the
    # specified time and midnight, 00:00 of January 1, 1970 UTC.
    "big-integer(n)",  # The value should be parsed as an integer, scale n.
    "big-integer(s,p)",  # The value should be parsed as a big decimal, scale n,
    # precision p.
    "blob",  # base-64 encoded byte-sequence
    "clob",  # character large object: the string is a large array of
    # characters, for example an HTML resource
    # Non-string values
    "decimal",  # the number should be interpreted as a float-point decimal.
    "int",  # the number should be interpreted as an integer.
]  # fmt: off
CollectionItem = dict[str, str]
LocationType = Literal["path", "query", "header", "cookie"]
ResultType = Literal["object", "list", "scalar", "void"]

KnownContentType = Literal[
    "application/json",
    "application/gzip",
]
AcceptFieldType = KnownContentType | list[KnownContentType]


class LinkType(TypedDict):
    rel: str
    href: str
    type: str
    method: str
    domainType: Literal["link"]
    title: NotRequired[str]
    body_params: NotRequired[dict[str, str | None]]


class ActionObject(TypedDict):
    id: str
    memberType: str
    links: list[LinkType]
    parameters: dict[str, Any]


class Result(TypedDict):
    links: list[LinkType]
    value: Any | None


class ActionResult(TypedDict):
    links: list[LinkType]
    resultType: ResultType
    result: Result


class DomainObject(TypedDict):
    domainType: DomainType
    id: str
    title: str
    links: list[LinkType]
    members: dict[str, Any]
    extensions: NotRequired[dict[str, Any]]


class CollectionObject(TypedDict):
    id: str
    domainType: str
    links: list[LinkType]
    value: Any
    extensions: dict[str, str]


class ObjectProperty(TypedDict, total=False):
    id: str
    value: Any
    disabledReason: str
    choices: list[Any]
    links: list[LinkType]
    extensions: dict[str, Any]


Serializable = dict[str, Any] | CollectionObject | ObjectProperty | DomainObject | ActionResult
ETagBehaviour = Literal["input", "output", "both"]

SchemaClass = type[Schema]
SchemaInstanceOrClass = Schema | SchemaClass
OpenAPISchemaType = Literal["string", "array", "object", "boolean", "integer", "number"]

# Used to blacklist some endpoints in certain locations
EndpointTarget = Literal["swagger-ui", "doc"]


def translate_to_openapi_keys(
    name: str,
    location: LocationType,
    description: str | None = None,
    required: bool = True,
    example: str | None = None,
    allow_empty: bool | None = False,
    schema_enum: list[str] | None = None,
    schema_type: OpenAPISchemaType = "string",
    schema_string_pattern: str | None = None,
    schema_string_format: PropertyFormat | None = None,
    schema_num_minimum: int | None = None,
    schema_num_maximum: int | None = None,
) -> "OpenAPIParameter":
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
    schema: SchemaType = {"type": schema_type}
    if schema_type == "string":
        if schema_string_format is not None:
            schema["format"] = schema_string_format
        if schema_string_pattern is not None:
            schema["pattern"] = schema_string_pattern
    if schema_enum:
        schema["enum"] = schema_enum
    if schema_type in ("number", "integer"):
        if schema_num_minimum is not None:
            schema["minimum"] = schema_num_minimum
        if schema_num_maximum is not None:
            schema["maximum"] = schema_num_maximum
    if not required and location == "path":
        raise ValueError(f"Path parameters must be required. In {name} - {description}")
    raw_values: OpenAPIParameter = {
        "name": name,
        "in": location,
        "required": required,
    }
    if description is not None:
        raw_values["description"] = description
    if allow_empty is not None:
        if location == "query":
            raw_values["allowEmptyValue"] = allow_empty
        elif allow_empty is True:
            raise ValueError(
                f"allowEmptyValue can only be set to true for query parameters. In {name} - {description}"
            )
    if example is not None:
        raw_values["example"] = example
    if schema:
        raw_values["schema"] = schema
    return raw_values


ValidatorType = Callable[[Any], dict[str, list[str]] | None]

MarshmallowFieldParams = Mapping[str, fields.Field]


class SchemaType(TypedDict, total=False):
    type: OpenAPISchemaType
    format: PropertyFormat
    pattern: str
    enum: list[Any]
    minimum: int | float
    maximum: int | float


OpenAPIParameter = TypedDict(
    "OpenAPIParameter",
    {
        "name": str,
        "description": str,
        "in": LocationType,
        "required": bool,
        "allowEmptyValue": bool,
        "example": Any,
        "schema": SchemaType | type[Schema],
        "content": dict[str, dict[str, object]],
    },
    total=False,
)

RawParameter = MarshmallowFieldParams | type[Schema]


class PathItem(TypedDict, total=False):
    content: dict[str, dict[str, Any]]
    description: str
    headers: dict[str, OpenAPIParameter]


ResponseType = TypedDict(
    "ResponseType",
    {
        "200": PathItem,
        "204": PathItem,
        "301": PathItem,
        "302": PathItem,
        "303": PathItem,
        "400": PathItem,
        "401": PathItem,
        "403": PathItem,
        "404": PathItem,
        "405": PathItem,
        "406": PathItem,
        "409": PathItem,
        "415": PathItem,
        "412": PathItem,
        "422": PathItem,
        "423": PathItem,
        "428": PathItem,
    },
    total=False,
)


class EditionLabel(TypedDict, total=True):
    name: str
    color: str
    position: Literal["before", "after"]


class CodeSample(TypedDict, total=True):
    label: str
    lang: str
    source: str


ParameterReference = str

OperationSpecType = TypedDict(
    "OperationSpecType",
    {
        "x-codeSamples": list[CodeSample],
        "x-badges": NotRequired[Sequence[EditionLabel]],
        "operationId": str,
        "tags": list[str],
        "description": str,
        "responses": ResponseType,
        "parameters": Sequence[OpenAPIParameter],
        "requestBody": dict[str, Any],
        "summary": str,
        "deprecated": bool,
    },
    total=False,
)

OperationObject = dict[HTTPMethod, OperationSpecType]

OpenAPITag = TypedDict(
    "OpenAPITag",
    {
        "name": str,
        "description": str,
        "externalDocs": str,
        "x-displayName": str,
    },
    total=False,
)


ParameterKey = tuple[str, ...]

ErrorStatusCodeInt = Literal[
    400,
    401,
    403,
    404,
    405,
    406,
    409,
    412,
    415,
    422,
    423,
    428,
    429,
    500,
    504,
]
SuccessStatusCodeInt = Literal[
    200,
    201,
    204,
]

RedirectStatusCodeInt = Literal[
    301,
    302,
    303,
]

StatusCodeInt = Literal[
    SuccessStatusCodeInt,
    ErrorStatusCodeInt,
    RedirectStatusCodeInt,
]

StatusCode = Literal[
    "200",
    "201",
    "204",
    "301",
    "302",
    "303",
    "400",
    "401",
    "403",
    "404",
    "405",
    "406",
    "409",
    "412",
    "415",
    "422",
    "423",
    "428",
    "429",
    "500",
    "504",
]

ContentType = str
ContentObject = dict[ContentType, dict[str, Any]]
