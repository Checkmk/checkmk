#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for predictive monitoring / anomaly detection"""

import logging
import time
from collections.abc import Callable
from typing import assert_never, Final, Literal

from cmk.utils.log import VERBOSE

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters

from ._prediction import (
    compute_prediction,
    LevelsSpec,
    MetricRecord,
    PredictionData,
    PredictionStore,
)

EstimatedLevels = tuple[float | None, float | None, float | None, float | None]

logger = logging.getLogger("cmk.prediction")


def _get_prediction(
    metric: str,
    store: PredictionStore,
    required_prediction: PredictionInfo,
) -> PredictionData | None:
    """Return a valid prediction, if available

    No prediction is available if
    * no prediction meta data file is found
    * the prediction is outdated
    * no prediction for these parameters (time group) has been made yet
    * no prediction data file is found
    """
    if (
        available_prediciton := store.get_info(
            metric, required_prediction.params.period, required_prediction.valid_interval[0]
        )
    ) is None:
        return None

    if available_prediciton != required_prediction:
        logger.log(VERBOSE, "Prediction outdated or parameters have changed.")
        return None

    return store.get_data(available_prediciton)


class PredictionUpdater:
    def __init__(
        self,
        params: PredictionParameters,
        partial_get_recorded_data: Callable[[str, int, int], MetricRecord | None],
        store: PredictionStore,
    ) -> None:
        self.params: Final = params
        self.partial_get_recorded_data: Final = partial_get_recorded_data
        self.store: Final = store

    def __repr__(self) -> str:
        return repr(f"{self.__class__.__name__}Sentinel")

    def _get_recorded_data(self, metric_name: str, start: int, end: int) -> MetricRecord | None:
        return self.partial_get_recorded_data(metric_name, start, end)

    def _get_updated_prediction(
        self,
        metric: str,
        now: int,
    ) -> PredictionData | None:
        info = PredictionInfo.make(metric, self.params, now)

        if (data_for_pred := _get_prediction(metric, self.store, info)) is None:
            logger.log(
                VERBOSE,
                "Calculating prediction data for %s/%s",
                info.params.period,
                info.valid_interval[0],
            )
            self.store.remove_prediction(info.metric, info.params.period, info.valid_interval[0])

            if (
                data_for_pred := compute_prediction(
                    info,
                    self._get_recorded_data,
                )
            ) is None:
                return None

            self.store.save_prediction(info, data_for_pred)

        return data_for_pred

    # levels_factor: this multiplies all absolute levels.
    # Passed via `scale` argument of the legacy check_levels.
    # Only remaining usages in mem plugin and diskstat include.
    def __call__(
        self,
        metric_name: str,
    ) -> tuple[float | None, EstimatedLevels]:
        now = int(time.time())
        if (prediction := self._get_updated_prediction(metric_name, now)) is None or (
            reference := prediction.predict(now)
        ) is None:
            return None, (None, None, None, None)

        return reference.average, estimate_levels_quadruple(
            reference_value=reference.average,
            stdev=reference.stdev,
            levels_lower=self.params.levels_lower,
            levels_upper=self.params.levels_upper,
            levels_upper_lower_bound=self.params.levels_upper_min,
        )


def estimate_levels_quadruple(
    *,
    reference_value: float,
    stdev: float | None,
    levels_lower: LevelsSpec | None,
    levels_upper: LevelsSpec | None,
    levels_upper_lower_bound: tuple[float, float] | None,
) -> EstimatedLevels:
    upper = (
        estimate_levels(reference_value, stdev, "upper", levels_upper, levels_upper_lower_bound)
        if levels_upper
        else None
    ) or (None, None)
    lower = (
        estimate_levels(reference_value, stdev, "lower", levels_lower, None)
        if levels_lower
        else None
    ) or (None, None)

    return (upper[0], upper[1], lower[0], lower[1])


def estimate_levels(
    reference_value: float,
    stdev: float | None,
    direction: Literal["upper", "lower"],
    levels: LevelsSpec,
    bound: tuple[float, float] | None,
) -> tuple[float, float] | None:
    estimated = _compute_levels_from_params(
        levels=levels,
        sig=1 if direction == "upper" else -1,
        reference=reference_value,
        stdev=stdev,
    )
    if estimated is None or bound is None:
        return estimated

    match direction:
        case "upper":
            return (max(estimated[0], bound[0]), max(estimated[1], bound[1]))
        case "lower":
            return (min(estimated[0], bound[0]), min(estimated[1], bound[1]))
        case other:
            assert_never(other)


def _compute_levels_from_params(
    *,
    levels: LevelsSpec,
    sig: Literal[1, -1],
    reference: float,
    stdev: float | None,
) -> tuple[float, float] | None:
    levels_type, (warn, crit) = levels

    match levels_type:
        case "absolute":
            reference_deviation = 1.0
        case "relative" if reference == 0:
            return None
        case "relative":
            reference_deviation = reference / 100.0
        case "stdev":
            match stdev:
                case 0 | None:
                    return None
                case _:
                    reference_deviation = stdev
        case _:
            assert_never(levels_type)

    return (
        reference + sig * warn * reference_deviation,
        reference + sig * crit * reference_deviation,
    )
