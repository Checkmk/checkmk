#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import assert_never, overload, TypeVar

T = TypeVar("T")


@overload
def denilled(obj: list[T | None]) -> list[T]: ...


@overload
def denilled(obj: dict[str, T | None]) -> dict[str, T]: ...


def denilled(
    obj: list[T | None] | dict[str, T | None],
) -> list[T] | dict[str, T]:
    """Remove all None values from a dict or list.

    Examples:

        >>> denilled({'a': None, 'foo': 'bar', 'b': None})
        {'foo': 'bar'}

        >>> denilled(['Foo', None, 'Bar'])
        ['Foo', 'Bar']

    Args:
        obj: Either a dict or a list.

    Returns:
        A dict or a list without values being None.
    """
    if isinstance(obj, list):
        return [entry for entry in obj if entry is not None]
    if isinstance(obj, dict):
        return {key: value for key, value in obj.items() if value is not None}
    return assert_never(type(obj))
