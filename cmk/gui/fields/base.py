#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import typing
from collections.abc import Callable, Mapping, Sequence
from functools import cached_property
from typing import cast, overload, override, Self

from apispec.ext.marshmallow import common
from marshmallow import (
    EXCLUDE,
    INCLUDE,
    post_dump,
    post_load,
    RAISE,
    Schema,
    types,
    utils,
    ValidationError,
)
from marshmallow import (
    fields as ma_fields,
)
from marshmallow.decorators import POST_DUMP, POST_LOAD, PRE_DUMP, pre_dump, PRE_LOAD
from marshmallow.error_store import ErrorStore

from cmk.fields import base


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""

    cast_to_dict: bool = False
    schema_example: dict[str, typing.Any] | None = None

    # Marshmallow removed dump-validation starting from 3.0.0rc9. When we want to verify we don't
    # try to dump (superfluous fields are filtered anyway) we need to do it ourselves.
    validate_on_dump: bool = False

    @property
    @override
    def dict_class(self) -> type:
        return dict

    context: dict[typing.Any, typing.Any] = {}

    def __init__(
        self,
        *,
        only: types.StrSequenceOrSet | None = None,
        exclude: types.StrSequenceOrSet = (),
        many: bool | None = None,
        context: dict | None = None,
        load_only: types.StrSequenceOrSet = (),
        dump_only: types.StrSequenceOrSet = (),
        partial: bool | types.StrSequenceOrSet | None = None,
        unknown: str | None = None,
    ) -> None:
        super().__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )
        self.context = context or {}  # TODO: why???

    @post_load(pass_many=True)
    @post_dump(pass_many=True)
    def remove_ordered_dict(self, data: object, **kwargs: object) -> object:
        def _remove_ordered_dict(obj: object) -> object:
            if self.cast_to_dict and isinstance(obj, collections.OrderedDict):
                return dict(obj)
            return obj

        # This is a post-load hook to cast the OrderedDict instances to normal dicts. This would
        # lead to problems with the *.mk file persisting logic otherwise.
        if isinstance(data, list):
            return [_remove_ordered_dict(obj) for obj in data]

        return _remove_ordered_dict(data)

    @pre_dump(pass_many=True)
    def validate_dump_fields(self, data: object, **kwargs: object) -> object:
        if not self.validate_on_dump:
            return data

        if not isinstance(data, dict):
            return data

        # Some fields may use `data_key` or `attribute` to specify the key in the data dict.
        field_names = [
            field.data_key if field.data_key is not None else name
            for name, field in self.declared_fields.items()
        ]
        for key in data:
            if key not in field_names:
                raise ValidationError({key: "Unknown field."})

        return data

    @classmethod
    @override
    def from_dict(
        cls,
        fields: dict[str, ma_fields.Field],
        *,
        name: str = "GeneratedSchema",
    ) -> type[Self]:
        """Create a new schema class from a dictionary of fields.

        Since the `from_dict` function returns a new type that inherits from the class from which
        it was called but the return type hint is `type[Schema]` it is necessary to set the type
        accordingly.

        Another alternative evaluated in order to avoid calling `cast` was to duplicate the
        function body and adjust the return type hint, but this would have implied that future
        changes to the base function would not be immediately reflected.
        """

        schema_cls = super().from_dict(fields, name=name)
        return cast(type[Self], schema_cls)


class FieldWrapper:
    """Wrapper for marshmallow fields.

    We need this because marshmallow automatically registers fields as attributes on schemas to its
    `declared_fields` dictionary and removes it from the class's __dict__.

    This is not what we want in some cases. Therefore, we wrap the fields to make sure they are not
    registered as attributes.
    """

    def __init__(self, field: ma_fields.Field) -> None:
        self.field = field


class ValueTypedDictMeta:
    value_type: type[Schema] | FieldWrapper


