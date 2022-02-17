#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections.abc
import re
from typing import Any, Optional, Protocol, Tuple

from marshmallow import fields, ValidationError


class OpenAPIAttributes:
    def __init__(self, *args, **kwargs):
        metadata = kwargs.setdefault("metadata", {})
        for key in [
            "description",
            "doc_default",
            "enum",
            "example",
            "maximum",
            "maxLength",
            "minimum",
            "minLength",
            "pattern",
            "format",
            "uniqueItems",
            "table",  # used for Livestatus ExprSchema, not an OpenAPI key
            "context",  # used in MultiNested, not an OpenAPI key
        ]:
            if key in kwargs:
                if key in metadata:
                    raise RuntimeError(f"Key {key!r} defined in 'metadata' and 'kwargs'.")
                metadata[key] = kwargs.pop(key)

        super().__init__(*args, **kwargs)


class String(OpenAPIAttributes, fields.String):
    """A string field which validates OpenAPI keys.

    Examples:

        It supports Enums:

            >>> String(enum=["World"]).deserialize("Hello")
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 'Hello' is not one of the enum values: ['World']

        It supports patterns:

            >>> String(pattern="World|Bob").deserialize("Bob")
            'Bob'

            >>> String(pattern="World|Bob").deserialize("orl")
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 'orl' does not match pattern 'World|Bob'.

            >>> String(pattern="World|Bob").deserialize("World!")
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 'World!' does not match pattern 'World|Bob'.

        It's safe to submit any UTF-8 character, be it encoded or not.

            >>> String().deserialize("Ümläut")
            'Ümläut'

            >>> String().deserialize("Ümläut".encode('utf-8'))
            'Ümläut'

        minLength and maxLength:

            >>> length = String(minLength=2, maxLength=3)
            >>> length.deserialize('A')
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: string 'A' is too short. \
The minimum length is 2.

            >>> length.deserialize('AB')
            'AB'
            >>> length.deserialize('ABC')
            'ABC'

            >>> length.deserialize('ABCD')
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: string 'ABCD' is too long. \
The maximum length is 3.

        minimum and maximum are also supported (though not very useful for Strings):

            >>> minmax = String(minimum="F", maximum="G")
            >>> minmax.deserialize('E')
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 'E' is smaller than the minimum (F).

            >>> minmax.deserialize('F')
            'F'
            >>> minmax.deserialize('G')
            'G'

            >>> minmax.deserialize('H')
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 'H' is bigger than the maximum (G).

    """

    default_error_messages = {
        "enum": "{value!r} is not one of the enum values: {enum!r}",
        "pattern": "{value!r} does not match pattern {pattern!r}.",
        "maxLength": "string {value!r} is too long. The maximum length is {maxLength}.",
        "minLength": "string {value!r} is too short. The minimum length is {minLength}.",
        "maximum": "{value!r} is bigger than the maximum ({maximum}).",
        "minimum": "{value!r} is smaller than the minimum ({minimum}).",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        enum = self.metadata.get("enum")
        if enum and value not in enum:
            raise self.make_error("enum", value=value, enum=enum)

        pattern = self.metadata.get("pattern")
        if pattern is not None and not re.match("^(:?" + pattern + ")$", value):
            raise self.make_error("pattern", value=value, pattern=pattern)

        max_length = self.metadata.get("maxLength")
        if max_length is not None and len(value) > max_length:
            raise self.make_error("maxLength", value=value, maxLength=max_length)

        min_length = self.metadata.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise self.make_error("minLength", value=value, minLength=min_length)

        maximum = self.metadata.get("maximum")
        if maximum is not None and value > maximum:
            raise self.make_error("maximum", value=value, maximum=maximum)

        minimum = self.metadata.get("minimum")
        if minimum is not None and value < minimum:
            raise self.make_error("minimum", value=value, minimum=minimum)

        return value


class Integer(OpenAPIAttributes, fields.Integer):
    """An integer field which validates OpenAPI keys.

    Examples:

        Minimum:

            >>> Integer(minimum=3).deserialize(3)
            3

            >>> Integer(minimum=3).deserialize(2)
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 2 is smaller than the minimum (3).

        Maximum:

            >>> Integer(maximum=3).deserialize(3)
            3

            >>> Integer(maximum=3).deserialize(4)
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 4 is bigger than the maximum (3).

        Exclusive Minimum:

            >>> Integer(exclusiveMinimum=3).deserialize(3)
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 3 is smaller or equal than the minimum (3).

        Exclusive Maximum:

            >>> Integer(exclusiveMaximum=3).deserialize(3)
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 3 is bigger or equal than the maximum (3).

        Multiple Of:

            >>> Integer(multipleOf=2).deserialize(4)
            4

            >>> Integer(multipleOf=2).deserialize(5)
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: 5 is not a multiple of 2.

    """

    default_error_messages = {
        "enum": "{value!r} is not one of the enum values: {enum!r}",
        "maximum": "{value!r} is bigger than the maximum ({maximum}).",
        "minimum": "{value!r} is smaller than the minimum ({minimum}).",
        "exclusiveMaximum": "{value!r} is bigger or equal than the maximum ({exclusiveMaximum}).",
        "exclusiveMinimum": "{value!r} is smaller or equal than the minimum ({exclusiveMinimum}).",
        "multipleOf": "{value!r} is not a multiple of {multipleOf!r}.",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)

        enum = self.metadata.get("enum")
        if enum and value not in enum:
            raise self.make_error("enum", value=value, enum=enum)

        maximum = self.metadata.get("maximum")
        if maximum is not None and value > maximum:
            raise self.make_error("maximum", value=value, maximum=maximum)

        minimum = self.metadata.get("minimum")
        if minimum is not None and value < minimum:
            raise self.make_error("minimum", value=value, minimum=minimum)

        exclusive_maximum = self.metadata.get("exclusiveMaximum")
        if exclusive_maximum is not None and value >= exclusive_maximum:
            raise self.make_error(
                "exclusiveMaximum", value=value, exclusiveMaximum=exclusive_maximum
            )

        exclusive_minimum = self.metadata.get("exclusiveMinimum")
        if exclusive_minimum is not None and value <= exclusive_minimum:
            raise self.make_error(
                "exclusiveMinimum", value=value, exclusiveMinimum=exclusive_minimum
            )

        multiple_of = self.metadata.get("multipleOf")
        if multiple_of is not None and value % multiple_of != 0:
            raise self.make_error("multipleOf", value=value, multipleOf=multiple_of)

        return value


def _freeze(obj: Any, partial: Optional[Tuple[str, ...]] = None):
    """Freeze all the things, so we can put them in a set.

    Examples:

        Note the different ordering of the keys. Even if Python3's dictionary order is based on
        insert time, this still works.

        >>> _freeze({'c': 'd', 'a': ['b']}) == _freeze({'a': ['b'], 'c': 'd'})
        True

        >>> _freeze({'c': 'd', 'a': ['b']}, partial=('a',)) == _freeze({'a': ['b'], 'c': 'd'})
        False

    Args:
        obj:

    Returns:

    """
    if isinstance(obj, collections.abc.Mapping):
        return frozenset(
            (_freeze(key), _freeze(value))
            for key, value in obj.items()
            if not partial or key in partial
        )

    if isinstance(obj, list):
        return tuple(_freeze(entry) for entry in obj)

    return obj


class HasMakeError(Protocol):
    def make_error(self, key: str, **kwargs: Any) -> ValidationError:
        ...


class UniqueFields:
    """Mixin for collection fields to ensure uniqueness of containing elements

    Currently supported Fields are `List` and `Nested(..., many=True, ...)`

    """

    default_error_messages = {
        "duplicate": "Duplicate entry found at entry #{idx}: {entry!r}",
        "duplicate_vary": (
            "Duplicate entry found at entry #{idx}: {entry!r} " "(optional fields {optional!r})"
        ),
    }

    def _verify_unique_schema_entries(self: HasMakeError, value, _fields):
        required_fields = tuple(name for name, field in _fields.items() if field.required)
        seen = set()
        for idx, entry in enumerate(value, start=1):
            # If some fields are required, we only freeze the required fields. This has the effect
            # that duplications of required fields are detected, essentially like primary-keys.
            # If this behaviour is somehow not desired in some circumstance (not known at the time
            # of implementation) then this needs to be refactored to support changing this
            # behaviour. Right now I don't see why we would need this though.
            entry_hash = hash(_freeze(entry, partial=(required_fields or None)))
            if entry_hash in seen:
                has_optional_fields = len(entry) > len(required_fields)
                if required_fields and has_optional_fields:
                    optional_values = {}
                    required_values = {}
                    for key, _value in sorted(entry.items()):
                        if key in required_fields:
                            required_values[key] = _value
                        else:
                            optional_values[key] = _value

                    raise self.make_error(
                        "duplicate_vary", idx=idx, optional=optional_values, entry=required_values
                    )
                raise self.make_error("duplicate", idx=idx, entry=dict(sorted(entry.items())))

            seen.add(entry_hash)

    def _verify_unique_scalar_entries(self: HasMakeError, value):
        # FIXME: Pretty sure that List(List(List(...))) will break this.
        #        I have yet to see this use-case though.
        seen = set()
        for idx, entry in enumerate(value, start=1):
            if entry in seen:
                raise self.make_error("duplicate", idx=idx, entry=entry)

            seen.add(entry)


class Nested(OpenAPIAttributes, fields.Nested, UniqueFields):
    """Allows you to nest a marshmallow Schema inside a field.

    Honors the OpenAPI key `uniqueItems`.

    Examples:

        >>> from marshmallow import Schema
        >>> from cmk.fields import String
        >>> class Service(Schema):
        ...      host = String(required=True)
        ...      description = String(required=True)
        ...      recur = String()

        Setting the `many` param will turn this into a list:

            >>> import pytest
            >>> from marshmallow import ValidationError

            >>> class Bulk(Schema):
            ...      entries = Nested(Service,
            ...                       many=True, uniqueItems=True,
            ...                       required=False, load_default=lambda: [])

            >>> entries = [
            ...     {'host': 'example', 'description': 'CPU load', 'recur': 'week'},
            ...     {'host': 'example', 'description': 'CPU load', 'recur': 'day'},
            ...     {'host': 'host', 'description': 'CPU load'}
            ... ]

            >>> with pytest.raises(ValidationError) as exc:
            ...     Bulk().load({'entries': entries})
            >>> exc.value.messages
            {'entries': ["Duplicate entry found at entry #2: \
{'description': 'CPU load', 'host': 'example'} (optional fields {'recur': 'day'})"]}

            >>> schema = Bulk()
            >>> assert schema.fields['entries'].missing is not fields.missing_
            >>> schema.load({})
            {'entries': []}

    """

    # NOTE:
    # Sometimes, when using `missing` fields, a broken OpenAPI spec may be the result.
    # In this situation, it should be sufficient to replace the `missing` parameter with
    # a `lambda` which returns the same object, as callables are ignored by apispec.

    def _deserialize(self, value, attr, data, partial=None, **kwargs):
        self._validate_missing(value)
        if value is fields.missing_:
            _miss = self.missing
            value = _miss() if callable(_miss) else _miss
        value = super()._deserialize(value, attr, data)
        if self.many and self.metadata.get("uniqueItems"):
            self._verify_unique_schema_entries(value, self.schema.fields)

        return value
