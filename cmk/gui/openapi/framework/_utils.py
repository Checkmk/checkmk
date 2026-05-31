#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import types
from collections.abc import Iterable
from typing import Annotated, get_args, get_origin, TypeAliasType

from cmk.gui.utils.dataclasses import DataclassInstance


# TODO(PEP-747): replace `type | TypeAliasType | types.UnionType` with `TypeForm` once available;
#   the return type would then be `TypeForm` as well
def resolve_type(t: type | TypeAliasType | types.UnionType) -> type | types.UnionType:
    """Strip Annotated wrappers and unwrap TypeAliasType to reach the underlying concrete type.

    Handles arbitrarily nested combinations in any order. Only the outermost wrappers are
    removed — Annotated inside generic arguments (e.g. dict[str, Annotated[...]]) is preserved.
    Union types (A | B) are passed through unchanged.

    Examples:
        >>> resolve_type(Annotated[list[str], "foo"])
        list[str]
        >>> resolve_type(Annotated[Annotated[int, "foo"], "bar"])
        <class 'int'>
        >>> resolve_type(Annotated[dict[str, Annotated[list[str], "foo"]], "bar"])
        dict[str, typing.Annotated[list[str], 'foo']]
    """
    while isinstance(t, TypeAliasType) or get_origin(t) is Annotated:
        t = t.__value__ if isinstance(t, TypeAliasType) else get_args(t)[0]
    return t


# TODO(PEP-747): replace `type | TypeAliasType | types.UnionType` with `TypeForm`.
def get_resolved_origin(t: type | TypeAliasType | types.UnionType) -> type:
    """Get the origin of the resolved type, dropping Annotated and TypeAliasType first.

    For union types (A | B) returns types.UnionType (the class) as the origin.

    Examples:
        >>> get_resolved_origin(Annotated[list[str], "foo"])
        <class 'list'>
        >>> get_resolved_origin(Annotated[Annotated[int, "foo"], "bar"])
        <class 'int'>
        >>> get_resolved_origin(Annotated[dict[str, Annotated[list[str], "foo"]], "bar"])
        <class 'dict'>
    """
    resolved = resolve_type(t)
    if isinstance(resolved, types.UnionType):
        return types.UnionType
    return get_origin(resolved) or resolved


def iter_dataclass_fields[T: DataclassInstance](dataclass: T) -> Iterable[tuple[str, object]]:
    """Iterate over the fields of a dataclass."""
    for field in dataclasses.fields(dataclass):
        value = getattr(dataclass, field.name)
        yield field.name, value
