#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
import re
from typing import Annotated

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    PlainSerializer,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema, CoreSchema

from cmk.gui.fields.fields_filter import FieldsFilter, parse_fields_filter
from cmk.gui.openapi.framework import QueryParam
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator
from cmk.gui.openapi.framework.model.omitted import ApiOmitted
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree


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


FieldsFilterType = Annotated[
    Annotated[FieldsFilter, TypedPlainValidator(str, parse_fields_filter)] | ApiOmitted,
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
]


class _FolderValidation:
    @staticmethod
    def _normalize_folder(folder_id: str) -> str:
        r"""Normalizes a folder representation.

        This means replacing the separators with slashes, and stripping extra ones.
        The leading separator will also be removed!

        Examples:

            >>> _FolderValidation._normalize_folder("\\")
            ''

            >>> _FolderValidation._normalize_folder("~")
            ''

            >>> _FolderValidation._normalize_folder("/foo/bar")
            'foo/bar'

            >>> _FolderValidation._normalize_folder("\\foo\\bar")
            'foo/bar'

            >>> _FolderValidation._normalize_folder("~foo~bar")
            'foo/bar'

            >>> _FolderValidation._normalize_folder("/foo/bar/")
            'foo/bar'
        """
        for sep in ("\\", "~"):
            folder_id = folder_id.replace(sep, "/")

        return folder_id.strip("/")

    @staticmethod
    def _is_hex(hex_string: str) -> bool:
        try:
            int(hex_string, 16)
            return True
        except ValueError:
            return False

    @classmethod
    def validate(cls, value: str) -> Folder:
        tree = folder_tree()
        value = cls._normalize_folder(value)
        if value == "":
            return tree.root_folder()

        if cls._is_hex(value):
            return tree._by_id(value)

        return tree.folder(value)

    @staticmethod
    def serialize(value: Folder) -> str:
        return "/" + value.path()


AnnotatedFolder = Annotated[
    Folder,
    TypedPlainValidator(str, _FolderValidation.validate),
    PlainSerializer(_FolderValidation.serialize, return_type=str),
]
