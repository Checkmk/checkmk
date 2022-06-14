#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing
from typing import Optional, Tuple

from apispec.ext import marshmallow  # type: ignore[import]
from apispec.ext.marshmallow import common, field_converter  # type: ignore[import]
from marshmallow import base, fields

from cmk.gui.fields.base import FieldWrapper, MultiNested, ValueTypedDictSchema


def is_value_typed_dict(schema) -> bool:
    is_class = isinstance(schema, type) and issubclass(schema, ValueTypedDictSchema)
    is_instance = isinstance(schema, ValueTypedDictSchema)
    return is_class or is_instance


def type_and_format_of_field(field: fields.Field) -> Tuple[str, Optional[str]]:
    """Get the type and the format of a field.

    Examples:

        >>> type_and_format_of_field(fields.String())
        ('string', None)

        >>> type_and_format_of_field(fields.String(metadata=dict(format="host")))
        ('string', None)

        >>> type_and_format_of_field(fields.Integer())
        ('integer', None)

    Args:
        field:
            A marshmallow field instance.

    Returns:
        A tuple representing the type and the format of this field.

    """
    for class_, spec in field_converter.DEFAULT_FIELD_MAPPING.items():
        if isinstance(field, class_):
            return spec
    raise ValueError(f"No fitting spec found for field {field!r}.")


FieldProperties = typing.TypedDict(
    "FieldProperties",
    {
        "required": bool,
        "description": str,
        "format": str,
        "pattern": str,
        "type": str,
    },
    total=False,
)


def field_properties(field: fields.Field) -> FieldProperties:
    """

    Examples:

        >>> field_properties(fields.String(metadata=dict(format="email")))
        {'type': 'string', 'format': 'email'}

        >>> field_properties(fields.String(metadata=dict(format="email", description="Email")))
        {'type': 'string', 'description': 'Email', 'format': 'email'}

        >>> field_properties(fields.String(metadata=dict(format="email", description="Email"), required=True))
        {'type': 'string', 'description': 'Email', 'format': 'email', 'required': True}

    Args:
        field:
            A marshmallow Field instance.

    Returns:
        The OpenAPI additionalproperties section.

    """
    type_, format_ = type_and_format_of_field(field)
    properties: FieldProperties = {
        "type": type_,
    }
    if format_ is not None:
        properties["format"] = format_

    if "description" in field.metadata:
        properties["description"] = field.metadata["description"]

    if "format" in field.metadata:
        properties["format"] = field.metadata["format"]

    if "pattern" in field.metadata:
        properties["pattern"] = field.metadata["pattern"]

    if field.required:
        properties["required"] = field.required

    return properties


class CheckmkOpenAPIConverter(marshmallow.OpenAPIConverter):
    def schema2jsonschema(self, schema):
        if not is_value_typed_dict(schema):
            return super().schema2jsonschema(schema)

        if isinstance(schema.value_type, FieldWrapper):
            properties = field_properties(schema.value_type.field)
        elif isinstance(schema.value_type, base.SchemaABC) or (
            isinstance(schema.value_type, type) and issubclass(schema.value_type, base.SchemaABC)
        ):
            schema_instance = common.resolve_schema_instance(schema.value_type)
            schema_key = common.make_schema_key(schema_instance)
            if schema_key not in self.refs:
                component_name = self.schema_name_resolver(schema.value_type)
                self.spec.components.schema(component_name, schema=schema_instance)
            properties = self.get_ref_dict(schema_instance)
        else:
            raise RuntimeError(f"Unsupported value_type: {schema.value_type}")

        return {
            "type": "object",
            "additionalProperties": properties,
        }

    def nested2properties(self, field: fields.Field, ret):
        """Return a dictionary of properties from :class:`Nested <marshmallow.fields.Nested` fields.

        Typically provides a reference object and will add the schema to the spec
        if it is not already present
        If a custom `schema_name_resolver` function returns `None` for the nested
        schema a JSON schema object will be returned

        Params:
            field:
                A marshmallow field.
            ret:
                A pre-prepared return value dictionary.

        Returns:
            A dict of the relevant OpenAPI subsection.
        """
        if isinstance(field, MultiNested):
            schemas = [self.resolve_nested_schema(schema) for schema in field.metadata["anyOf"]]
            ret["anyOf"] = schemas
            return ret

        return super().nested2properties(field, ret)


class CheckmkMarshmallowPlugin(marshmallow.MarshmallowPlugin):
    Converter = CheckmkOpenAPIConverter
