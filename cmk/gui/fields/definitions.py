#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A few upgraded Fields which handle some OpenAPI validation internally."""
import collections.abc
import json
import re
import logging
import typing
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

import pytz
from marshmallow import fields as _fields, post_load
from marshmallow import utils, ValidationError
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

import cmk.utils.version as version
from cmk.gui import config, sites, watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.fields.base import BaseSchema, MultiNested, ValueTypedDictSchema
from cmk.gui.fields.utils import attr_openapi_schema, collect_attributes, ObjectContext, ObjectType
from cmk.gui.groups import load_group_information
from cmk.gui.watolib.passwords import contact_group_choices, password_exists
from cmk.utils.exceptions import MKException
from cmk.utils.livestatus_helpers.expressions import (
    NothingExpression,
    QueryExpression,
    tree_to_expr,
)
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Hostgroups, Hosts, Servicegroups
from cmk.utils.livestatus_helpers.types import Column, Table

if version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

_logger = logging.getLogger(__name__)


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
            raise self.make_error("enum", value=value, enum=enum)

        pattern = self.metadata.get('pattern')
        if pattern is not None and not re.match("^(:?" + pattern + ")$", value):
            raise self.make_error("pattern", value=value, pattern=pattern)

        max_length = self.metadata.get('maxLength')
        if max_length is not None and len(value) > max_length:
            raise self.make_error("maxLength", value=value, maxLength=max_length)

        min_length = self.metadata.get('minLength')
        if min_length is not None and len(value) < min_length:
            raise self.make_error("minLength", value=value, minLength=min_length)

        maximum = self.metadata.get('maximum')
        if maximum is not None and value > maximum:
            raise self.make_error("maximum", value=value, maximum=maximum)

        minimum = self.metadata.get('minimum')
        if minimum is not None and value < minimum:
            raise self.make_error("minimum", value=value, minimum=minimum)

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
            raise self.make_error("enum", value=value, enum=enum)

        maximum = self.metadata.get('maximum')
        if maximum is not None and value > maximum:
            raise self.make_error("maximum", value=value, maximum=maximum)

        minimum = self.metadata.get('minimum')
        if minimum is not None and value < minimum:
            raise self.make_error("minimum", value=value, minimum=minimum)

        exclusive_maximum = self.metadata.get('exclusiveMaximum')
        if exclusive_maximum is not None and value >= exclusive_maximum:
            raise self.make_error(
                "exclusiveMaximum",
                value=value,
                exclusiveMaximum=exclusive_maximum,
            )

        exclusive_minimum = self.metadata.get('exclusiveMinimum')
        if exclusive_minimum is not None and value <= exclusive_minimum:
            raise self.make_error(
                "exclusiveMinimum",
                value=value,
                exclusiveMinimum=exclusive_minimum,
            )

        multiple_of = self.metadata.get('multipleOf')
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
    make_error: Callable[..., ValidationError]

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

                    raise self.make_error(
                        "duplicate_vary",
                        idx=idx,
                        optional=optional_values,
                        entry=required_values,
                    )

                raise self.make_error("duplicate", idx=idx, entry=dict(sorted(entry.items())))

            seen.add(entry_hash)

    def _verify_unique_scalar_entries(self, value):
        # FIXME: Pretty sure that List(List(List(...))) will break this.
        #        I have yet to see this use-case though.
        seen = set()
        for idx, entry in enumerate(value, start=1):
            if entry in seen:
                raise self.make_error("duplicate", idx=idx, entry=entry)

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
FOLDER_PATTERN = r"(?:(?:[~\\\/]|(?:[~\\\/][-_ a-zA-Z0-9.]+)+)|[0-9a-fA-F]{32})"


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
        if 'description' not in kwargs:
            kwargs['description'] = "The path name of the folder."

        kwargs['description'] += (
            "\n\nPath delimiters can be either `~`, `/` or `\\`. Please use the one most "
            "appropriate for your quoting/escaping needs. A good default choice is `~`.")
        super().__init__(pattern=FOLDER_PATTERN, **kwargs)

    @classmethod
    def _normalize_folder(cls, folder_id):
        r"""Normalizes a folder representation

        Args:
            folder_id:
                A representation of a folder.

        Examples:

            >>> FolderField._normalize_folder("\\")
            '/'

            >>> FolderField._normalize_folder("~")
            '/'

            >>> FolderField._normalize_folder("/foo/bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("\\foo\\bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("~foo~bar")
            '/foo/bar'

        Returns:
            The normalized representation.

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
            folder_id = cls._normalize_folder(folder_id)
            folder = watolib.Folder.folder(folder_id[1:])

        return folder

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        try:
            return self.load_folder(value)
        except MKException:
            if value:
                raise self.make_error("not_found", folder_id=value)


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

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> input_expr = {'op': '=', 'left': 'hosts.name', 'right': 'foo'}
        >>> q = {'op': 'not', 'expr': input_expr}
        >>> result = NotExprSchema(context={'table': Hosts}).load(q)
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
            lambda *a, **kw: ExprSchema(*a, **kw),  # pylint: disable=unnecessary-lambda
            description="A list of query expressions to combine.",
        ))


class ExprSchema(OneOfSchema):
    """Top level class for query expression schema

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

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> schema = ExprSchema(context={'table': Hosts})
        >>> assert schema.load(q) == schema.load(json.dumps(q))

        >>> q = {'op': '=', 'left': 'foo', 'right': 'bar'}
        >>> schema.load(q)
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Table 'hosts' has no column 'foo'.

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

    def load(self, data, *, many=None, partial=None, unknown=None, **kwargs):
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
        elif isinstance(data, QueryExpression):
            return data

        if not self.context or 'table' not in self.context:
            raise RuntimeError(f"No table in context for field {self}")

        if not data:
            return NothingExpression()

        try:
            tree_to_expr(data, self.context['table'])
        except ValueError as e:
            raise ValidationError(str(e)) from e
        return super().load(data, many=many, partial=partial, unknown=unknown, **kwargs)


