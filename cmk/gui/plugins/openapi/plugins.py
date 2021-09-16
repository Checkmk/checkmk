#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Type, Union

from apispec.ext import marshmallow  # type: ignore[import]
from apispec.ext.marshmallow import common  # type: ignore[import]
from marshmallow import fields, Schema, ValidationError


class ValueTypedDictOpenAPIConverter(marshmallow.OpenAPIConverter):
    def schema2jsonschema(self, schema):
        if self.openapi_version.major < 3 or not is_value_typed_dict(schema):
            return super().schema2jsonschema(schema)

        schema_type = schema.value_type
        schema_instance = common.resolve_schema_instance(schema_type)
        schema_key = common.make_schema_key(schema_instance)
        if schema_key not in self.refs:
            component_name = self.schema_name_resolver(schema_type)
            self.spec.components.schema(component_name, schema=schema_instance)

        ref_dict = self.get_ref_dict(schema_instance)

        return {
            "type": "object",
            "additionalProperties": ref_dict,
        }


class ValueTypedDictSchema(Schema):
    """A schema where you can define the type for a dict's values

    Attributes:
        value_type:
            the Schema for the dict's values

        key_name:
            The name of the key in the value-dictionary which stores the key for the
            parent dictionary.

            For example, having:
                key_name = 'a'
                value_dict = {'a': 'b', 'c': 'd'}

            will result in:

                {'b': {'c': 'd'}}

        keep_key:
            to keep the key and it's value in the value-dict or to remove it.

    """

    key_name: str = "name"
    keep_key: bool = True
    value_type: Union[Type[Schema], fields.Field]

    def dump(self, obj: Any, *, many=None):
        schema = common.resolve_schema_instance(self.value_type)
        result = {}
        for entry in obj:
            part = schema.dump(entry)
            # HACK. marshmallow_oneofschema returns errors instead of raising them. :-(
            # See https://github.com/marshmallow-code/marshmallow-oneofschema/issues/48
            is_error_return = (
                isinstance(part, tuple)
                and len(part) == 2
                and part[0] is None
                and isinstance(part[1], dict)
                and "_schema" in part[1]
            )
            if is_error_return:
                raise ValidationError(part[1]["_schema"])
            result[part[self.key_name]] = part
            if not self.keep_key:
                del part[self.key_name]
        return result

    def load(self, data, *, many=None, partial=None, unknown=None):
        if not isinstance(data, dict):
            raise ValidationError({"_schema": f"Data type is invalid: {data}"})

        schema = common.resolve_schema_instance(self.value_type)
        res = []
        for key, value in data.items():
            payload = value.copy()
            payload[self.key_name] = key
            result = schema.load(payload)
            res.append(result)

        return res


def is_value_typed_dict(schema):
    is_class = isinstance(schema, type) and issubclass(schema, ValueTypedDictSchema)
    is_instance = isinstance(schema, ValueTypedDictSchema)
    return is_class or is_instance


class ValueTypedDictMarshmallowPlugin(marshmallow.MarshmallowPlugin):
    def init_spec(self, spec):
        super().init_spec(spec)
        self.converter = ValueTypedDictOpenAPIConverter(
            openapi_version=spec.openapi_version,
            schema_name_resolver=self.schema_name_resolver,
            spec=spec,
        )
