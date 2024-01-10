#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for predictive monitoring / anomaly detection"""

import logging
import time
from collections.abc import Callable
from typing import assert_never, Final, Literal

from cmk.utils.hostaddress import HostName
from cmk.utils.log import VERBOSE
from cmk.utils.servicename import ServiceName

from ._grouping import PREDICTION_PERIODS, Slice
from ._paths import PREDICTION_DIR
from ._prediction import (
    compute_prediction,
    LevelsSpec,
    MetricRecord,
    PredictionData,
    PredictionInfo,
    PredictionParameters,
    PredictionStore,
)

EstimatedLevels = tuple[float | None, float | None, float | None, float | None]

logger = logging.getLogger("cmk.prediction")


_ONE_DAY = 24 * 3600


def _get_prediction(
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
    if (available_prediciton := store.get_info(required_prediction.name)) is None:
        return None

    if available_prediciton != required_prediction:
        logger.log(VERBOSE, "Prediction outdated or parameters have changed.")
        return None

    return store.get_data(available_prediciton.name)


class PredictionUpdater:
    def __init__(
        self,
        host_name: HostName,
        service_description: ServiceName,
        params: PredictionParameters,
        partial_get_recorded_data: Callable[[str, str, str, int, int], MetricRecord | None],
    ) -> None:
        self.host_name: Final = host_name
        self.service_description: Final = service_description
        self.params: Final = params
        self.partial_get_recorded_data: Final = partial_get_recorded_data

    def __repr__(self) -> str:
        return repr(f"{self.__class__.__name__}Sentinel")

    def _get_recorded_data(self, metric_name: str, start: int, end: int) -> MetricRecord | None:
        return self.partial_get_recorded_data(
            self.host_name, self.service_description, metric_name, start, end
        )

    def _get_updated_prediction(
        self,
        dsname: str,
        now: int,
    ) -> PredictionData | None:
        period_info = PREDICTION_PERIODS[self.params.period]

        current_slice = Slice.from_timestamp(now, period_info)
        start_of_day = _start_of_day(now)
        info = PredictionInfo(
            name=current_slice.group,
            valid_interval=(start_of_day, start_of_day + _ONE_DAY),
            dsname=dsname,
            params=self.params,
        )

        prediction_store = PredictionStore(
            PREDICTION_DIR,
            self.host_name,
            self.service_description,
            dsname,
        )

        if (
            data_for_pred := _get_prediction(
                prediction_store,
                info,
            )
        ) is None:
            logger.log(VERBOSE, "Calculating prediction data for time group %s", info.name)
            prediction_store.remove_prediction(info.name)

            if (
                data_for_pred := compute_prediction(
                    info,
                    self._get_recorded_data,
                )
            ) is None:
                return None

            prediction_store.save_prediction(info, data_for_pred)

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

        return reference.average, estimate_levels(
            reference_value=reference.average,
            stdev=reference.stdev,
            levels_lower=self.params.levels_lower,
            levels_upper=self.params.levels_upper,
            levels_upper_lower_bound=self.params.levels_upper_min,
        )


def _start_of_day(timestamp: int) -> int:
    t = time.localtime(timestamp)
    sec_of_day = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec
    return timestamp - sec_of_day


def estimate_levels(
    *,
    reference_value: float,
    stdev: float | None,
    levels_lower: LevelsSpec | None,
    levels_upper: LevelsSpec | None,
    levels_upper_lower_bound: tuple[float, float] | None,
) -> EstimatedLevels:
    estimated_upper_warn, estimated_upper_crit = (
        _get_levels_from_params(
            levels=levels_upper,
            sig=1,
            reference=reference_value,
            stdev=stdev,
        )
        if levels_upper
        else (None, None)
    )

    estimated_lower_warn, estimated_lower_crit = (
        _get_levels_from_params(
            levels=levels_lower,
            sig=-1,
            reference=reference_value,
            stdev=stdev,
        )
        if levels_lower
        else (None, None)
    )

    if levels_upper_lower_bound:
        estimated_upper_warn = (
            None
            if estimated_upper_warn is None
            else max(levels_upper_lower_bound[0], estimated_upper_warn)
        )
        estimated_upper_crit = (
            None
            if estimated_upper_crit is None
            else max(levels_upper_lower_bound[1], estimated_upper_crit)
        )

    return (estimated_upper_warn, estimated_upper_crit, estimated_lower_warn, estimated_lower_crit)


def _get_levels_from_params(
    *,
    levels: LevelsSpec,
    sig: Literal[1, -1],
    reference: float,
    stdev: float | None,
) -> tuple[float, float] | tuple[None, None]:
    levels_type, (warn, crit) = levels

    match levels_type:
        case "absolute":
            reference_deviation = 1.0
        case "relative" if reference == 0:
            return (None, None)
        case "relative":
            reference_deviation = reference / 100.0
        case "stdev":
            match stdev:
                case 0 | None:
                    return (None, None)
                case _:
                    reference_deviation = stdev
        case _:
            assert_never(levels_type)

    return (
        reference + sig * warn * reference_deviation,
        reference + sig * crit * reference_deviation,
    )