class _ExprNested(Nested):
    def _load(self, value, data, partial=None):
        _data = super()._load(value, data, partial=partial)
        return tree_to_expr(_data, table=self.metadata['table'])


def query_field(table: typing.Type[Table], required: bool = False, example=None) -> Nested:
    """Returns a Nested ExprSchema Field which validates a Livestatus query.

    Args:
        table:
            A Livestatus Table class.
        required:
            Whether the field shall be required.
        example:
            optional query example

    Returns:
        A marshmallow Nested field.

    """

    if example is None:
        example = json.dumps({
            'op': 'and',
            'expr': [{
                'op': '=',
                'left': 'name',
                'right': 'example.com'
            }, {
                'op': '!=',
                'left': 'state',
                'right': '0'
            }],
        })

    return _ExprNested(
        ExprSchema(context={'table': table}),
        table=table,
        description=(
            f"An query expression of the Livestatus {table.__tablename__!r} table in nested "
            "dictionary form. If you want to use multiple expressions, nest them with the "
            "AND/OR operators."),
        many=False,
        example=example,
        required=required,
    )


ColumnTypes = typing.Union[Column, str]


def column_field(
    table: typing.Type[Table],
    example: typing.List[str],
    required: bool = False,
    mandatory: Optional[typing.List[ColumnTypes]] = None,
) -> '_ListOfColumns':
    column_names: typing.List[str] = []
    if mandatory is not None:
        for col in mandatory:
            if isinstance(col, Column):
                column_names.append(col.name)
            else:
                column_names.append(col)

    return _ListOfColumns(
        _LiveStatusColumn(table=table, required=required),
        table=table,
        required=required,
        mandatory=column_names,
        missing=[getattr(table, col) for col in column_names],
        description=f"The desired columns of the `{table.__tablename__}` table. If left empty, a "
        "default set of columns is used.",
        example=example,
    )


