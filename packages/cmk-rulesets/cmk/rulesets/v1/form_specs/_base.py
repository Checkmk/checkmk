#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from .._localize import Localizable

ModelT = TypeVar("ModelT")


@dataclass(frozen=True)
class Migrate(Generic[ModelT]):
    """Creates a transformation that changes the value every time it is loaded into the form spec.

    You can add a :class:`Migrate` instance to a form spec to update the value from an
    old version to be compatible with the current definition.
    This function is executed every time a stored value is loaded into the form spec,
    so it is important that it is idem potent.
    In other words: The function should change values only once, and in subsequent calls leave the
    value alone. Counter example: Simply multiplying a value by 10 will increase it during
    every (patch) upgrade, and every time the surprised user looks at their configuration.

    Args:
        model_to_form: Transforms the present parameter value ("consumer model")
                       to a value compatible with the current form specification.
    """

    update: Callable[[object], ModelT]


@dataclass(frozen=True, kw_only=True)
class FormSpec(Generic[ModelT]):
    """
    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        migrate: Convert a stored configuration to a data format this
          form spec understands.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    migrate: Migrate[ModelT] | None = None


@dataclass(frozen=True)
class DefaultValue(Generic[ModelT]):
    """Defines a default value for the form spec.

    Note that the default value *will* be part of the created configuration,
    unless the user changes it before hitting the save button.
    See also :class:`InputHint`.
    """

    value: ModelT


@dataclass(frozen=True)
class InputHint(Generic[ModelT]):
    """Defines an input hint for the form spec.

    Note that an input hint *will not* be part of the created configuration,
    unless the user enters a value before hitting the save button.
    See also :class:`DefaultValue`.
    """

    value: ModelT


Prefill = DefaultValue[ModelT] | InputHint[ModelT]
