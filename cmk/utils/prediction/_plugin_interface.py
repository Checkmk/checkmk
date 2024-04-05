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

from ._grouping import PREDICTION_PERIODS, Slice, Timegroup
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


def _get_prediction(
    store: PredictionStore,
    timegroup: Timegroup,
    params: PredictionParameters,
) -> PredictionData | None:
    """Return a valid prediction, if available

    No prediction is available if
    * no prediction meta data file is found
    * the prediction is outdated
    * no prediction for these parameters (time group) has been made yet
    * no prediction data file is found
    """
    if (last_info := store.get_info(timegroup)) is None:
        return None

    period_info = PREDICTION_PERIODS[params.period]
    now = time.time()
    if last_info.time + period_info.valid * period_info.slice < now:
        logger.log(VERBOSE, "Prediction of %s outdated", timegroup)
        return None

    if last_info.params != params:
        logger.log(VERBOSE, "Prediction parameters have changed.")
        return None

    return store.get_data(timegroup)


class PredictionUpdater:
    def __init__(
        self,
        host_name: HostName,
        service_description: ServiceName,
        params: PredictionParameters,
        partial_get_recorded_data: Callable[[str, str, str, int, int], MetricRecord],
    ) -> None:
        self.host_name: Final = host_name
        self.service_description: Final = service_description
        self.params: Final = params
        self.partial_get_recorded_data: Final = partial_get_recorded_data

    def __repr__(self) -> str:
        return repr(f"{self.__class__.__name__}Sentinel")

    def _get_recorded_data(self, metric_name: str, start: int, end: int) -> MetricRecord:
        return self.partial_get_recorded_data(
            self.host_name, self.service_description, metric_name, start, end
        )

    def _get_updated_prediction(
        self,
        dsname: str,
        now: int,
    ) -> PredictionData:
        period_info = PREDICTION_PERIODS[self.params.period]

        current_slice = Slice.from_timestamp(now, period_info)

        prediction_store = PredictionStore(
            PREDICTION_DIR,
            self.host_name,
            self.service_description,
            dsname,
        )

        if (
            data_for_pred := _get_prediction(
                store=prediction_store,
                timegroup=current_slice.group,
                params=self.params,
            )
        ) is None:
            info = PredictionInfo(
                name=current_slice.group,
                time=now,
                range=current_slice.interval,
                dsname=dsname,
                params=self.params,
            )
            logger.log(VERBOSE, "Calculating prediction data for time group %s", info.name)
            prediction_store.remove_prediction(info.name)

            data_for_pred = compute_prediction(
                info,
                now,
                period_info,
                self._get_recorded_data,
            )
            prediction_store.save_prediction(info, data_for_pred)

        return data_for_pred

    # levels_factor: this multiplies all absolute levels. Usage for example
    # in the cpu.loads check the multiplies the levels by the number of CPU
    # cores.
    def __call__(
        self,
        metric_name: str,
        levels_factor: float = 1.0,
    ) -> tuple[float | None, EstimatedLevels]:
        now = int(time.time())
        prediction = self._get_updated_prediction(metric_name, now)
        if (reference := prediction.predict(now)) is None:
            return None, (None, None, None, None)

        return reference.average, estimate_levels(
            reference_value=reference.average,
            stdev=reference.stdev,
            levels_lower=self.params.levels_lower,
            levels_upper=self.params.levels_upper,
            levels_upper_lower_bound=self.params.levels_upper_min,
            levels_factor=levels_factor,
        )


def estimate_levels(
    *,
    reference_value: float,
    stdev: float | None,
    levels_lower: LevelsSpec | None,
    levels_upper: LevelsSpec | None,
    levels_upper_lower_bound: tuple[float, float] | None,
    levels_factor: float,
) -> EstimatedLevels:
    estimated_upper_warn, estimated_upper_crit = (
        _get_levels_from_params(
            levels=levels_upper,
            sig=1,
            reference=reference_value,
            stdev=stdev,
            levels_factor=levels_factor,
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
            levels_factor=levels_factor,
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
    levels_factor: float,
) -> tuple[float, float] | tuple[None, None]:
    levels_type, (warn, crit) = levels

    match levels_type:
        case "absolute":
            reference_deviation = levels_factor
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
