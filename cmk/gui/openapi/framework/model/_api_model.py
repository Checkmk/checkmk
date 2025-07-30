#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Callable
from typing import dataclass_transform, overload

from ._api_field import api_field


@overload
@dataclass_transform(kw_only_default=True, field_specifiers=(dataclasses.field, api_field))
def api_model[T](cls: type[T]) -> type[T]: ...


@overload
@dataclass_transform(kw_only_default=True, field_specifiers=(dataclasses.field, api_field))
def api_model[T](
    *,
    frozen: bool = False,
) -> Callable[[type[T]], type[T]]: ...


@dataclass_transform(kw_only_default=True, field_specifiers=(dataclasses.field, api_field))
def api_model[T](
    cls: type[T] | None = None,
    *,
    frozen: bool = False,
) -> type[T] | Callable[[type[T]], type[T]]:
    """Decorator to mark a class as an API model.

    This makes the model default to using slots and keyword-only constructors.
    It should be used for all request and response models in the REST API framework.
    The main (and so far only) benefit is that it allows type checkers to recognize the `api_field`
    decorator as a field specifier.
    """
    dataclass_wrapper = dataclasses.dataclass(
        kw_only=True,
        slots=True,
        frozen=frozen,
    )

    def wrapper(class_: type[T]) -> type[T]:
        """Wrapper to apply the dataclass_transform decorator."""
        return dataclass_wrapper(class_)

    if cls is not None:
        # decorator was used without parentheses, applied directly to a class
        return dataclass_wrapper(cls)

    return wrapper