class _ListOfColumns(List):
    """Manages a list of Livestatus columns and returns Column instances

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> cols = _ListOfColumns(
        ...     _LiveStatusColumn(table=Hosts),
        ...     table=Hosts,
        ... )
        >>> cols.deserialize(['name', 'alias'])
        [Column(hosts.name: string), Column(hosts.alias: string)]

        >>> cols = _ListOfColumns(
        ...     _LiveStatusColumn(table=Hosts),
        ...     table=Hosts,
        ...     mandatory=[Hosts.name],
        ... )
        >>> cols.deserialize(['alias'])
        [Column(hosts.name: string), Column(hosts.alias: string)]

        >>> class FooSchema(BaseSchema):
        ...      columns = _ListOfColumns(
        ...          _LiveStatusColumn(table=Hosts),
        ...          table=Hosts,
        ...          mandatory=[Hosts.name])
        >>> schema = FooSchema()
        >>> schema.load({'columns': ['alias']})
        OrderedDict([('columns', [Column(hosts.name: string), Column(hosts.alias: string)])])

    """
    default_error_messages = {
        'unknown_column': "Unknown default column: {table_name}.{column_name}",
    }

    def __init__(self, cls_or_instance: typing.Union[_fields.Field, type], **kwargs):
        super().__init__(cls_or_instance, **kwargs)
        table = self.metadata['table']
        for column in self.metadata.get('mandatory', []):
            if column not in table.__columns__():
                raise ValueError(f"Column {column!r} in parameter 'mandatory' is not a column "
                                 f"of table {table.__tablename__!r}")

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        table = self.metadata['table']
        for column in reversed(self.metadata.get('mandatory', [])):
            if isinstance(column, Column):
                column_name = column.name
            else:
                column_name = column
            if column_name not in value:
                value.insert(0, column_name)
        return [getattr(table, col) for col in value]


