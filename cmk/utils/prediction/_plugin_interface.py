#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for predictive monitoring / anomaly detection"""

import json
import logging
import time
from typing import Literal

from cmk.utils.log import VERBOSE

from ._prediction import (
    compute_prediction,
    ConsolidationFunctionName,
    PREDICTION_PERIODS,
    PredictionData,
    PredictionInfo,
    PredictionParameters,
    PredictionStore,
    Timegroup,
)

_LevelsType = Literal["absolute", "relative", "stdev"]
_LevelsSpec = tuple[_LevelsType, tuple[float, float]]

EstimatedLevels = tuple[float | None, float | None, float | None, float | None]

logger = logging.getLogger("cmk.prediction")


def _is_prediction_up_to_date(
    last_info: PredictionInfo | None,
    timegroup: Timegroup,
    params: PredictionParameters,
) -> bool:
    """Check, if we need to (re-)compute the prediction file.

    This is the case if:
    - no prediction has been made yet for this time group
    - the prediction from the last time is outdated
    - the prediction from the last time was made with other parameters
    """
    if last_info is None:
        return False

    period_info = PREDICTION_PERIODS[params["period"]]
    now = time.time()
    if last_info.time + period_info.valid * period_info.slice < now:
        logger.log(VERBOSE, "Prediction of %s outdated", timegroup)
        return False

    jsonized_params = json.loads(json.dumps(params))
    if last_info.params != jsonized_params:
        logger.log(VERBOSE, "Prediction parameters have changed.")
        return False

    return True


# cf: consilidation function (MAX, MIN, AVERAGE)
# levels_factor: this multiplies all absolute levels. Usage for example
# in the cpu.loads check the multiplies the levels by the number of CPU
# cores.
def get_predictive_levels(
    hostname: str,
    service_description: str,
    dsname: str,
    params: PredictionParameters,
    cf: ConsolidationFunctionName,
    levels_factor: float = 1.0,
) -> tuple[float | None, EstimatedLevels]:
    now = int(time.time())
    period_info = PREDICTION_PERIODS[params["period"]]

    timegroup, rel_time = period_info.groupby(now)

    prediction_store = PredictionStore(hostname, service_description, dsname)
    prediction_store.clean_prediction_files(timegroup)

    data_for_pred: PredictionData | None = None
    if _is_prediction_up_to_date(
        last_info=prediction_store.get_info(timegroup),
        timegroup=timegroup,
        params=params,
    ):
        data_for_pred = prediction_store.get_data(timegroup)

    if data_for_pred is None:
        data_for_pred = compute_prediction(
            timegroup,
            prediction_store,
            params,
            now,
            period_info,
            hostname,
            service_description,
            dsname,
            cf,
        )

    # Find reference value in data_for_pred
    index = int(rel_time / data_for_pred.step)
    reference = dict(zip(data_for_pred.columns, data_for_pred.points[index]))

    return reference["average"], estimate_levels(
        reference_value=reference["average"],
        stdev=reference["stdev"],
        levels_lower=params.get("levels_lower"),
        levels_upper=params.get("levels_upper"),
        levels_upper_lower_bound=params.get("levels_upper_min"),
        levels_factor=levels_factor,
    )


def estimate_levels(
    *,
    reference_value: float | None,
    stdev: float | None,
    levels_lower: _LevelsSpec | None,
    levels_upper: _LevelsSpec | None,
    levels_upper_lower_bound: tuple[float, float] | None,
    levels_factor: float,
) -> EstimatedLevels:
    if not reference_value:  # No reference data available
        return (None, None, None, None)

    estimated_upper_warn, estimated_upper_crit = (
        _get_levels_from_params(
            levels=levels_upper,
            sig=1,
            reference_value=reference_value,
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
            reference_value=reference_value,
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
    levels: _LevelsSpec,
    sig: Literal[1, -1],
    reference_value: float,
    stdev: float | None,
    levels_factor: float,
) -> tuple[float, float]:
    levels_type, (warn, crit) = levels

    reference_deviation = _get_reference_deviation(
        levels_type=levels_type,
        reference_value=reference_value,
        stdev=stdev,
        levels_factor=levels_factor,
    )

    estimated_warn = reference_value + sig * warn * reference_deviation
    estimated_crit = reference_value + sig * crit * reference_deviation

    return estimated_warn, estimated_crit


def _get_reference_deviation(
    *,
    levels_type: _LevelsType,
    reference_value: float,
    stdev: float | None,
    levels_factor: float,
) -> float:
    if levels_type == "absolute":
        return levels_factor

    if levels_type == "relative":
        return reference_value / 100.0

    # levels_type == "stdev":
    if stdev is None:  # just make explicit what would have happend anyway:
        raise TypeError("stdev is None")

    return stdev
