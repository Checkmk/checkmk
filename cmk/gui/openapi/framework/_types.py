#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from typing import ClassVar, Protocol, TypedDict

from werkzeug.datastructures import Headers

from .api_config import APIVersion


# copied from typeshed
class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[object]]]


class RawRequestData(TypedDict):
    body: bytes | None
    path: dict[str, str]
    query: dict[str, list[str]]
    headers: Headers


@dataclasses.dataclass(kw_only=True, slots=True)
class ApiContext:
    version: APIVersion


class _BaseParameterAnnotation:
    __slots__ = ("alias", "description", "example")

    def __init__(self, *, description: str, example: str, alias: str | None = None) -> None:
        super().__init__()
        self.alias = alias
        self.description = description
        self.example = example

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(alias={self.alias!r})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.alias == other.alias
            and self.description == other.description
            and self.example == other.example
        )


class PathParam(_BaseParameterAnnotation):
    __slots__ = ()


class HeaderParam(_BaseParameterAnnotation):
    __slots__ = ()


class QueryParam(_BaseParameterAnnotation):
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
    "ApiContext",
    "DataclassInstance",
    "RawRequestData",
    "PathParam",
    "HeaderParam",
    "QueryParam",
]
