#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .._localize import Help, Title


@dataclass(frozen=True, kw_only=True)
class FormSpec[ModelT]:
    """Common base class for FormSpecs.

    This encapsulates some properties that all form specs have in common.
    Even if the ``migrate`` and ``custom_validate`` arguments do not always
    make sense, all form specs have them for consistency.

    Every form spec has a configuration model and a consumer model.
    The configuration model is the type of the value that is expected to be
    stored in the configuration. This type is the generic parameter of this class.

    The consumer model is the type of the value that is expected to be passed to the
    consumer of the ruleset. It will be the same as the configuration model in most cases,
    but there are exceptions.

    The consumer model is not part of the form spec, but it is important to keep it in mind
    when implementing the consumer of the ruleset.

    **Example:**

    A form spec that represents a single choice will have a configuration model of str
    and a consumer model of str. A form spec that represents predictive levels will have
    a configuration model containing the metric name and information on how to compute the
    predictive levels and a consumer model containing the metric name and the predictive
    levels themselves.

    Common arguments:
    *****************
    """

    title: Title | None = None
    """A human readable title."""
    help_text: Help | None = None
    """Description to help the user with the configuration."""
    migrate: Callable[[object], ModelT] | None = None
    """A function to change the value every time it is loaded into the form spec.

    You can add a migration function to a form spec to update the value from an
    old version to be compatible with the current definition.
    This function is executed every time a stored value is loaded into the form spec,
    so it is important that it is idem potent.
    In other words: The function should change values only once, and in subsequent calls
    leave the value alone.
    Counter example: Simply multiplying a value by 10 will increase it during every
    (patch) upgrade and also every time the surprised user looks at their configuration.
    By default the value remains unchanged.
    """
    # Since we can't have a default `migrate` other than `None`, we also allow it here for
    # consistency, although an empty tuple would work as well.
    custom_validate: Sequence[Callable[[ModelT], object]] | None = None
    """Optional additional validators.

    After the validation of the specific form spec is successful, these function are executed.
    They must raise a ValidationError in case validation fails.
    The return value of the functions will not be used.
    """


@dataclass(frozen=True)
class DefaultValue[ModelT]:
    """Defines a default value for the form spec.

    Note that the default value *will* be part of the created configuration,
    unless the user changes it before hitting the save button.
    See also :class:`InputHint`.
    """

    value: ModelT


@dataclass(frozen=True)
class InputHint[ModelT]:
    """Defines an input hint for the form spec.

    Note that an input hint *will not* be part of the created configuration,
    unless the user enters a value before hitting the save button.
    See also :class:`DefaultValue`.
    """

    value: ModelT


type Prefill[ModelT] = DefaultValue[ModelT] | InputHint[ModelT]
