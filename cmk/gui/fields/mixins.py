#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import itertools
from typing import Dict, Optional, Tuple, Union

from marshmallow import fields, post_load, pre_dump, ValidationError


class Converter(abc.ABC):
    """A converter class to map values from and to Checkmk"""

    def to_checkmk(self, data):
        raise NotImplementedError()

    def from_checkmk(self, data):
        raise NotImplementedError()


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

    declared_fields: Dict[str, fields.Field]
    # NOTE: actually recursive, but what can you do: mypy doesn't do recursive yet.
    tuple_fields: Tuple[Union[Tuple[str, ...], str], ...] = ()
    converter: Tuple[Union[Tuple[Optional[Converter], ...], Optional[Converter]], ...] = ()

    @post_load
    def to_checkmk_tuple(self, data, **kwargs):
        def _convert_to_tuple(_fields, _converter, _result):
            for field, converter in itertools.zip_longest(_fields, _converter, fillvalue=None):
                if isinstance(field, tuple):
                    _result.append(_convert_to_tuple(field, converter or [], []))
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
    def from_checkmk_tuple(self, data, **kwargs):
        # We use result as the aggregation variable. In this case a dict we pass around everywhere.
        def _convert_tuple(_fields, _data, _converter, _result):
            for field, value, converter in itertools.zip_longest(
                _fields,
                _data,
                _converter,
                fillvalue=None,
            ):
                if isinstance(field, tuple):
                    # Recursive call
                    _convert_tuple(field, value, converter or [], _result)
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
