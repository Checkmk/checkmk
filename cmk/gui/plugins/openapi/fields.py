#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A few upgraded Fields which handle some OpenAPI validation internally."""
import collections.abc
import json
import re
from typing import Any, Optional, Tuple, Callable

from marshmallow import fields as _fields, ValidationError
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.gui import watolib, valuespec as valuespec
from cmk.gui.exceptions import MKUserError

from cmk.gui.plugins.openapi.utils import BaseSchema
from cmk.utils.exceptions import MKException


class String(_fields.String):
    """"A string field which validates OpenAPI keys.

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
        'enum': "{value!r} is not one of the enum values: {enum!r}",
        'pattern': "{value!r} does not match pattern {pattern!r}.",
        'maxLength': "string {value!r} is too long. The maximum length is {maxLength}.",
        'minLength': "string {value!r} is too short. The minimum length is {minLength}.",
        'maximum': "{value!r} is bigger than the maximum ({maximum}).",
        'minimum': "{value!r} is smaller than the minimum ({minimum}).",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        enum = self.metadata.get('enum')
        if enum and value not in enum:
            self.fail("enum", value=value, enum=enum)

        pattern = self.metadata.get('pattern')
        if pattern is not None and not re.match("^(:?" + pattern + ")$", value):
            self.fail("pattern", value=value, pattern=pattern)

        max_length = self.metadata.get('maxLength')
        if max_length is not None and len(value) > max_length:
            self.fail("maxLength", value=value, maxLength=max_length)

        min_length = self.metadata.get('minLength')
        if min_length is not None and len(value) < min_length:
            self.fail("minLength", value=value, minLength=min_length)

        maximum = self.metadata.get('maximum')
        if maximum is not None and value > maximum:
            self.fail("maximum", value=value, maximum=maximum)

        minimum = self.metadata.get('minimum')
        if minimum is not None and value < minimum:
            self.fail("minimum", value=value, minimum=minimum)

        return value


class Integer(_fields.Integer):
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
        'enum': "{value!r} is not one of the enum values: {enum!r}",
        'maximum': "{value!r} is bigger than the maximum ({maximum}).",
        'minimum': "{value!r} is smaller than the minimum ({minimum}).",
        'exclusiveMaximum': "{value!r} is bigger or equal than the maximum ({exclusiveMaximum}).",
        'exclusiveMinimum': "{value!r} is smaller or equal than the minimum ({exclusiveMinimum}).",
        'multipleOf': "{value!r} is not a multiple of {multipleOf!r}."
    }

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)

        enum = self.metadata.get('enum')
        if enum and value not in enum:
            self.fail("enum", value=value, enum=enum)

        maximum = self.metadata.get('maximum')
        if maximum is not None and value > maximum:
            self.fail("maximum", value=value, maximum=maximum)

        minimum = self.metadata.get('minimum')
        if minimum is not None and value < minimum:
            self.fail("minimum", value=value, minimum=minimum)

        exclusive_maximum = self.metadata.get('exclusiveMaximum')
        if exclusive_maximum is not None and value >= exclusive_maximum:
            self.fail("exclusiveMaximum", value=value, exclusiveMaximum=exclusive_maximum)

        exclusive_minimum = self.metadata.get('exclusiveMinimum')
        if exclusive_minimum is not None and value <= exclusive_minimum:
            self.fail("exclusiveMinimum", value=value, exclusiveMinimum=exclusive_minimum)

        multiple_of = self.metadata.get('multipleOf')
        if multiple_of is not None and value % multiple_of != 0:
            self.fail("multipleOf", value=value, multipleOf=multiple_of)

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
        return frozenset((_freeze(key), _freeze(value))
                         for key, value in obj.items()
                         if not partial or key in partial)

    if isinstance(obj, list):
        return tuple([_freeze(entry) for entry in obj])

    return obj


class UniqueFields:
    """Mixin for collection fields to ensure uniqueness of containing elements

    Currently supported Fields are `List` and `Nested(..., many=True, ...)`

    """
    fail: Callable[..., None]

    default_error_messages = {
        'duplicate': "Duplicate entry found at entry #{idx}: {entry!r}",
        'duplicate_vary': ("Duplicate entry found at entry #{idx}: {entry!r} "
                           "(optional fields {optional!r})"),
    }

    def _verify_unique_schema_entries(self, value, fields):
        required_fields = tuple([name for name, field in fields.items() if field.required])
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

                    self.fail("duplicate_vary",
                              idx=idx,
                              optional=optional_values,
                              entry=required_values)
                else:
                    self.fail("duplicate", idx=idx, entry=dict(sorted(entry.items())))

            seen.add(entry_hash)

    def _verify_unique_scalar_entries(self, value):
        # FIXME: Pretty sure that List(List(List(...))) will break this.
        #        I have yet to see this use-case though.
        seen = set()
        for idx, entry in enumerate(value, start=1):
            if entry in seen:
                self.fail("duplicate", idx=idx, entry=entry)

            seen.add(entry)


class List(_fields.List, UniqueFields):
    """A list field, composed with another `Field` class or instance.

    Honors the OpenAPI key `uniqueItems`.

    Examples:

        With scalar values:

            >>> from marshmallow import Schema
            >>> class Foo(Schema):
            ...      id = String()
            ...      lists = List(String(), uniqueItems=True)

            >>> import pytest
            >>> from marshmallow import ValidationError
            >>> with pytest.raises(ValidationError) as exc:
            ...     Foo().load({'lists': ['2', '2']})
            >>> exc.value.messages
            {'lists': ["Duplicate entry found at entry #2: '2'"]}

        With nested schemas:

            >>> class Bar(Schema):
            ...      entries = List(Nested(Foo), allow_none=False, required=True, uniqueItems=True)

            >>> with pytest.raises(ValidationError) as exc:
            ...     Bar().load({'entries': [{'id': '1'}, {'id': '2'}, {'id': '2'}]})
            >>> exc.value.messages
            {'entries': ["Duplicate entry found at entry #3: {'id': '2'}"]}

            >>> with pytest.raises(ValidationError) as exc:
            ...     Bar().load({'entries': [{'lists': ['2']}, {'lists': ['2']}]})
            >>> exc.value.messages
            {'entries': ["Duplicate entry found at entry #2: {'lists': ['2']}"]}

        Some more examples:

            >>> class Service(Schema):
            ...      host = String(required=True)
            ...      description = String(required=True)
            ...      recur = String()

            >>> class Bulk(Schema):
            ...      entries = List(Nested(Service), uniqueItems=True)

            >>> with pytest.raises(ValidationError) as exc:
            ...     Bulk().load({"entries": [
            ...         {'host': 'example', 'description': 'CPU load', 'recur': 'week'},
            ...         {'host': 'example', 'description': 'CPU load', 'recur': 'day'},
            ...         {'host': 'host', 'description': 'CPU load'}
            ...     ]})
            >>> exc.value.messages
            {'entries': ["Duplicate entry found at entry #2: \
{'description': 'CPU load', 'host': 'example'} (optional fields {'recur': 'day'})"]}

    """
    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        if self.metadata.get('uniqueItems'):
            if isinstance(self.inner, Nested):
                self._verify_unique_schema_entries(value, self.inner.schema.fields)
            else:
                self._verify_unique_scalar_entries(value)

        return value


class Nested(_fields.Nested, UniqueFields):
    """Allows you to nest a marshmallow Schema inside a field.

    Honors the OpenAPI key `uniqueItems`.

    Examples:

        >>> from marshmallow import Schema
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
            ...                       required=False, missing=lambda: [])

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
            >>> assert schema.fields['entries'].missing is not _fields.missing_
            >>> schema.load({})
            {'entries': []}

    """

    # NOTE:
    # Sometimes, when using `missing` fields, a broken OpenAPI spec may be the result.
    # In this situation, it should be sufficient to replace the `missing` parameter with
    # a `lambda` which returns the same object, as callables are ignored by apispec.

    def _deserialize(self, value, attr, data, partial=None, **kwargs):
        self._validate_missing(value)
        if value is _fields.missing_:
            _miss = self.missing
            value = _miss() if callable(_miss) else _miss
        value = super()._deserialize(value, attr, data)
        if self.many and self.metadata.get('uniqueItems'):
            self._verify_unique_schema_entries(value, self.schema.fields)

        return value


# NOTE
# All these non-capturing match groups are there to properly distinguish the alternatives.
FOLDER_PATTERN = r"(?:(?:[~\\\/]|(?:[~\\\/][-_ a-zA-Z0-9]+)+)|[0-9a-fA-F]{32})"


class FolderField(String):
    """This field represents a WATO Folder.

    It will return a Folder instance, ready to use.
    """
    default_error_messages = {
        'not_found': "The folder {folder_id!r} could not be found.",
    }

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(pattern=FOLDER_PATTERN, **kwargs)

    @classmethod
    def _normalize_folder(cls, folder_id):
        r"""

        Args:
            folder_id:
        Examples:

            >>> FolderField._normalize_folder("\\")
            '/'

            >>> FolderField._normalize_folder("/foo/bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("\\foo\\bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("~foo~bar")
            '/foo/bar'

        Returns:

        """
        prev = folder_id
        separators = ['\\', '~']
        while True:
            for sep in separators:
                folder_id = folder_id.replace(sep, "/")
            if prev == folder_id:
                break
            prev = folder_id
        return folder_id

    @classmethod
    def load_folder(cls, folder_id: str) -> watolib.CREFolder:
        folder_id = cls._normalize_folder(folder_id)

        def _ishexdigit(hex_string: str) -> bool:
            try:
                int(hex_string, 16)
                return True
            except ValueError:
                return False

        if folder_id == '/':
            folder = watolib.Folder.root_folder()
        elif _ishexdigit(folder_id):
            folder = watolib.Folder.by_id(folder_id)
        else:
            folder = watolib.Folder.folder(folder_id[1:])

        return folder

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        try:
            return self.load_folder(value)
        except MKException:
            if self.required:
                self.fail("not_found", folder_id=value)


class BinaryExprSchema(BaseSchema):
    """

    >>> q = {'left': 'name', 'op': '=', 'right': 'foo'}
    >>> result = BinaryExprSchema().load(q)
    >>> assert result == q

    """
    op = String(description="The operator.")
    left = String(description="The LiveStatus column name.",
                  pattern=r"([a-z]+\.)?[_a-z]+",
                  example="name")
    right = String(
        description="The value to compare the column to.")  # should be AnyOf(all openapi types)


class NotExprSchema(BaseSchema):
    """Expression negating another query expression.

    Examples:

        >>> input_expr = {'op': '=', 'left': 'foo.bar', 'right': 'foo'}
        >>> q = {'op': 'not', 'expr': input_expr}
        >>> result = NotExprSchema().load(q)
        >>> assert result == q

    """

    op = String(description="The operator. In this case `not`.")
    expr = Nested(
        lambda: ExprSchema(),  # pylint: disable=unnecessary-lambda
        description="The query expression to negate.",
    )


class LogicalExprSchema(BaseSchema):
    """Expression combining multiple other query expressions.
    """
    op = String(description="The operator.")
    # many=True does not work here for some reason.
    expr = List(
        Nested(
            lambda: ExprSchema(),  # pylint: disable=unnecessary-lambda
            description="A list of query expressions to combine.",
        ))


class ExprSchema(OneOfSchema):
    """

    Operators can be one of: AND, OR

    Examples:

        >>> q = {'op': 'and', 'expr': [
        ...         {'op': 'not', 'expr':
        ...             {'op': 'or', 'expr': [
        ...                 {'op': '=', 'left': 'name', 'right': 'foo'},
        ...                 {'op': '=', 'left': 'name', 'right': 'bar'},
        ...             ]},
        ...         },
        ...     ]}
        >>> result = ExprSchema().load(q)
        >>> assert result == q

    """
    type_field = 'op'
    type_field_remove = False
    type_schemas = {
        'and': LogicalExprSchema,
        'or': LogicalExprSchema,
        'not': NotExprSchema,
        '=': BinaryExprSchema,
        '~': BinaryExprSchema,
        '~~': BinaryExprSchema,
        '<': BinaryExprSchema,
        '>': BinaryExprSchema,
        '>=': BinaryExprSchema,
        '<=': BinaryExprSchema,
        '!=': BinaryExprSchema,
        '!~': BinaryExprSchema,
        '!~~': BinaryExprSchema,
        '!<': BinaryExprSchema,
        '!>': BinaryExprSchema,
        '!>=': BinaryExprSchema,
        '!<=': BinaryExprSchema,
    }

    def load(self, data, *, many=None, partial=None, unknown=None):
        # When being passed in via the query string, we may get the raw JSON string instead of
        # the deserialized dictionary. We need to unpack it ourselves.
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError as exc:
                raise ValidationError({
                    '_schema': [
                        f"Invalid JSON value: '{data}'",
                        str(exc),
                    ],
                })

        return super().load(data, many=many, partial=partial, unknown=unknown)


class LiveStatusColumn(String):
    """Represents a LiveStatus column.

    >>> class Hosts:
    ...      __tablename__ = 'hosts'
    ...      @classmethod
    ...      def __columns__(cls):
    ...          return ['foo']

    >>> LiveStatusColumn(table=Hosts).deserialize('foo')
    'foo'

    >>> import pytest
    >>> with pytest.raises(ValidationError) as exc:
    ...     LiveStatusColumn(table=Hosts).deserialize('bar')
    >>> exc.value.messages
    ['Unknown column: hosts.bar']

    """
    default_error_messages = {
        'unknown_column': "Unknown column: {table_name}.{column_name}",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        table = self.metadata['table']
        if value not in table.__columns__():
            self.fail(
                "unknown_column",
                table_name=table.__tablename__,
                column_name=value,
            )
        for column in self.metadata.get('mandatory', []):
            if column not in value:
                value.append(column)
        return value


HOST_NAME_REGEXP = '[-0-9a-zA-Z_.]+'


class HostField(String):
    """A field representing a hostname.

    """
    default_error_messages = {
        'should_exist': 'Host not found: {host_name!r}',
        'should_not_exist': 'Host {host_name!r} already exists.',
        'invalid_name': 'The provided name for host {host_name!r} is invalid: {invalid_reason!r}',
    }

    def __init__(
        self,
        example='example.com',
        pattern=HOST_NAME_REGEXP,
        required=True,
        validate=None,
        should_exist: bool = True,
        should_be_monitored: Optional[bool] = None,
        **kwargs,
    ):
        self._should_exist = should_exist
        self._should_be_monitored = should_be_monitored
        super().__init__(
            example=example,
            pattern=pattern,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        try:
            valuespec.Hostname().validate_value(value, self.name)
        except MKUserError as e:
            self.fail("invalid_name", host_name=value, invalid_reason=str(e))

        host = watolib.Host.host(value)
        if self._should_exist and not host:
            self.fail("should_exist", host_name=value)
        elif not self._should_exist and host:
            self.fail("should_not_exist", host_name=value)

        if self._should_be_monitored is not None:
            pass


Boolean = _fields.Boolean
Decimal = _fields.Decimal
DateTime = _fields.DateTime
Dict = _fields.Dict
Constant = _fields.Constant
Time = _fields.Time
Date = _fields.Date
Field = _fields.Field

# Shortcuts
Int = Integer
Bool = Boolean
Str = String

__all__ = [
    'Bool',
    'Boolean',
    'Constant',
    'DateTime',
    'Date',
    'Decimal',
    'Dict',
    'Int',
    'Integer',
    'List',
    'Nested',
    'Str',
    'String',
    'Time',
    'Field',
    'ExprSchema',
    'FolderField',
    'HostField',
    'FOLDER_PATTERN',
]
