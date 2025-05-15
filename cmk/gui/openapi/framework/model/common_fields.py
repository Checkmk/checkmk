#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
import re
from typing import Annotated

from pydantic import AfterValidator, GetCoreSchemaHandler, GetJsonSchemaHandler, PlainValidator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema, CoreSchema

from cmk.gui.fields.fields_filter import FieldsFilter, parse_fields_filter
from cmk.gui.openapi.framework import QueryParam


def _validate_regex(value: str) -> str:
    """Check if the value is a valid regex."""
    re.compile(value)
    return value


class RegexString(str):
    """Normal string that is validated as a regex."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: CoreSchema, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            _validate_regex, core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema.setdefault("format", "regex")
        return json_schema


def _validate_ipv4(value: str) -> str:
    """Check if the value is a valid IPv4 address."""
    ipaddress.IPv4Address(value)
    return value


class IPv4String(str):
    """Normal string that is validated as an IPv4 address."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: CoreSchema, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            _validate_ipv4, core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema.setdefault("format", "ipv4")
        return json_schema


def _validate_ipv4_network(value: str) -> str:
    """Check if the value is a valid IPv4 network."""
    ipaddress.IPv4Network(value)
    return value


IPv4NetworkString = Annotated[str, AfterValidator(_validate_ipv4_network)]


FieldsFilterType = Annotated[
    FieldsFilter,
    QueryParam(
        description="""The fields to include/exclude.

The syntax is a comma-separated list of field paths.
Each field path is a sequence of field names separated by a tilde (`~`).
Field names may contain alphanumeric characters, dashes (`-`) and underscores (`_`).
The field path may be followed by a list of subfields enclosed in parentheses (`(` and `)`).

The outermost fields must be enclosed in parentheses and may be prefixed with an exclamation mark (`!`) to negate the selection.

Examples:
- `(ipaddress)` selects the field `ipaddress`, all other fields will be omitted.
- `!(ipaddress)` excludes the field `ipaddress`, all other fields will be included.
- `(ipaddress,ipv6address)` selects only the fields `ipaddress` and `ipv6address`.
- `(attributes~ipaddress)` selects the field `ipaddress` within `attributes`, all other fields (not just within attributes) will be omitted.
- `(attributes(ipaddress,ipv6address))` selects the fields `ipaddress` and `ipv6address` within `attributes`, again all other fields will be omitted.
- `!(extensions~attributes(ipaddress,ipv6address))` excludes the fields `ipaddress` and `ipv6address` within `attributes` under `extensions`, all other fields will be included.
""",
        example="(id)",
    ),
    PlainValidator(parse_fields_filter, json_schema_input_type=str),
]
