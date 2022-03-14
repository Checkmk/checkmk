#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import typing

from apispec.ext.marshmallow import common  # type: ignore[import]
from marshmallow import fields, post_dump, post_load, Schema, types, utils, ValidationError
from marshmallow.base import SchemaABC
from marshmallow.decorators import POST_DUMP, POST_LOAD, PRE_DUMP, PRE_LOAD
from marshmallow.error_store import ErrorStore

from cmk.fields import base


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""

    class Meta:
        """Holds configuration for marshmallow"""

        ordered = True  # we want to have documentation in definition-order

    cast_to_dict: bool = False

    @post_load(pass_many=True)
    @post_dump(pass_many=True)
    def remove_ordered_dict(self, data, **kwargs):
        def _remove_ordered_dict(obj):
            if self.cast_to_dict and isinstance(obj, collections.OrderedDict):
                return dict(obj)
            return obj

        # This is a post-load hook to cast the OrderedDict instances to normal dicts. This would
        # lead to problems with the *.mk file persisting logic otherwise.
        if isinstance(data, list):
            return [_remove_ordered_dict(obj) for obj in data]

        return _remove_ordered_dict(data)


class FieldWrapper:
    def __init__(self, field: fields.Field):
        self.field = field


class ValueTypedDictSchema(BaseSchema):
    """A schema where you can define the type for a dict's values

    Attributes:
        value_type:
            the Schema for the dict's values

    """

    value_type: typing.Union[typing.Type[Schema], FieldWrapper]

    @classmethod
    def field(cls, field: fields.Field) -> FieldWrapper:
        return FieldWrapper(field)

    def _convert_with_schema(self, data, schema_func):
        result = {}
        for key, value in data.items():
            result[key] = schema_func(value)
        return result

    def _serialize_field(self, data, field: fields.Field):
        result = {}
        for key, value in data.items():
            field._validate(value)
            try:
                result[key] = field.serialize(obj=data, attr=key)
            except ValueError as exc:
                raise ValidationError(str(exc), field_name=key)
        return result

    def _deserialize_field(self, data, field: fields.Field):
        result = {}
        for key, value in data.items():
            field._validate(value)
            result[key] = field.deserialize(value=value, data=data, attr=key)
        return result

    def load(self, data, *, many=None, partial=None, unknown=None):
        if self._has_processors(PRE_LOAD):
            data = self._invoke_load_processors(
                PRE_LOAD, data, many=many, original_data=data, partial=partial
            )

        if not isinstance(data, dict):
            raise ValidationError(f"Data type is invalid: {data}", field_name="_schema")

        if isinstance(self.value_type, FieldWrapper):
            result = self._serialize_field(data, field=self.value_type.field)
        elif isinstance(self.value_type, BaseSchema) or (
            isinstance(self.value_type, type) and issubclass(self.value_type, SchemaABC)
        ):
            schema = common.resolve_schema_instance(self.value_type)
            result = self._convert_with_schema(data, schema_func=schema.load)
        else:
            raise ValidationError(
                f"Data type is not known: {type(self.value_type)} {self.value_type}"
            )

        if self._has_processors(POST_LOAD):
            result = self._invoke_load_processors(
                POST_LOAD,
                result,
                many=many,
                original_data=data,
                partial=partial,
            )

        return result

    def dump(self, obj: typing.Any, *, many=None):
        if self._has_processors(PRE_DUMP):
            obj = self._invoke_dump_processors(PRE_DUMP, obj, many=many, original_data=obj)

        if isinstance(self.value_type, FieldWrapper):
            result = self._deserialize_field(obj, field=self.value_type.field)
        elif isinstance(self.value_type, BaseSchema) or (
            isinstance(self.value_type, type) and issubclass(self.value_type, SchemaABC)
        ):
            schema = common.resolve_schema_instance(self.value_type)
            result = self._convert_with_schema(obj, schema_func=schema.dump)
        else:
            raise ValidationError(f"Data type is not known: {type(obj)}")

        if self._has_processors(POST_DUMP):
            result = self._invoke_dump_processors(POST_DUMP, result, many=many, original_data=obj)

        return result


class MultiNested(base.OpenAPIAttributes, fields.Field):
    """

    >>> class User(BaseSchema):
    ...     cast_to_dict = True
    ...     name = fields.String()

    >>> class Luser(BaseSchema):
    ...     cast_to_dict = True
    ...     epithet = fields.String()

    >>> class People(BaseSchema):
    ...     cast_to_dict = True
    ...     lusers = MultiNested([User(), Luser()], many=True)

    >>> nested = People()
    >>> nested.load({'lusers': [{'name': 'Hans Wurst'}, {'epithet': 'DAU'}]})
    {'lusers': [{'name': 'Hans Wurst'}, {'epithet': 'DAU'}]}

    >>> nested.declared_fields['lusers'].metadata
    {'anyOf': [<User(many=False)>, <Luser(many=False)>]}

    """

    def __init__(
        self,
        nested: typing.List[typing.Type[fields.SchemaABC]],
        mode: typing.Literal["anyOf", "allOf"] = "anyOf",
        *,
        default: typing.Any = fields.missing_,
        only: typing.Optional[types.StrSequenceOrSet] = None,
        exclude: types.StrSequenceOrSet = (),
        many: bool = False,
        unknown: typing.Optional[str] = None,
        **kwargs,
    ):
        if mode != "anyOf":
            raise NotImplementedError("allOf is not yet implemented.")

        metadata = kwargs.pop("metadata", {})
        context = getattr(self.parent, "context", {})
        context.update(metadata.get("context", {}))

        self.nested = []
        schema_inst: Schema
        for schema in nested:
            schema_inst = common.resolve_schema_instance(schema)
            schema_inst.context.update(context)
            self.nested.append(schema_inst)

        metadata["anyOf"] = self.nested

        self.mode = mode
        self.only = only
        self.exclude = exclude
        self.many = many
        self.unknown = unknown
        super().__init__(default=default, metadata=metadata, **kwargs)

    def _serialize(
        self,
        value: typing.Any,
        attr: str,
        obj: typing.Any,
        **kwargs,
    ):
        if value is None:
            return None

        error_store = ErrorStore()
        for schema in self.nested:
            try:
                return common.resolve_schema_instance(schema).dump(value, many=self.many)
            except ValidationError as exc:
                error_store.store_error(exc.messages, field_name=exc.field_name)

        raise ValidationError(error_store.errors, data=value)

    def _test_collection(self, value):
        if self.many and not utils.is_collection(value):
            raise self.make_error("type", input=value, type=value.__class__.__name__)

    def _check_schemas(self, scalar, partial=None):
        error_store = ErrorStore()
        for schema in self.nested:
            try:
                return common.resolve_schema_instance(schema).load(
                    scalar,
                    unknown=self.unknown,
                    partial=partial,
                )
            except ValidationError as exc:
                error_store.store_error(exc.messages, field_name=exc.field_name)

        raise ValidationError(error_store.errors, data=scalar)

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ):
        error_store = ErrorStore()
        if self.many:
            result = []
            if utils.is_collection(value):
                for collection_entry in value:
                    result.append(self._check_schemas(collection_entry))
                return result

            raise self.make_error("type", input=value, type=value.__class__.__name__)

        for schema in self.nested:
            try:
                return common.resolve_schema_instance(schema).load(value, unknown=self.unknown)
            except ValidationError as exc:
                error_store.store_error(exc.messages, field_name=exc.field_name)

        raise ValidationError(error_store.errors, data=value)
