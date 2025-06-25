#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import itertools
from collections.abc import Mapping
from typing import Any

from marshmallow import fields, post_load, pre_dump, ValidationError


class Converter(abc.ABC):
    """A converter class to map values from and to Checkmk"""

    def to_checkmk(self, data: Any) -> object:
        raise NotImplementedError()

    def from_checkmk(self, data: Any) -> object:
        raise NotImplementedError()


type _TupleFields = tuple[str | _TupleFields, ...]
type _ConverterTuple = tuple[Converter | None | _ConverterTuple, ...]


class CheckmkTuple:
    """This is a helper mixin for tuples with a regular structure.

    Just add this mixin to your form class like so,

        class MyTupleForm(Schema, CheckmkTuple):
            tuple_fields = (..., )
            converters = (..., )
            ...

    Nested tuples are supported.

    To decode the following example

        ('ip_range', ('192.168.0.1', '192.168.0.10'))

    The `tuple_fields` attribute on the form class has to be set to ('type', ('ip_from', 'ip_to'))
    and this will result in the following dict

        {'type': 'ip_range', 'ip_from': '192.168.0.1', 'ip_to': '192.168.0.10'}

    """

    declared_fields: dict[str, fields.Field]
    tuple_fields: _TupleFields = ()
    converter: _ConverterTuple = ()

    @post_load
    def to_checkmk_tuple(self, data: Mapping[str, object], **kwargs: object) -> tuple:
        def _convert_to_tuple(
            _fields: _TupleFields, _converter: _ConverterTuple, _result: list
        ) -> tuple:
            for field, converter in itertools.zip_longest(_fields, _converter, fillvalue=None):
                if field is None:
                    raise ValueError("extra converter without field in CheckmkTuple")
                if isinstance(field, tuple):
                    assert converter is None or isinstance(converter, tuple), (
                        "Converter for nested field must be a tuple of converters"
                    )
                    _result.append(_convert_to_tuple(field, converter or tuple(), []))
                else:
                    try:
                        entry = data[field]
                    except KeyError as exc:
                        raise KeyError(f"{field} not in {data}") from exc
                    _result.append(
                        converter.to_checkmk(entry) if isinstance(converter, Converter) else entry
                    )
            return tuple(_result)

        return _convert_to_tuple(self.tuple_fields, self.converter, [])

    @pre_dump
    def from_checkmk_tuple(self, data: tuple, **kwargs: object) -> Mapping[str, object]:
        # We use result as the aggregation variable. In this case a dict we pass around everywhere.
        def _convert_tuple(
            _fields: _TupleFields,
            _data: tuple | list,
            _converter: _ConverterTuple,
            _result: dict[str, object],
        ) -> dict[str, object]:
            for field, value, converter in itertools.zip_longest(
                _fields,
                _data,
                _converter,
                fillvalue=None,
            ):
                if isinstance(field, tuple):
                    assert isinstance(value, tuple | list), (
                        f"Expected a tuple for field {field!r}, got {value!r}"
                    )
                    assert converter is None or isinstance(converter, tuple), (
                        "Converter for nested field must be a tuple of converters"
                    )
                    # Recursive call
                    _convert_tuple(field, value, converter or tuple(), _result)
                else:
                    if field not in self.declared_fields:
                        raise ValidationError(
                            f"Field {field!r} not declared in schema {self.__class__.__name__}. "
                            f"Declared are: {self.declared_fields!r}"
                        )
                    _result[field] = (
                        converter.from_checkmk(value) if isinstance(converter, Converter) else value
                    )

            return _result

        return _convert_tuple(self.tuple_fields, data, self.converter, {})
