#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from marshmallow import fields

from cmk.fields import base

_JSON_TYPES: dict[type, str] = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    dict: "object",
    list: "array",
}


class Constant(base.OpenAPIAttributes, fields.Constant):
    def __init__(self, constant: object, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        super().__init__(constant, **kwargs)
        # A marshmallow Constant renders into JSON Schema without a ``type`` (its MRO maps to
        # the generic ``Field`` type in apispec). Discriminator validation in
        # openapi-generator requires the discriminator's ``propertyName`` to be string-typed
        # in every ``oneOf`` member, so derive the JSON type from the constant's Python type.
        if (json_type := _JSON_TYPES.get(type(constant))) is not None:
            self.metadata.setdefault("type", json_type)


class Boolean(base.OpenAPIAttributes, fields.Boolean):
    pass


class Dict(base.OpenAPIAttributes, fields.Dict):
    pass


class Date(base.OpenAPIAttributes, fields.Date):
    pass


class DateTime(base.OpenAPIAttributes, fields.DateTime):
    pass


class AwareDateTime(base.OpenAPIAttributes, fields.AwareDateTime):
    pass


class Decimal(base.OpenAPIAttributes, fields.Decimal):
    pass


class Float(base.OpenAPIAttributes, fields.Float):
    pass


class Email(base.OpenAPIAttributes, fields.Email):
    pass


class Function(base.OpenAPIAttributes, fields.Function):
    pass


class IPv4(base.OpenAPIAttributes, fields.IPv4):
    pass


class IPv4Interface(base.OpenAPIAttributes, fields.IPv4Interface):
    pass


class IPv6(base.OpenAPIAttributes, fields.IPv6):
    pass


class IPv6Interface(base.OpenAPIAttributes, fields.IPv6Interface):
    pass


class Time(base.OpenAPIAttributes, fields.Time):
    pass


class UUID(base.OpenAPIAttributes, fields.UUID):
    pass


class URL(base.OpenAPIAttributes, fields.URL):
    pass
