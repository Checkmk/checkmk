#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from dataclasses import dataclass

from ._base import FormSpec, Migrate
from .basic import DataSize, Float, Integer, Percentage, TimeSpan


@dataclass(frozen=True, kw_only=True)
class PredictiveLevels:
    """Definition for levels that change over time based on a prediction of the monitored value.
    Usable only in conjunction with `Levels`

    Args:
        reference_metric: The name of the metric that should be used to compute the prediction.
         This value is hardcoded by you, the developer. It is your responsibility to make sure
         that all plugins subscribing to the ruleset actually create this metric.
         Failing to do so will prevent the backend from providing a prediction, currently leading
         to an always OK service.
        prefill_abs_diff: Value to pre-populate the form fields with when the levels depend on the
         absolute difference to the predicted value. If None, the backend will decide whether to
         leave the field empty or to prefill it with a canonical value.
        prefill_rel_diff: Value to pre-populate the form fields with when the levels depend on the
         relative difference to the predicted value. If None, the backend will decide whether to
         leave the field empty or to prefill it with a canonical value.
        prefill_stddev_diff: Value to pre-populate the form fields with when the levels depend on
         the relation of the predicted value to the standard deviation. If None, the backend will
         decide whether to leave the field empty or to prefill it with a canonical value.
    """

    reference_metric: str
    prefill_abs_diff: tuple[float, float] | None = None
    prefill_rel_diff: tuple[float, float] | None = None
    prefill_stddev_diff: tuple[float, float] | None = None


class LevelDirection(enum.Enum):
    """Specifies a type of bound the levels represents"""

    UPPER = "upper"
    LOWER = "lower"


@dataclass(frozen=True, kw_only=True)
class Levels(FormSpec):
    """Specifies a form for configuring levels

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        form_spec_template: Template for the specification of the form fields of the warning and
            critical levels. If `title` or `prefill_value` are provided here, they will be ignored
        level_direction: Do the levels represent the lower or the upper bound.
            It's used only to provide labels and error messages in the UI.
        predictive: Specification for the predictive levels
        prefill_fixed_levels: Value to pre-populate the form fields of fixed levels with.
            If None, the backend will decide whether to leave the field empty or to prefill it
            with a canonical value.
        transform: Transformation of the stored configuration

    Consumer model:
        **Type**: ``_NoLevels | _FixedLevels | _PredictiveLevels``

        The value presented to consumers will be crafted in a way that makes it a suitable
        argument for the ``check_levels`` function of the agent based API.
        These are the tree possible types defined in the consumer model::

          _NoLevels = tuple[
              Literal["no_levels"],
              None,
          ]

          _FixedLevels = tuple[
              Literal["fixed"],
              # (warn, crit)
              tuple[int, int] | tuple[float, float],
          ]

          _PredictiveLevels = tuple[
              Literal["predictive"],
              # (reference_metric, predicted_value, levels_tuple)
              tuple[str, float | None, tuple[float, float] | None],
          ]

        The configured value will be presented to consumers as a 2-tuple consisting of
        level type identifier and one of the 3 types: None, 2-tuple of numbers or a
        3-tuple containing the name of the reference metric used for prediction,
        the predicted value and the resulting levels tuple.

        **Example**: Levels used to configure no levels will look
        like this::

            ("no_levels", None)

        Levels used to configure fixed lower levels might look
        like this::

            ("fixed", (5.0, 1.0))

        Levels resulting from configured upper predictive levels might look
        like this::

            ("predictive", ("mem_used_percent", 42.1, (50.3, 60.7)))

    """

    form_spec_template: DataSize | Float | Integer | Percentage | TimeSpan
    level_direction: LevelDirection
    predictive: PredictiveLevels | None

    prefill_fixed_levels: tuple[float, float] | None = None

    transform: Migrate[object] | None = None
