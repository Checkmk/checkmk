#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import typing

from apispec.ext.marshmallow import common  # type: ignore[import]
from marshmallow import (
    EXCLUDE,
    fields,
    INCLUDE,
    post_dump,
    post_load,
    pre_dump,
    RAISE,
    Schema,
    types,
    utils,
    ValidationError,
)
from marshmallow.decorators import (
    POST_DUMP,
    POST_LOAD,
    PRE_DUMP,
    PRE_LOAD,
)
from marshmallow.error_store import ErrorStore


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""
    class Meta:
        """Holds configuration for marshmallow"""
        ordered = True  # we want to have documentation in definition-order

    cast_to_dict: bool = False

    # Marshmallow removed dump-validation starting from 3.0.0rc9. When we want to verify we don't
    # try to dump (superfluous fields are filtered anyway) we need to do it ourselves.
    validate_on_dump: bool = False

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

    @pre_dump(pass_many=True)
    def validate_dump_fields(self, data, **kwargs):
        if self.validate_on_dump and isinstance(data, dict):
            for key in data:
                if key not in self.declared_fields:
                    raise ValidationError({key: "Unknown field."})
        return data


class FieldWrapper:
    def __init__(self, field: fields.Field):
        self.field = field


class ValueTypedDictSchema(BaseSchema):
    """A schema where you can define the type for a dict's values

    Attributes:
        value_type:
            the Schema for the dict's values

    """
    value_type: typing.Union[typing.Type[Schema], typing.Tuple[fields.Field]]

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
            data = self._invoke_load_processors(PRE_LOAD,
                                                data,
                                                many=many,
                                                original_data=data,
                                                partial=partial)

        if not isinstance(data, dict):
            raise ValidationError(f'Data type is invalid: {data}', field_name='_schema')

        try:
            schema = common.resolve_schema_instance(self.value_type)
            result = self._convert_with_schema(data, schema_func=schema.load)
        except ValueError:
            result = self._serialize_field(data, field=self.value_type[0])  # type: ignore[index]

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

        try:
            schema = common.resolve_schema_instance(self.value_type)
            result = self._convert_with_schema(obj, schema_func=schema.dump)
        except ValueError:
            result = self._deserialize_field(obj, field=self.value_type[0])  # type: ignore[index]

        if self._has_processors(POST_DUMP):
            result = self._invoke_dump_processors(POST_DUMP, result, many=many, original_data=obj)

        return result


