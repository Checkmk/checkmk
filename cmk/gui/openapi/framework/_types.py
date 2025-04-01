#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from typing import ClassVar, Protocol, TypedDict

from werkzeug.datastructures import Headers


# copied from typeshed
class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[object]]]


class RawRequestData(TypedDict):
    body: bytes | None
    path: dict[str, str]
    query: dict[str, list[str]]
    headers: Headers


class _BaseParameterAnnotation:
    __slots__ = ("description", "example")

    def __init__(self, *, description: str, example: str) -> None:
        super().__init__()
        self.description = description
        self.example = example

    def __repr__(self) -> str:
        return self.__class__.__name__

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.description == other.description
            and self.example == other.example
        )


class FromPath(_BaseParameterAnnotation):
    __slots__ = ()


class _AliasedParameterAnnotation(_BaseParameterAnnotation):
    __slots__ = ("alias",)

    def __init__(self, *, description: str, example: str, alias: str | None = None) -> None:
        super().__init__(description=description, example=example)
        self.alias = alias

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(alias={self.alias!r})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.alias == other.alias
            and super().__eq__(other)
        )


class FromHeader(_AliasedParameterAnnotation):
    __slots__ = ()


class FromQuery(_AliasedParameterAnnotation):
    __slots__ = ("is_list",)

    def __init__(
        self, *, description: str, example: str, alias: str | None = None, is_list: bool = False
    ) -> None:
        super().__init__(description=description, example=example, alias=alias)
        self.is_list = is_list

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.is_list == other.is_list
            and super().__eq__(other)
        )


__all__ = [
    "DataclassInstance",
    "RawRequestData",
    "FromPath",
    "FromHeader",
    "FromQuery",
]
