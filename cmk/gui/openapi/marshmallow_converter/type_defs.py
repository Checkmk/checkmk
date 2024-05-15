#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing

from marshmallow_oneofschema import OneOfSchema

from cmk.gui import valuespec
from cmk.gui.fields.base import BaseSchema

from cmk import fields

V_c = typing.TypeVar("V_c", bound=valuespec.ValueSpec)

BaseOrOneOfSchemaType: typing.TypeAlias = type[BaseSchema] | type[OneOfSchema]
ValuespecToSchemaTransformFunction = typing.Callable[[V_c, str | None, bool], fields.Field]
ValuespecToValueTransformFunction = typing.Callable[[V_c], typing.Any]


class ValuespecToSchemaMatchEntry(typing.NamedTuple, typing.Generic[V_c]):
    match_func: ValuespecToSchemaTransformFunction[V_c]
    has_name: bool


class ValuespecToValueMatchEntry(typing.NamedTuple, typing.Generic[V_c]):
    match_func: ValuespecToValueTransformFunction[V_c]


class ValuespecToSchemaMatchDict(typing.Protocol[V_c]):
    def __getitem__(self, item: type[V_c] | type[None]) -> ValuespecToSchemaMatchEntry[V_c]: ...

    def __setitem__(
        self, item: type[V_c] | type[None], value: ValuespecToSchemaMatchEntry[V_c]
    ) -> None: ...

    def get(self, item: type[V_c] | type[None]) -> ValuespecToSchemaMatchEntry[V_c] | None: ...


class ValuespecToValueMatchDict(typing.Protocol[V_c]):
    def __getitem__(self, item: type[V_c] | type[None]) -> ValuespecToValueMatchEntry[V_c]: ...

    def __setitem__(
        self, item: type[V_c] | type[None], value: ValuespecToValueMatchEntry[V_c]
    ) -> None: ...

    def get(self, item: type[V_c] | type[None]) -> ValuespecToValueMatchEntry[V_c] | None: ...
