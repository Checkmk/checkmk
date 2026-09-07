#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import functools
import operator
import types
from collections.abc import Iterable, Iterator, Mapping
from typing import Annotated, get_args, get_origin, TypeAliasType, TypeVar

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


def get_dataclass_origin(annotation: object) -> type | None:
    """Return the dataclass behind an annotation, also for a parameterized generic model.

    Annotated and TypeAliasType wrappers are *not* unwrapped, because a model behind such a
    wrapper was never walked as a model either.

    Examples:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Model[T]:
        ...     value: T
        >>> get_dataclass_origin(Model[int]) is Model
        True
        >>> get_dataclass_origin(list[int]) is None
        True
    """
    origin = get_origin(annotation) or annotation
    if isinstance(origin, type) and dataclasses.is_dataclass(origin):
        return origin

    return None


def substitute_type_vars(annotation: object, substitutions: Mapping[TypeVar, object]) -> object:
    """Replace the type variables in an annotation with their concrete type arguments.

    A `TypeAliasType` is not unwrapped. A parameterized alias keeps its arguments substituted,
    and the body of an alias cannot reference the type variables of the enclosing model.

    Examples:
        >>> T = TypeVar("T")
        >>> substitute_type_vars(list[T], {T: int})
        list[int]
        >>> substitute_type_vars(T | None, {T: int})
        int | None
        >>> substitute_type_vars(dict[str, T], {T: int})
        dict[str, int]
        >>> substitute_type_vars(list[str], {T: int})
        list[str]
    """
    if not substitutions:
        return annotation

    if isinstance(annotation, TypeVar):
        if annotation not in substitutions:
            raise ValueError(f"Unbound type variable: {annotation}")
        return substitutions[annotation]

    origin = get_origin(annotation)
    if origin is None or not (args := get_args(annotation)):
        return annotation

    substituted = tuple(substitute_type_vars(arg, substitutions) for arg in args)
    if substituted == args:
        return annotation

    if origin is Annotated:
        return Annotated[substituted]
    if isinstance(annotation, types.UnionType):
        return functools.reduce(operator.or_, substituted)

    return origin[substituted]


def iter_model_fields(
    annotation: object, *, path: str
) -> Iterator[tuple[dataclasses.Field[object], object]]:
    """Iterate the fields of a model, with the type arguments of a parameterized generic applied.

    `path` names the model in the error messages.

    Raises:
        ValueError: if the annotation is not a dataclass, if a generic model is not fully
            parameterized, or if a field uses a string annotation.
    """
    if (origin := get_dataclass_origin(annotation)) is None:
        raise ValueError(f"Expected a dataclass annotation for `{path}`.")

    parameters = getattr(origin, "__parameters__", ())
    arguments = get_args(annotation)
    if len(parameters) != len(arguments):
        raise ValueError(
            f"Expected {len(parameters)} type argument(s) for `{path}`, got {len(arguments)}. "
            f"Generic models must be fully parameterized."
        )

    substitutions = dict(zip(parameters, arguments, strict=True))
    for field in dataclasses.fields(origin):
        if isinstance(field.type, str):
            raise ValueError(f"String annotation for `{path}.{field.name}` is not allowed.")

        yield field, substitute_type_vars(field.type, substitutions)


def iter_dataclass_fields[T: DataclassInstance](dataclass: T) -> Iterable[tuple[str, object]]:
    """Iterate over the fields of a dataclass."""
    for field in dataclasses.fields(dataclass):
        value = getattr(dataclass, field.name)
        yield field.name, value