class _LiveStatusColumn(String):
    """Represents a LiveStatus column.

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> _LiveStatusColumn(table=Hosts).deserialize('name')
        'name'

        >>> import pytest
        >>> with pytest.raises(ValidationError) as exc:
        ...     _LiveStatusColumn(table=Hosts).deserialize('bar')
        >>> exc.value.messages
        ['Unknown column: hosts.bar']

    """
    default_error_messages = {
        'unknown_column': "Unknown column: {table_name}.{column_name}",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        table = self.metadata['table']
        if value not in table.__columns__():
            raise self.make_error(
                "unknown_column",
                table_name=table.__tablename__,
                column_name=value,
            )
        return value


HOST_NAME_REGEXP = '[-0-9a-zA-Z_.]+'


class HostField(String):
    """A field representing a hostname.

    """
    default_error_messages = {
        'should_exist': 'Host not found: {host_name!r}',
        'should_not_exist': 'Host {host_name!r} already exists.',
        'should_be_monitored': 'Host {host_name!r} exists, but is not monitored. '
                               'Activate the configuration?',
        'should_not_be_monitored': 'Host {host_name!r} exists, but should not be monitored. '
                                   'Activate the configuration?',
        'should_be_cluster': 'Host {host_name!r} is not a cluster host, but needs to be.',
        'should_not_be_cluster': "Host {host_name!r} may not be a cluster host, but is.",
        'invalid_name': 'The provided name for host {host_name!r} is invalid: {invalid_reason!r}',
    }

    def __init__(
        self,
        example='example.com',
        pattern=HOST_NAME_REGEXP,
        required=True,
        validate=None,
        should_exist: Optional[bool] = True,
        should_be_monitored: Optional[bool] = None,
        should_be_cluster: Optional[bool] = None,
        **kwargs,
    ):
        if not should_exist and should_be_cluster is not None:
            raise ValueError("Can't be missing and checking for cluster status!")

        self._should_exist = should_exist
        self._should_be_monitored = should_be_monitored
        self._should_be_cluster = should_be_cluster
        super().__init__(
            example=example,
            pattern=pattern,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        # Regex gets checked through the `pattern` of the String instance

        if self._should_exist is not None:
            host = watolib.Host.host(value)
            if self._should_exist and not host:
                raise self.make_error("should_exist", host_name=value)

            if not self._should_exist and host:
                raise self.make_error("should_not_exist", host_name=value)

        if self._should_be_cluster is not None and (host := watolib.Host.host(value)) is not None:
            if self._should_be_cluster and not host.is_cluster():
                raise self.make_error("should_be_cluster", host_name=value)

            if not self._should_be_cluster and host.is_cluster():
                raise self.make_error("should_not_be_cluster", host_name=value)

        if self._should_be_monitored is not None:
            monitored = host_is_monitored(value)
            if self._should_be_monitored and not monitored:
                raise self.make_error("should_be_monitored", host_name=value)

            if not self._should_be_monitored and monitored:
                raise self.make_error("should_not_be_monitored", host_name=value)


def group_is_monitored(group_type, group_name):
    # Danke mypy
    rv: bool
    if group_type == 'service':
        rv = bool(
            Query([Servicegroups.name], Servicegroups.name == group_name).first_value(sites.live()))
    elif group_type == 'host':
        rv = bool(Query([Hostgroups.name], Hostgroups.name == group_name).first_value(sites.live()))
    else:
        raise ValueError("Unknown group type.")
    return rv


def host_is_monitored(host_name: str) -> bool:
    return bool(Query([Hosts.name], Hosts.name == host_name).first_value(sites.live()))


def validate_custom_host_attributes(
    host_attributes: Dict[str, str],
    errors: typing.Literal["warn", "raise"],
) -> Dict[str, str]:
    """Validate only custom host attributes

    Args:
        host_attributes:
            The host attributes a dictionary with the attributes as keys (without any prefixes)
            and the values as values.

        errors:
            Either `warn` or `raise`. When set to `warn`, errors will just be logged, when set to
            `raise`, errors will lead to a ValidationError being raised.

    Returns:
        The data unchanged.

    Raises:
        ValidationError: when `errors` is set to `raise`

    """
    for name, value in host_attributes.items():
        try:
            attribute = watolib.host_attribute(name)
        except KeyError as exc:
            if errors == "raise":
                raise ValidationError(f"No such attribute, {name!r}", field_name=name) from exc

            _logger.error("No such attribute: %s", name)
            return host_attributes

        try:
            attribute.validate_input(value, "")
        except MKUserError as exc:
            if errors == "raise":
                raise ValidationError(str(exc)) from exc

            _logger.error("Error validating %s: %s", name, str(exc))

    return host_attributes


class CustomAttributes(ValueTypedDictSchema):
    value_type = (_fields.String(description="Each tag is a mapping of string to string"),)

    @post_load
    def _valid(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # NOTE
        # If an attribute gets deleted AFTER it has already been set to a host or a folder,
        # then this would break here. We therefore can't validate outbound data as thoroughly
        # because our own data can be inherently inconsistent.
        if self.context["direction"] == "outbound":  # pylint: disable=no-else-return
            return validate_custom_host_attributes(data, "warn")
        else:
            return validate_custom_host_attributes(data, "raise")


def attributes_field(object_type: ObjectType,
                     object_context: ObjectContext,
                     direction: typing.Literal["inbound", "outbound"],
                     description: Optional[str] = None,
                     example: Optional[Any] = None,
                     required: bool = False,
                     missing: Any = utils.missing,
                     many: bool = False,
                     names_only: bool = False) -> _fields.Field:
    """Build an Attribute Field

    Args:
        object_type:
            May be one of 'folder', 'host' or 'cluster'.

        object_context:
            May be 'create' or 'update'. Deletion is considered as 'update'.

        direction:
            If the data is *coming from* the user (inbound) or *going to* the user (outbound).

        description:
            A descriptive text of this field. Required.

        example:
            An example for the OpenAPI documentation. Required.

        required:
            Whether the field must be sent by the client or is option.

        missing:
        many:

        names_only:
            When set to True, the field will be a List of Strings which validate the tag names only.

    Returns:

    """
    if description is None:
        # SPEC won't validate without description, though the error message is very obscure, so we
        # clarify this here by force.
        raise ValueError("description is necessary.")

    if not names_only:
        return MultiNested(
            [
                attr_openapi_schema(object_type, object_context),
                CustomAttributes,
            ],
            metadata={"context": {
                "object_context": object_context,
                "direction": direction
            }},
            merged=True,  # to unify both models
            description=description,
            example=example,
            many=many,
            missing=dict if missing is utils.missing else utils.missing,
            required=required,
        )

    attrs = {attr.name for attr in collect_attributes(object_type, object_context)}

    def validate(value):
        if value not in attrs:
            raise ValidationError(f"Unknown attribute: {value!r}")

    return List(
        String(validate=validate),
        description=description,
        example=example,
        missing=missing,
        required=required,
    )


class SiteField(_fields.String):
    """A field representing a site name."""
    default_error_messages = {'unknown_site': 'Unknown site {site!r}'}

    def _validate(self, value):
        if value not in config.allsites().keys():
            raise self.make_error("unknown_site", site=value)


def customer_field(**kw):
    if version.is_managed_edition():
        return _CustomerField(**kw)
    return None


class _CustomerField(_fields.String):
    """A field representing a customer"""
    default_error_messages = {
        'invalid_global': 'Invalid customer: global',
        'should_exist': 'Customer missing: {customer!r}',
        'should_not_exist': 'Customer {customer!r} already exists.',
    }

    def __init__(
        self,
        example='provider',
        description="By specifying a customer, you configure on which sites the user object will be "
        "available. 'global' will make the object available on all sites.",
        required=True,
        validate=None,
        allow_global=True,
        should_exist: bool = True,
        **kwargs,
    ):
        self._should_exist = should_exist
        self._allow_global = allow_global
        super().__init__(
            example=example,
            description=description,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        if value == "global":
            value = managed.SCOPE_GLOBAL

        if not self._allow_global and value is None:
            raise self.make_error("invalid_global")

        included = value in managed.customer_collection()
        if self._should_exist and not included:
            raise self.make_error("should_exist", host_name=value)
        if not self._should_exist and included:
            raise self.make_error("should_not_exist", host_name=value)

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        return None if value == "global" else value


def verify_group_exists(group_type: str, name):
    specific_existing_groups = load_group_information()[group_type]
    return name in specific_existing_groups


class GroupField(String):
    """A field representing a group.

    """
    default_error_messages = {
        'should_exist': 'Group missing: {name!r}',
        'should_not_exist': 'Group {name!r} already exists.',
        'should_be_monitored': 'Group {host_name!r} exists, but is not monitored. '
                               'Activate the configuration?',
        'should_not_be_monitored': 'Group {host_name!r} exists, but should not be monitored. '
                                   'Activate the configuration?',
    }

    def __init__(
        self,
        group_type,
        example,
        required=True,
        validate=None,
        should_exist: bool = True,
        should_be_monitored: Optional[bool] = None,
        **kwargs,
    ):
        self._group_type = group_type
        self._should_exist = should_exist
        self._should_be_monitored = should_be_monitored
        if should_be_monitored and not should_exist:
            raise ValueError("No use in trying to validate deleted but still monitored groups.")

        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        group_exists = verify_group_exists(self._group_type, value)
        if self._should_exist and not group_exists:
            raise self.make_error("should_exist", name=value)

        if not self._should_exist and group_exists:
            raise self.make_error("should_not_exist", name=value)

        if self._should_be_monitored is not None:
            monitored = group_is_monitored(self._group_type, value)
            if self._should_be_monitored and not monitored:
                raise self.make_error("should_be_monitored", host_name=value)

            if not self._should_be_monitored and monitored:
                raise self.make_error("should_not_be_monitored", host_name=value)


class PasswordIdent(String):
    """A field representing a password identifier"""

    default_error_messages = {
        'should_exist': 'Identifier missing: {name!r}',
        'should_not_exist': 'Identifier {name!r} already exists.',
    }

    def __init__(
        self,
        example,
        required=True,
        validate=None,
        should_exist: bool = True,
        **kwargs,
    ):
        self._should_exist = should_exist
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        exists = password_exists(value)
        if self._should_exist and not exists:
            raise self.make_error("should_exist", name=value)

        if not self._should_exist and exists:
            raise self.make_error("should_not_exist", name=value)


class PasswordOwner(String):
    """A field representing a password owner group"""

    default_error_messages = {
        'invalid': 'Specified owner value is not valid: {name!r}',
    }

    def __init__(
        self,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        """Verify if the specified owner is valid for the logged-in user

        Non-admin users cannot specify admin as the owner

        """
        super()._validate(value)
        permitted_owners = [group[0] for group in contact_group_choices(only_own=True)]
        if config.user.may("wato.edit_all_passwords"):
            permitted_owners.append("admin")

        if value not in permitted_owners:
            raise self.make_error("invalid", name=value)


class PasswordShare(String):
    """A field representing a password share group"""

    default_error_messages = {
        'invalid': 'The password cannot be shared with specified group: {name!r}',
    }

    def __init__(
        self,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        shareable_groups = [group[0] for group in contact_group_choices()]
        if value not in ["all", *shareable_groups]:
            raise self.make_error("invalid", name=value)


def from_timestamp(value: float) -> datetime:
    stamp = datetime.utcfromtimestamp(value)
    return stamp.replace(tzinfo=pytz.utc)


def to_timestamp(value: datetime) -> float:
    return float(datetime.timestamp(value))


class Timestamp(_fields.DateTime):
    """A timestamp field for Checkmk timestamp

    Examples:

        >>> from marshmallow import Schema
        >>> class TestSchema(Schema):
        ...      ts_field = Timestamp()

        >>> value = {'ts_field': 0.0}

        >>> schema = TestSchema()
        >>> schema.dump({'ts_field': '0.0'})
        {'ts_field': '1970-01-01T00:00:00+00:00'}

        >>> schema.dump({'ts_field': 1622620683.60371})
        {'ts_field': '2021-06-02T07:58:03.603710+00:00'}

        >>> dumped = schema.dump(value)
        >>> dumped
        {'ts_field': '1970-01-01T00:00:00+00:00'}

        >>> loaded = schema.load(dumped)
        >>> loaded
        {'ts_field': 0.0}

        >>> assert loaded == value, f"{loaded!r} != {value!r}"

        >>> schema.load({'ts_field': 'foo'})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: ...

    """
    OBJ_TYPE = 'timestamp'

    default_error_messages = {'invalid': 'Not a valid timestamp: {input!r}'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        dt_obj = from_timestamp(float(value))
        return super()._serialize(dt_obj, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        val = super()._deserialize(value, attr, data, **kwargs)
        return datetime.timestamp(val)


__all__ = [
    'attributes_field',
    'customer_field',
    'CustomAttributes',
    'column_field',
    'ExprSchema',
    'FolderField',
    'FOLDER_PATTERN',
    'GroupField',
    'HostField',
    'Integer',
    'List',
    'Nested',
    'PasswordIdent',
    'PasswordOwner',
    'PasswordShare',
    'query_field',
    'SiteField',
    'String',
    'Timestamp',
    'MultiNested',
]
