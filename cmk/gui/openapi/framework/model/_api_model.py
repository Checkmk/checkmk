#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Callable
from typing import dataclass_transform, overload

from ._api_field import api_field


def _reject_generic_base(class_: type) -> None:
    for ancestor in class_.__mro__[1:]:
        if dataclasses.is_dataclass(ancestor) and getattr(ancestor, "__parameters__", None):
            raise TypeError(
                f"{class_.__name__} inherits from the generic model {ancestor.__name__}. Pydantic "
                f"does not apply the type arguments of a dataclass base, so the inherited fields "
                f"are validated against the type variables and not against the arguments. "
                f"Parameterize the model where it is used instead."
            )


@overload
@dataclass_transform(
    kw_only_default=True,
    frozen_default=True,
    field_specifiers=(dataclasses.field, api_field),
)
def api_model[T](cls: type[T]) -> type[T]: ...


@overload
@dataclass_transform(
    kw_only_default=True,
    frozen_default=True,
    field_specifiers=(dataclasses.field, api_field),
)
def api_model[T](*, slots: bool = True) -> Callable[[type[T]], type[T]]: ...


@dataclass_transform(
    kw_only_default=True,
    frozen_default=True,
    field_specifiers=(dataclasses.field, api_field),
)
def api_model[T](
    cls: type[T] | None = None, *, slots: bool = True
) -> type[T] | Callable[[type[T]], type[T]]:
    """Decorator to mark a class as an API model.

    This makes the model default to using slots and keyword-only constructors.
    It should be used for all request and response models in the REST API framework.
    It allows type checkers to recognize the `api_field` decorator as a field specifier, and it
    rejects a model that inherits from a generic model.
    """
    dataclass_wrapper = dataclasses.dataclass(
        kw_only=True,
        slots=slots,
        frozen=True,
    )

    def wrapper(class_: type[T]) -> type[T]:
        """Wrapper to apply the dataclass_transform decorator."""
        _reject_generic_base(class_)
        return dataclass_wrapper(class_)

    if cls is not None:
        # decorator was used without parentheses, applied directly to a class
        return wrapper(cls)

    return wrapper
