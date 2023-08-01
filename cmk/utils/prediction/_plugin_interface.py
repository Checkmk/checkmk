#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for predictive monitoring / anomaly detection"""

import json
import logging
import time
from typing import assert_never, Literal

from cmk.utils.log import VERBOSE

from ._prediction import (
    compute_prediction,
    ConsolidationFunctionName,
    PREDICTION_PERIODS,
    PredictionData,
    PredictionParameters,
    PredictionStore,
    Timegroup,
)

_LevelsType = Literal["absolute", "relative", "stdev"]
_LevelsSpec = tuple[_LevelsType, tuple[float, float]]

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

    period_info = PREDICTION_PERIODS[params["period"]]
    now = time.time()
    if last_info.time + period_info.valid * period_info.slice < now:
        logger.log(VERBOSE, "Prediction of %s outdated", timegroup)
        return None

    jsonized_params = json.loads(json.dumps(params))
    if last_info.params != jsonized_params:
        logger.log(VERBOSE, "Prediction parameters have changed.")
        return None

    return store.get_data(timegroup)


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

    if (
        data_for_pred := _get_prediction(
            store=prediction_store,
            timegroup=timegroup,
            params=params,
        )
    ) is None:
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
    levels: _LevelsSpec,
    sig: Literal[1, -1],
    reference: float,
    stdev: float | None,
    levels_factor: float,
) -> tuple[float, float]:
    levels_type, (warn, crit) = levels

    match levels_type:
        case "absolute":
            reference_deviation = levels_factor
        case "relative":
            reference_deviation = reference / 100.0
        case "stdev":
            if stdev is None:  # just make explicit what would have happend anyway:
                raise TypeError("stdev is None")
            reference_deviation = stdev
        case _:
            assert_never(levels_type)

    return (
        reference + sig * warn * reference_deviation,
        reference + sig * crit * reference_deviation,
    )
