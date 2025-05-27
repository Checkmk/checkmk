#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Handling of non-required fields in the REST API.

This module provides the `ApiOmitted` class, which is used to represent fields that were or will be
omitted in REST API request/response bodies. This is mainly needed, because (some of) our internal
data structures differentiate between None values and unset ones. Until this is fixed, the REST API
will need to be able to handle omitted values separately from None values as well. This can be
modelled with `NotRequired` in `TypedDict`s or with `required=False` in `marshmallow` schemas.
Python's `dataclasses` however don't have the ability to represent this. Instead, the `ApiOmitted`
class is used as a sentinel value to represent fields that are not included in the final request/
response body. For deserializing the request, non-required fields should use `ApiOmitted` as the
default value. For serializing the response, the `json_dump_without_omitted` function should be used
to remove the `ApiOmitted` values from the response body.
"""

from typing import Any, ClassVar, NoReturn

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic_core import CoreSchema, PydanticOmit
from pydantic_core.core_schema import is_instance_schema


class ApiOmitted:
    """Sentinel value for omitted fields in the REST API.

    This should only be used within the REST API code. This means request/response models and the
    endpoint handlers (where they should be removed when converting to internal data structures).
    When generating the OpenAPI schema, this type should not be included. Instead, the fields
    should be marked as optional.
    Can possibly be replaced once PEP 661 (sentinel values) lands.
    """

    __slots__ = ()
    _instance: ClassVar["ApiOmitted | None"] = None

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: type[Any], _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return is_instance_schema(cls)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> NoReturn:
        raise PydanticOmit()

    def __new__(cls, *args: object, **kwargs: object) -> "ApiOmitted":
        # Singleton pattern to ensure only one instance of ApiOmitted exists
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def __bool__(self) -> bool:
        return False


def json_dump_without_omitted[T](
    instance_type: type[T], instance: T, *, is_testing: bool = False
) -> bytes:
    """Serialize the given dataclass instance to JSON, removing omitted fields.

    Args:
        instance_type: The class of the `instance` - will be used to create a `TypeAdapter`.
        instance: The data to be serialized, must be an instance of `instance_type`.
        is_testing: Will perform round-trip validation to ensure proper serialization.

    Notes:
        - This function relies on the `instance_type` using defaults for *all* omittable fields.
          Other fields *must not* use defaults. This is checked for API models in a test.
    """
    # This will be called at most once per REST-API request
    adapter = TypeAdapter(instance_type)  # nosemgrep: type-adapter-detected
    # TODO: Rework how we deal with omitted values once pydantic supports either `PydanticOmit`
    #       in serializers or implements `exclude_if`
    # NOTE: keep in sync with CheckmkGenerateJsonSchema.encode_default for correct schemas
    return adapter.dump_json(instance, by_alias=True, exclude_defaults=True, round_trip=is_testing)