class ValueTypedDictSchema(BaseSchema):
    """A schema where you can define the type for a dict's values

    Attributes:
        ValueTypedDict:
            value_type:
                the Schema for the dict's values

    """

    class Meta:
        unknown = INCLUDE

    # The value_type attribute was moved to a separate class so that
    # it is not taken as a regular field by Marshmallow.
    ValueTypedDict: ValueTypedDictMeta

    @classmethod
    def wrap_field(cls, field: ma_fields.Field) -> FieldWrapper:
        return FieldWrapper(field)

    def _convert_with_schema(
        self, data: Mapping[str, typing.Any], schema_func: Callable[[typing.Any], object]
    ) -> Mapping[str, object]:
        result = {}
        for key, value in data.items():
            result[key] = schema_func(value)
        return result

    def _serialize_field(
        self, data: Mapping[str, object], field: ma_fields.Field
    ) -> dict[str, object]:
        result = {}
        for key, value in data.items():
            target_field = self.fields[key] if key in self.fields else field

            try:
                target_field._validate(value)
            except ValidationError as exc:
                raise ValidationError({key: exc.messages}) from exc
            try:
                result[key] = target_field.serialize(obj=data, attr=key)
            except ValueError as exc:
                raise ValidationError(str(exc), field_name=key)
        return result

    def _deserialize_field(
        self, data: Mapping[str, object], field: ma_fields.Field
    ) -> dict[str, object]:
        result = {}
        for key, value in data.items():
            target_field = self.fields[key] if key in self.fields else field
            try:
                target_field._validate(value)
            except ValidationError as exc:
                raise ValidationError({key: exc.messages}) from exc
            result[key] = target_field.deserialize(value=value, data=data, attr=key)
        return result

    @override
    def load(
        self,
        data: Mapping[str, typing.Any] | typing.Iterable[Mapping[str, typing.Any]],
        *,
        many: bool | None = None,
        partial: bool | types.StrSequenceOrSet | None = None,
        unknown: str | None = None,
    ) -> object:
        if self._hooks[PRE_LOAD]:
            data = self._invoke_load_processors(
                PRE_LOAD, data, many=many or self.many, original_data=data, partial=partial
            )

        if not isinstance(data, dict):
            raise ValidationError(f"Data type is invalid: {data}", field_name="_schema")

        static_fields: dict[str, object] = {}
        dynamic_fields: dict[str, object] = {}

        for key, value in data.items():
            target = static_fields if key in self.fields else dynamic_fields
            target[key] = value

        # Load static definition
        result = super().load(static_fields, many=many, partial=partial, unknown=unknown)

        # Load dynamic definition
        if isinstance(self.ValueTypedDict.value_type, FieldWrapper):
            result.update(
                self._serialize_field(dynamic_fields, field=self.ValueTypedDict.value_type.field)
            )

        elif isinstance(self.ValueTypedDict.value_type, BaseSchema) or (
            isinstance(self.ValueTypedDict.value_type, type)
            and issubclass(self.ValueTypedDict.value_type, Schema)
        ):
            schema = common.resolve_schema_instance(self.ValueTypedDict.value_type)
            result.update(self._convert_with_schema(dynamic_fields, schema_func=schema.load))
        else:
            raise ValidationError(
                f"Data type is not known: {type(self.ValueTypedDict.value_type)} {self.ValueTypedDict.value_type}"
            )

        if self._hooks[POST_LOAD]:
            result = self._invoke_load_processors(
                POST_LOAD,
                result,
                many=many or self.many,
                original_data=data,
                partial=partial,
            )

        return result

    @override
    def dump(self, obj: typing.Any, *, many: bool | None = None) -> object:
        many = self.many if many is None else bool(many)
        if self._hooks[PRE_DUMP]:
            obj = self._invoke_dump_processors(PRE_DUMP, obj, many=many, original_data=obj)

        static_fields: dict[str, object] = {}
        dynamic_fields: dict[str, object] = {}

        for key, value in obj.items():
            target = static_fields if key in self.fields else dynamic_fields
            target[key] = value

        result = super().dump(static_fields, many=many)

        if isinstance(self.ValueTypedDict.value_type, FieldWrapper):
            result.update(
                self._deserialize_field(dynamic_fields, field=self.ValueTypedDict.value_type.field)
            )

        elif isinstance(self.ValueTypedDict.value_type, BaseSchema) or (
            isinstance(self.ValueTypedDict.value_type, type)
            and issubclass(self.ValueTypedDict.value_type, Schema)
        ):
            schema = common.resolve_schema_instance(self.ValueTypedDict.value_type)
            result.update(self._convert_with_schema(dynamic_fields, schema_func=schema.dump))
        else:
            raise ValidationError(f"Data type is not known: {type(obj)}")

        if self._hooks[POST_DUMP]:
            result = self._invoke_dump_processors(POST_DUMP, result, many=many, original_data=obj)

        return result


