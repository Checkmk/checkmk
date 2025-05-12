#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Handling of dynamic fields in REST API models.

This module provides the `WithDynamicFields` class, which is used as a base class for models that
support dynamic fields. An example would be user defined host attributes.
"""

import dataclasses
from collections.abc import Mapping

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import ArgsKwargs, core_schema
from pydantic_core.core_schema import CoreSchema, SerializerFunctionWrapHandler


@dataclasses.dataclass(kw_only=True, slots=True)
class WithDynamicFields:
    """This will add support for dynamic fields in the schema.

    Instantiation of the class still requires the dynamic fields to be explicitly specified under
    the `dynamic_fields` key. The specific use case here is the validation and serialization with
    pydantic/TypeAdapters.

    The `dynamic_fields` field can be overridden, meeting the following requirements:
    * the type must be a mapping, with the keys being strings
    * the mappings values can be any type, but they must be (de-)serializable to JSON
    * the field must not have a default or default_factory
    * the field can include additional metadata, which will be included in the OpenAPI schema.
    """

    dynamic_fields: Mapping[str, object]

    @classmethod
    def _populate_dynamic_fields(cls, values: object) -> object:
        known_fields = {f.name for f in dataclasses.fields(cls)}
        if isinstance(values, ArgsKwargs):
            if values.kwargs is None:
                return values

            extra_fields = values.kwargs.keys() - known_fields
            values.kwargs["dynamic_fields"] = {f: values.kwargs.pop(f) for f in extra_fields}
        elif isinstance(values, dict):
            extra_fields = values.keys() - known_fields
            values["dynamic_fields"] = {f: values.pop(f) for f in extra_fields}
        else:
            raise TypeError(f"Unsupported type {type(values)}")
        return values

    @classmethod
    def _serialize_dynamic_fields(cls, value: object, nxt: SerializerFunctionWrapHandler) -> object:
        serialized = nxt(value)
        serialized.update(serialized.pop("dynamic_fields", {}))
        return serialized

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: CoreSchema, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_before_validator_function(
            cls._populate_dynamic_fields,
            schema=handler(source_type),
            serialization=core_schema.wrap_serializer_function_ser_schema(
                cls._serialize_dynamic_fields,
                info_arg=False,
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        # remove the field from the schema, it should be replaced by "additionalProperties"
        if (
            (dynamic_field_schema := json_schema["properties"].pop("dynamic_fields", None))
            and isinstance(dynamic_field_schema, dict)
            and dynamic_field_schema.get("type") == "object"
        ):
            # the schema for `dynamic_fields` is a dict. `additionalProperties` in the json schema
            # should only be the value schema, as the keys are implicitly strings.
            dynamic_field_schema.update(dynamic_field_schema.pop("additionalProperties", {}))
            json_schema["additionalProperties"] = dynamic_field_schema
        else:
            # this is supported by OpenAPI
            json_schema["additionalProperties"] = True

        # remove the `dynamic_fields` key from the required list
        json_schema["required"].remove("dynamic_fields")

        return json_schema
