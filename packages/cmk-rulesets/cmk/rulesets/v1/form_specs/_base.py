#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from .._localize import Help, Title

ModelT = TypeVar("ModelT")


@dataclass(frozen=True, kw_only=True)
class FormSpec(Generic[ModelT]):
    """Common base class for FormSpecs.

    This encapsulates some properties that all form specs have in common.
    Even if the ``migrate`` and ``custom_validate`` arguments do not always
    make sense, all form specs have them for consistency.

    Args:
        title: A human readable title.
        help_text: Description to help the user with the configuration.
        migrate: A function to change the value every time it is loaded into the form spec.
            You can add a migration function to a form spec to update the value from an
            old version to be compatible with the current definition.
            This function is executed every time a stored value is loaded into the form spec,
            so it is important that it is idem potent.
            In other words: The function should change values only once, and in subsequent calls
            leave the value alone.
            Counter example: Simply multiplying a value by 10 will increase it during every
            (patch) upgrade and also every time the surprised user looks at their configuration.
            By default the value remains unchanged.
        custom_validate: An optional additional validator.
            After the validation of the specific form spec is successful, this function is executed.
            It must raise a ValidationError in case validation fails.
            The return value of the function will not be used.

    """

    title: Title | None = None
    help_text: Help | None = None
    migrate: Callable[[object], ModelT] | None = None
    # Since we can't have a default `migrate` other than `None`, we also allow it here for
    # consistency, although a no-op validator would work as well.
    custom_validate: Callable[[ModelT], object] | None = None


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
