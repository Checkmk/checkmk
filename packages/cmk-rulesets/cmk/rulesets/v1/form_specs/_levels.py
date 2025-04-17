#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypedDict

from .._localize import Help, Title
from ._base import DefaultValue, FormSpec, Prefill


@dataclass(frozen=True, kw_only=True)
class PredictiveLevels[_NumberT: (int, float)]:
    """Definition for levels based on a prediction of the monitored value.

    Usable only in conjunction with :class:`Levels`.

    Example:
    ********

    >>> predictive = PredictiveLevels(
    ...     reference_metric="mem_used_percent",
    ...     prefill_abs_diff=DefaultValue((5.0, 10.0)),
    ...     prefill_rel_diff=DefaultValue((10.0, 20.0)),
    ...     prefill_stdev_diff=DefaultValue((2.0, 4.0)),
    ... )

    Arguments:
    **********
    """

    reference_metric: str
    """The name of the metric that should be used to compute the prediction.

    This value is hardcoded by you, the developer.
    It is your responsibility to make sure that all plug-ins subscribing to the ruleset actually
    create this metric.
    Failing to do so will prevent the backend from providing a prediction, currently leading to an
    always OK service.
    """
    prefill_abs_diff: Prefill[tuple[_NumberT, _NumberT]]
    """Value to pre-populate the form fields with when the levels depend on the
    absolute difference to the predicted value. If None, the backend will decide whether to
    leave the field empty or to prefill it with a canonical value."""

    prefill_rel_diff: Prefill[tuple[float, float]] = DefaultValue((10.0, 20.0))
    """Value to pre-populate the form fields with when the levels depend on the
    relative difference to the predicted value. If None, the backend will decide whether to
    leave the field empty or to prefill it with a canonical value."""
    prefill_stdev_diff: Prefill[tuple[float, float]] = DefaultValue((2.0, 4.0))
    """Value to pre-populate the form fields with when the levels depend on
    the relation of the predicted value to the standard deviation. If None, the backend will
    decide whether to leave the field empty or to prefill it with a canonical value.
    """


class LevelDirection(enum.Enum):
    """Specifies a type of bound the levels represents"""

    UPPER = "upper"
    LOWER = "lower"


class _PredictiveLevelsT[_NumberT: (int, float)](TypedDict):
    period: Literal["wday", "day", "hour", "minute"]
    horizon: int
    levels: (
        tuple[Literal["absolute"], tuple[_NumberT, _NumberT]]
        | tuple[Literal["relative"], tuple[float, float]]
        | tuple[Literal["stdev"], tuple[float, float]]
    )
    bound: tuple[_NumberT, _NumberT] | None


type SimpleLevelsConfigModel[_NumberT: (int, float)] = (
    tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[_NumberT, _NumberT]]
)


type LevelsConfigModel[_NumberT: (int, float)] = (
    SimpleLevelsConfigModel[_NumberT]
    | tuple[
        Literal["cmk_postprocessed"], Literal["predictive_levels"], _PredictiveLevelsT[_NumberT]
    ]
)


class LevelsType(enum.Enum):
    """Type of levels configuration"""

    NONE = enum.auto()
    FIXED = enum.auto()
    PREDICTIVE = enum.auto()


@dataclass(frozen=True, kw_only=True)
class SimpleLevels[_NumberT: (int, float)](FormSpec[SimpleLevelsConfigModel[_NumberT]]):
    """Specifies a form for configuring levels without predictive levels.

    This creates a FormSpec that allows to configure simple levels, i.e.
    either configure to not use levels at all, or to configure fixed levels.

    Consumer model:
    ***************

    **Type**: ``_NoLevels`` | ``_FixedLevels``.

    The value presented to consumers will be crafted in a way that makes it a suitable
    argument for the ``check_levels`` function of the agent based API v2.
    They either represent that no levels should be applied, or they contain a 2-tuple
    of numbers representing the warning and critical levels. Here ``Number`` can be either
    ``float`` or ``int``, depending on the consumer model of the used form spec::

          _NoLevels = tuple[
              Literal["no_levels"],
              None,
          ]

          _FixedLevels = tuple[
              Literal["fixed"],
              tuple[Number, Number],
          ]

    **Example**: SimpleLevels used to configure no levels will look like ``("no_levels", None)``,
    levels used to configure fixed upper levels might be ``("fixed", (5.0, 10.0))``.

    Arguments:
    **********
    """

    title: Title | None = None
    help_text: Help | None = None
    migrate: Callable[[object], SimpleLevelsConfigModel[_NumberT]] | None = None
    custom_validate: tuple[Callable[[SimpleLevelsConfigModel[_NumberT]], object], ...] | None = None

    form_spec_template: FormSpec[_NumberT]
    """Template for the specification of the form fields of the warning and critical levels.
    If `title` or `prefill_value` are provided here, they will be ignored."""
    level_direction: LevelDirection
    """Specifies the type of bound the levels represents. This is used only to adjust the
    labels and error messages in the UI."""
    prefill_levels_type: DefaultValue[Literal[LevelsType.NONE, LevelsType.FIXED]] = DefaultValue(
        LevelsType.FIXED
    )
    """Pre-selected type of the levels (no levels or fixed levels)."""
    prefill_fixed_levels: Prefill[tuple[_NumberT, _NumberT]]
    """Value to pre-populate the form field for fixed levels with."""


@dataclass(frozen=True, kw_only=True)
class Levels[_NumberT: (int, float)](FormSpec[LevelsConfigModel[_NumberT]]):
    """Specifies a form for configuring levels including predictive levels

    This creates a FormSpec that extends the SimpleLevels with the possibility to configure
    predictive levels, i.e. levels that are based on a prediction of the monitored value.

    Consumer model:
    ***************

    **Type**: ``_NoLevels`` | ``_FixedLevels`` | ``_PredictiveLevels``.

    The value presented to consumers will be crafted in a way that makes it a suitable
    argument for the ``check_levels`` function of the agent based API.
    In addition to the two types defined in :class:`SimpleLevels`, this class also
    allows for predictive levels.
    The model of the predictive levels is::

        _PredictiveLevels = tuple[
            Literal["predictive"],
            # (reference_metric, predicted_value, levels_tuple)
            tuple[str, float | None, tuple[float, float] | None],
        ]

    The configured value will be presented to consumers as a 2-tuple consisting of
    the level type identifier ``"predictive"`` and a 3-tuple containing the name of the
    reference metric used for prediction, the predicted value and the resulting levels tuple.

    **Example**: Levels resulting from configured upper predictive levels might look
    like this::

        ("predictive", ("mem_used_percent", 42.1, (50.3, 60.7)))

    """

    title: Title | None = None
    help_text: Help | None = None
    migrate: Callable[[object], LevelsConfigModel[_NumberT]] | None = None
    custom_validate: tuple[Callable[[LevelsConfigModel[_NumberT]], object], ...] | None = None

    form_spec_template: FormSpec[_NumberT]
    """Template for the specification of the form fields of the warning and critical levels.
    If `title` or `prefill_value` are provided here, they will be ignored."""
    level_direction: LevelDirection
    """Specifies the type of bound the levels represents. This is used only to adjust the
    labels and error messages in the UI."""
    prefill_levels_type: DefaultValue[LevelsType] = DefaultValue(LevelsType.FIXED)
    """Pre-selected type of the levels (no levels, fixed levels or predictive levels)."""
    prefill_fixed_levels: Prefill[tuple[_NumberT, _NumberT]]
    """Value to pre-populate the form fields with."""
    predictive: PredictiveLevels[_NumberT]
    """Specification for the predictive levels."""
