#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from collections.abc import Iterable
from typing import Annotated, get_args, get_origin

from cmk.gui.openapi.framework._types import DataclassInstance


def strip_annotated(t: type) -> type:
    """Strip `Annotated` from a type, until we reach a non-`Annotated` type.

    Examples:
        >>> strip_annotated(Annotated[list[str], "foo"])
        list[str]
        >>> strip_annotated(Annotated[Annotated[int, "foo"], "bar"])
        <class 'int'>
        >>> strip_annotated(Annotated[dict[str, Annotated[list[str], "foo"]], "bar"])
        dict[str, typing.Annotated[list[str], 'foo']]
    """
    while get_origin(t) is Annotated:
        t = get_args(t)[0]
    return t


def get_stripped_origin(t: type) -> type:
    """Get the origin of a type, excluding `Annotated` itself.

    Examples:
        >>> get_stripped_origin(Annotated[list[str], "foo"])
        <class 'list'>
        >>> get_stripped_origin(Annotated[Annotated[int, "foo"], "bar"])
        <class 'int'>
        >>> get_stripped_origin(Annotated[dict[str, Annotated[list[str], "foo"]], "bar"])
        <class 'dict'>
    """
    stripped = strip_annotated(t)
    return get_origin(stripped) or stripped


def iter_dataclass_fields[T: DataclassInstance](dataclass: T) -> Iterable[tuple[str, object]]:
    """Iterate over the fields of a dataclass."""
    for field in dataclasses.fields(dataclass):
        value = getattr(dataclass, field.name)
        yield field.name, value