class LazySequence(Sequence):
    """Calculates the items of the list on first access"""

    def __init__(self, compute_items: typing.Callable[[], list[Schema]]) -> None:
        self._compute_items = compute_items

    @cached_property
    def _items(self) -> list[Schema]:
        return self._compute_items()

    @override
    @overload
    def __getitem__(self, i: int) -> Schema:
        return self._items[i]

    @override
    @overload
    def __getitem__(self, i: slice) -> Sequence[Schema]:
        return self._items[i]

    @override
    def __getitem__(self, i: int | slice) -> Schema | Sequence[Schema]:
        return self._items[i]

    @override
    def __len__(self) -> int:
        return len(self._items)


class MultiNested(base.OpenAPIAttributes, ma_fields.Field):
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
        ...     required1 = ma_fields.String(required=True)
        ...     optional1 = ma_fields.String()

        >>> class Schema2(BaseSchema):
        ...     cast_to_dict = True
        ...     required2 = ma_fields.String(required=True)
        ...     optional2 = ma_fields.String()
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
        >>> list(nested.declared_fields['entries'].metadata["anyOf"])
        [<Schema1(many=False)>, <Schema2(many=False)>]

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
            ...     dump_only = ma_fields.String(dump_only=True)

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

            >>> MultiNested([Schema1(), Schema1()], merged=True).deserialize({})
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

    default_error_messages = {
        "type": "Incompatible data type. Received a(n) '{type}', but an associative value is required. Maybe you quoted a value that is meant to be an object?"
    }

    class ValidateOnDump(BaseSchema):
        cast_to_dict = True
        validate_on_dump = True

    Result = dict[str, typing.Any]

    def __init__(
        self,
        nested: typing.Sequence[type[Schema] | Schema | typing.Callable[[], type[Schema]]],
        mode: typing.Literal["anyOf", "allOf"] = "anyOf",
        *,
        default: typing.Any = ma_fields.missing_,  # type: ignore[attr-defined, unused-ignore]
        only: types.StrSequenceOrSet | None = None,
        exclude: types.StrSequenceOrSet = (),
        many: bool = False,
        unknown: str | None = None,
        # In this loop we do the following:
        #  1) we try to dump all the keys of a model
        #  2) when the dump succeeds, we remove all the dumped keys from the source
        #  3) we go to the next model and goto 1
        #
        # For this we assume the schema is always symmetrical (i.e. a round trip is
        # idempotent) to get at the original keys. If this is not true, there may be bugs.
        merged: bool = False,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(default=default, **kwargs)

        if unknown is not None:
            raise ValueError("unknown is not supported for MultiNested")

        if merged and many:
            raise NotImplementedError("merged=True with many=True is not supported.")

        if mode != "anyOf":
            raise NotImplementedError("allOf is not yet implemented.")

        self._context = getattr(self.parent, "context", {})
        self._context.update(self.metadata.get("context", {}))

        self._nested_args = nested

        # We must not evaluate self._nested now, but can only hand over a list like object to
        # marshmallow. So we use a small helper to do the late evaluation for us.
        self.metadata["anyOf"] = LazySequence(lambda: self._nested)

        self.mode = mode
        self.only = only
        self.exclude = exclude
        self.many = many
        self.merged = merged
        # When we are merging, we don't want to have errors due to cross-schema validation.
        # When we operate in standard mode, we really want to know these errors.
        self.unknown = EXCLUDE if self.merged else RAISE

    @cached_property
    def _nested(self) -> list[Schema]:
        nested = []
        schema_inst: Schema
        for schema in self._nested_args:
            if callable(schema):
                schema = schema()
            schema_inst = common.resolve_schema_instance(schema)
            schema_inst.context.update(self._context)
            if not self._has_fields(schema_inst):
                # NOTE
                # We want all values to be included in the result, even if the schema hasn't
                # defined any fields on it. This is, because these schemas are used to validate
                # through the hooks @post_load, @pre_dump, etc.
                schema_inst.unknown = INCLUDE

            nested.append(schema_inst)

        # We need to check that the key names of all schemas are completely disjoint, because
        # we can't represent multiple schemas with the same key in merge-mode.
        if self.merged:
            set1: set[str] = set()
            for schema_inst in nested:
                keys = set(schema_inst.declared_fields.keys())
                if not set1.isdisjoint(keys):
                    wrong_keys = ", ".join(repr(key) for key in sorted(set1.intersection(keys)))
                    raise RuntimeError(
                        f"Schemas {nested} are not disjoint. "
                        f"Keys {wrong_keys} occur more than once."
                    )
                set1.update(keys)

        return nested

    def _nested_schemas(self) -> list[Schema]:
        return self._nested + [MultiNested.ValidateOnDump(unknown=RAISE)]

    @staticmethod
    def _has_fields(_schema: Schema) -> bool:
        return bool(_schema.declared_fields)

    def _add_error(
        self,
        error_store: ErrorStore,
        errors: str | list | dict,
    ) -> None:
        if isinstance(errors, dict):
            error_store.store_error(errors)  # type: ignore[no-untyped-call]
        elif isinstance(errors, list):
            error_store.errors.setdefault("_schema", []).extend(errors)
        elif isinstance(errors, str):
            error_store.errors.setdefault("_schema", []).append(errors)
        else:
            raise TypeError(f"Unexpected error message type: {type(errors)}")

    def _dump_schemas(self, scalar: Result) -> Result | list[Result]:
        rv = []
        error_store = ErrorStore()  # type: ignore[no-untyped-call]
        value = dict(scalar)
        value_initially_empty = not value

        for schema in self._nested_schemas():
            schema_inst = common.resolve_schema_instance(schema)
            try:
                if not (value_initially_empty or self._has_fields(schema_inst)):
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

    @override
    def _serialize(
        self,
        value: typing.Any,
        attr: str | None,
        obj: typing.Any,
        **kwargs: typing.Any,
    ) -> Result | list[Result]:
        error_store = ErrorStore()  # type: ignore[no-untyped-call]

        result: list[MultiNested.Result] = []
        if self.many:
            if utils.is_collection(value):
                for entry in value:
                    schemas = self._dump_schemas(entry)
                    assert isinstance(schemas, list), (
                        f"Expected a collection of schemas, got {schemas!r}"
                    )
                    result.extend(schemas)
            else:
                error_store.store_error(self._make_type_error(value))  # type: ignore[no-untyped-call]
        else:
            schemas = self._dump_schemas(value)
            assert isinstance(schemas, list), f"Expected a collection of schemas, got {schemas!r}"
            result.extend(schemas)

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

    def _make_type_error(self, value: object) -> ValidationError:
        return self.make_error(
            "type",
            input=value,
            type=value.__class__.__name__,
        )

    def _load_schemas(
        self, scalar: Result, partial: bool | types.StrSequenceOrSet | None = None
    ) -> Result:
        rv = {}
        error_store = ErrorStore()  # type: ignore[no-untyped-call]

        try:
            value = dict(scalar)
        except ValueError:
            raise self.make_error("type", type=type(scalar).__name__)
        value_initially_empty = not value

        for schema in self._nested_schemas():
            schema_inst = common.resolve_schema_instance(schema)
            if not (value_initially_empty or self._has_fields(schema_inst)):
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
        if (value_initially_empty or value_left_over) and error_store.errors:
            raise ValidationError(error_store.errors)
        return rv

    def _check_key_by_key(
        self,
        value: Result,
        schema_inst: Schema,
        error_store: ErrorStore,
    ) -> Result:
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

    @override
    def _deserialize(
        self,
        value: Result | list[Result],
        attr: str | None,
        data: typing.Mapping[str, typing.Any] | None,
        **kwargs: typing.Any,
    ) -> Result | list[Result]:
        if isinstance(value, list):
            if self.many:
                result = []
                for collection_entry in value:
                    result.append(self._load_schemas(collection_entry))
            else:
                raise self._make_type_error(value)

            return result
        else:
            return self._load_schemas(value)