class MultiNested(fields.Field):
    """Combine many distinct models under one overarching model

    Standard behaviour is to only allow one of the sub-model to be true at the same time, i.e.
    when one model validates, the others are not considered and the first model wins.

    MultiNested supports two different behaviors:

     * Standard Mode:
           For each object to validate, only one sub-schema may be true at the same time.

     * Merged Mode:
           For each object, all sub-schemas may be true at the same time. Resulting keys
           are merged in the result. All keys of the input have to be claimed by some sub-schema.
           The next schema in the chain will only get the until then unclaimed keys as input.
           If at the end of the chain any key is not claimed by some schema, this will result
           in an error.

    Standard mode
    =============

    We start with 2 sub-models for different types of users:

        >>> class Schema1(BaseSchema):
        ...     cast_to_dict = True
        ...     required1 = fields.String(required=True)
        ...     optional1 = fields.String()

        >>> class Schema2(BaseSchema):
        ...     cast_to_dict = True
        ...     required2 = fields.String(required=True)
        ...     optional2 = fields.String()
        ...
        ...     @post_load
        ...     def _valid(self, data, **kwargs):
        ...         for key in data:
        ...             if key not in ['required2', 'optional2']:
        ...                raise ValidationError({key: f"Unknown key found: {key}"})
        ...         return data

    In standard-mode, we just combine them into a nested container model, like so.

        >>> class Entries(BaseSchema):
        ...     cast_to_dict = True
        ...     entries = MultiNested([Schema1(), Schema2()], many=True)

    We can see our sub-modles are arranged in an `anyOf` OpenAPI property, which corresponds to
    a Union type.

        >>> nested = Entries()
        >>> nested.declared_fields['entries'].metadata
        {'anyOf': [<Schema1(many=False)>, <Schema2(many=False)>]}

    When serializing and deserializing, we can use either model in our collections.

        >>> nested = Entries()
        >>> rv1 = nested.load({'entries': [{'required1': '1'}, {'required2': '2'}]})
        >>> rv1
        {'entries': [{'required1': '1'}, {'required2': '2'}]}

        >>> nested.load(rv1)
        {'entries': [{'required1': '1'}, {'required2': '2'}]}

    Merged mode (many=True)
    =======================

    Merged (combining objects) with having many objects as a result is nonsensible and thus
    not supported.

        >>> MultiNested([Schema1(), Schema2()], merged=True, many=True)
        Traceback (most recent call last):
        ...
        NotImplementedError: merged=True with many=True is not supported.

    Merged mode (many=False)
    ========================

    Merged mode only makes sense when all schemas have disjoint keys. When regular schemas with
    fields are used, this is checked automatically. When blank schemas are used, this is not
    possible, and you have to ensure that all schemas validate disjoint keys.

    When using many=False, we can merge and separate as expected.

        >>> class MergedEntry(BaseSchema):
        ...     cast_to_dict = True
        ...     entry = MultiNested([Schema1(), Schema2()], merged=True, many=False)

        Only required fields:

        >>> merged_entry = MergedEntry()
        >>> rv3 = merged_entry.dump({'entry': {'required1': '1', 'required2': '2'}})
        >>> rv3
        {'entry': {'required1': '1', 'required2': '2'}}

        >>> rv4 = merged_entry.load(rv3)
        >>> rv4
        {'entry': {'required1': '1', 'required2': '2'}}

        A mix of required and optional fields:

        >>> rv5 = merged_entry.dump({'entry': {'required1': '1', 'optional1': '1', 'required2': '2'}})
        >>> rv5
        {'entry': {'required1': '1', 'optional1': '1', 'required2': '2'}}

        >>> rv6 = merged_entry.dump({'entry': {'required1': '1', 'required2': '2', 'optional2': '2'}})
        >>> rv6
        {'entry': {'required1': '1', 'required2': '2', 'optional2': '2'}}

        Error handling is done by the two sub-schemas

        >>> merged_entry.dump({'entry': {'optional1': '1', 'optional2': '2'}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'required1': ['Missing data for required field.'], \
'required2': ['Missing data for required field.']}

        >>> merged_entry.dump({'entry': {'required1': '1', 'something': 'else'}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'required2': ['Missing data for \
required field.'], 'something': ['Unknown field.']}

        >>> merged_entry.dump({'entry': {'required1': '1', 'something': 'else'}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'required2': ['Missing data for \
required field.'], 'something': ['Unknown field.']}

        >>> merged_entry.dump({'entry': {'required2': '2', 'something': 'else'}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'required1': ['Missing data for \
required field.'], 'something': ['Unknown field.']}

        And the exception is:

            >>> merged_entry.dump({'entry': {'required2': '2', 'something': 'else'}})
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: {'required1': ['Missing data for \
required field.'], 'something': ['Unknown field.']}

        Dump only fields are handled correctly as well:

            >>> class DumpOnly(BaseSchema):
            ...     cast_to_dict = True
            ...     dump_only = fields.String(dump_only=True)

            >>> class WithDumpOnly(BaseSchema):
            ...      cast_to_dict = True
            ...      field = MultiNested([Schema1(), DumpOnly()], merged=True)

            >>> nested = WithDumpOnly()

            >>> nested.load({'field': {'required1': '1'}})
            {'field': {'required1': '1'}}

            >>> nested.load({'field': {'required1': '1', 'dump_only': '1'}})
            {'field': {'required1': '1'}}

            >>> nested.dump({'field': {'required1': '1', 'dump_only': '1'}})
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: {'dump_only': ['Unknown field.']}

        When merging, all keys can only occur once:

            >>> MultiNested([Schema1(), Schema1()], merged=True)
            Traceback (most recent call last):
            ...
            RuntimeError: Schemas [<Schema1(many=False)>, <Schema1(many=False)>] are not disjoint. \
Keys 'optional1', 'required1' occur more than once.

        Merged mode with blank schemas:

            >>> class Schema(BaseSchema):
            ...     cast_to_dict = True
            ...     def __init__(self, required, *args, **kwargs):
            ...         self.required = required
            ...         super().__init__(*args, **kwargs)
            ...
            ...     @post_load
            ...     def _validate(self, data, many=False, partial=None):
            ...         for key in self.required:
            ...             if key not in data:
            ...                 raise ValidationError({key: f"Required for load: {key} ({data})/{self.required}"})
            ...         return data

            >>> schema = Schema(['required42'], unknown=INCLUDE)
            >>> schema.load({'required42': '42'})
            {'required42': '42'}

            There is no @pre_dump hook, so this will not work:

            >>> schema.dump({'required84': '84'})
            {}

            >>> class MergedSchema(BaseSchema):
            ...     cast_to_dict = True
            ...     field = MultiNested([Schema(['required17']), Schema(['required18'])],
            ...                         merged=True)

            >>> merged_blank = MergedSchema()
            >>> merged_blank.load({'field': {'required17': '17', 'required18': '18'}})
            {'field': {'required17': '17', 'required18': '18'}}

            >>> merged_blank.dump({'field': {'required17': '17', 'required18': '18'}})
            {'field': {'required17': '17', 'required18': '18'}}

        And blank schemas are also handled correctly when encountering missing fields:

            >>> merged_blank = MergedSchema()
            >>> merged_blank.load({'field': {}})  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: ...

    """
    class ValidateOnDump(BaseSchema):
        cast_to_dict = True
        validate_on_dump = True

    Result = typing.Dict[str, typing.Any]

    def __init__(
        self,
        nested: typing.Sequence[typing.Union[typing.Type[fields.SchemaABC], fields.SchemaABC]],
        mode: typing.Literal["anyOf", "allOf"] = "anyOf",
        *,
        default: typing.Any = fields.missing_,
        only: typing.Optional[types.StrSequenceOrSet] = None,
        exclude: types.StrSequenceOrSet = (),
        many: bool = False,
        unknown: typing.Optional[str] = None,
        # In this loop we do the following:
        #  1) we try to dump all the keys of a model
        #  2) when the dump succeeds, we remove all the dumped keys from the source
        #  3) we go to the next model and goto 1
        #
        # For this we assume the schema is always symmetrical (i.e. a round trip is
        # idempotent) to get at the original keys. If this is not true, there may be bugs.
        merged: bool = False,
        **kwargs,
    ):
        if unknown is not None:
            raise ValueError("unknown is not supported for MultiNested")

        if merged and many:
            raise NotImplementedError("merged=True with many=True is not supported.")

        if mode != "anyOf":
            raise NotImplementedError("allOf is not yet implemented.")

        metadata = kwargs.pop("metadata", {})
        context = getattr(self.parent, "context", {})
        context.update(metadata.get("context", {}))

        self._nested = []
        schema_inst: Schema
        for schema in nested:
            schema_inst = common.resolve_schema_instance(schema)
            schema_inst.context.update(context)
            if not self._has_fields(schema_inst):
                # NOTE
                # We want all values to be included in the result, even if the schema hasn't
                # defined any fields on it. This is, because these schemas are used to validate
                # through the hooks @post_load, @pre_dump, etc.
                schema_inst.unknown = INCLUDE

            self._nested.append(schema_inst)

        metadata["anyOf"] = self._nested

        # We need to check that the key names of all schemas are completely disjoint, because
        # we can't represent multiple schemas with the same key in merge-mode.
        if merged:
            set1: typing.Set[str] = set()
            for schema_inst in self._nested:
                keys = set(schema_inst.declared_fields.keys())
                if not set1.isdisjoint(keys):
                    wrong_keys = ", ".join(repr(key) for key in sorted(set1.intersection(keys)))
                    raise RuntimeError(f"Schemas {self._nested} are not disjoint. "
                                       f"Keys {wrong_keys} occur more than once.")
                set1.update(keys)

        self.mode = mode
        self.only = only
        self.exclude = exclude
        self.many = many
        self.merged = merged
        # When we are merging, we don't want to have errors due to cross-schema validation.
        # When we operate in standard mode, we really want to know these errors.
        self.unknown = EXCLUDE if self.merged else RAISE
        super().__init__(default=default, metadata=metadata, **kwargs)

    def _nested_schemas(self) -> typing.List[Schema]:
        return self._nested + [MultiNested.ValidateOnDump(unknown=RAISE)]

    @staticmethod
    def _has_fields(_schema: Schema) -> bool:
        return bool(_schema.declared_fields)

    def _add_error(
        self,
        error_store: ErrorStore,
        errors: typing.Union[str, typing.List, typing.Dict],
    ) -> None:
        if isinstance(errors, dict):
            error_store.errors.update(errors)
        elif isinstance(errors, list):
            error_store.errors.setdefault("_schema", []).extend(errors)
        elif isinstance(errors, str):
            error_store.errors.setdefault("_schema", []).append(errors)
        else:
            raise TypeError(f"Unexpected error message type: {type(errors)}")

    def _dump_schemas(self, scalar: Result):
        rv = []
        error_store = ErrorStore()
        value = dict(scalar)
        value_empty = not value

        for schema in self._nested_schemas():
            schema_inst = common.resolve_schema_instance(schema)
            try:
                if not (value_empty or self._has_fields(schema_inst)):
                    dumped = self._check_key_by_key(value, schema_inst, error_store)
                else:
                    dumped = schema_inst.dump(value, many=False)

                if not self.merged:
                    return dumped

                # This only works if the schema has fields declared.
                if self._has_fields(schema_inst):
                    loaded = schema_inst.load(
                        dumped,
                        unknown=self.unknown,
                    )
                    # We check what could actually pass through the load() call, because some
                    # schemas validate keys without having them defined in their _declared_fields.
                    for key in loaded.keys():
                        if key in value:
                            del value[key]
            except ValidationError as exc:
                # When we encounter an error, we can't do anything besides remove the keys which
                # we know about.
                for key in schema_inst.declared_fields:
                    if key in value:
                        del value[key]
                self._add_error(error_store, exc.messages)
                continue

            if not isinstance(schema_inst, MultiNested.ValidateOnDump):
                rv.append(dumped)

        if error_store.errors:
            raise ValidationError(error_store.errors)

        return rv

    def _serialize(
        self,
        value: typing.Any,
        attr: str,
        obj: typing.Any,
        **kwargs,
    ) -> typing.Union[Result, typing.List[Result]]:
        result: typing.Any
        error_store = ErrorStore()

        result = []
        if self.many:
            if utils.is_collection(value):
                for entry in value:
                    result.extend(self._dump_schemas(entry))
            else:
                error_store.store_error(self._make_type_error(value))
        else:
            result.extend(self._dump_schemas(value))

        if error_store.errors:
            raise ValidationError(error_store.errors, data=value)

        if self.merged and not self.many:
            rv = {}
            for entry in result:
                for key, _value in entry.items():
                    if key in rv:
                        raise ValidationError({key: "Can't collate result. Key occurs twice."})
                    rv[key] = _value
            return rv

        return result

    def _make_type_error(self, value) -> ValidationError:
        return self.make_error(
            "type",
            input=value,
            type=value.__class__.__name__,
        )

    def _load_schemas(self, scalar: Result, partial=None) -> Result:
        rv = {}
        error_store = ErrorStore()
        if not isinstance(scalar, dict):
            raise ValidationError(f"Expected an object, not a {type(scalar).__name__}.")

        value = dict(scalar)
        value_empty = not value

        for schema in self._nested_schemas():
            schema_inst = common.resolve_schema_instance(schema)
            if not (value_empty or self._has_fields(schema_inst)):
                try:
                    loaded = self._check_key_by_key(value, schema_inst, error_store)
                except ValidationError as exc:
                    self._add_error(error_store, exc.messages)
                    continue
            else:
                try:
                    # We can only load key-by-key when we have at least one key.
                    loaded = schema_inst.load(
                        value,
                        unknown=self.unknown,
                        partial=partial,
                    )
                    for key in schema_inst.declared_fields:
                        if key in value:
                            del value[key]
                except ValidationError as exc:
                    for key in schema_inst.declared_fields:
                        if key in value:
                            del value[key]
                    self._add_error(error_store, exc.messages)
                    continue

            if not self.merged:
                return loaded

            if self.merged:
                rv.update(loaded)

        # We only want to report errors when one of these cases is true:
        # 1. There are values left over in the value dict. This means that there were
        #    no schemas which could validate these values.
        # 2. We got no values in the first place and errors were recorded.
        value_left_over = bool(value)
        if (value_empty or value_left_over) and error_store.errors:
            raise ValidationError(error_store.errors)
        return rv

    def _check_key_by_key(self, value, schema_inst, error_store):
        result = {}
        success = []
        for key, _value in value.copy().items():
            try:
                result.update(schema_inst.load({key: _value}))
                del value[key]
                success.append(key)
            except ValidationError as exc:
                self._add_error(error_store, exc.messages)
        for key in success:
            if key in error_store.errors:
                del error_store.errors[key]
        return result

    def _deserialize(
        self,
        value: typing.Union[Result, typing.List[Result]],
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ):
        result: typing.Any
        if isinstance(value, list):
            if self.many:
                result = []
                for collection_entry in value:
                    result.append(self._load_schemas(collection_entry))
            else:
                raise self._make_type_error(value)
        else:
            result = self._load_schemas(value)

        return result
