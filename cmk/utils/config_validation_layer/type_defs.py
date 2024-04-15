#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Callable, overload

from pydantic import Field


class Omitted:
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[object], Omitted]]:
        yield cls.validate

    @classmethod
    def validate(cls, *v: object) -> Omitted:
        return cls()


def omitted_value() -> Any:
    return Omitted()


OMITTED_FIELD = Field(default_factory=omitted_value)


@overload
def remove_omitted(data: dict[str, Any]) -> dict[str, Any]: ...


@overload
def remove_omitted(data: list[Any]) -> list[Any]: ...


def remove_omitted(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: remove_omitted(value)
            for key, value in data.items()
            if not isinstance(value, Omitted)
        }
    if isinstance(data, list):
        return [remove_omitted(value) for value in data if not isinstance(value, Omitted)]
    return data
