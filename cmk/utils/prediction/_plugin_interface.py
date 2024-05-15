#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for predictive monitoring / anomaly detection"""

import logging
from collections.abc import Callable, Mapping
from typing import assert_never, Literal

from cmk.utils.log import VERBOSE

from cmk.agent_based.prediction_backend import PredictionInfo

from ._prediction import (
    compute_prediction,
    LevelsSpec,
    MetricRecord,
    PredictionData,
    PredictionStore,
)

EstimatedLevels = tuple[tuple[float, float] | None, tuple[float, float] | None]

logger = logging.getLogger("cmk.prediction")


def make_updated_predictions(
    store: PredictionStore,
    get_recorded_data: Callable[[str, int, int], MetricRecord | None],
    now: float,
) -> Mapping[int, tuple[float | None, tuple[float, float] | None]]:
    store.remove_outdated_predictions(now)
    return {
        hash(meta): _make_reference_and_prediction(
            meta, valid_prediction or _update_prediction(store, meta, get_recorded_data), now
        )
        for meta, valid_prediction in store.iter_all_valid_predictions(now)
    }


def _make_reference_and_prediction(
    meta: PredictionInfo,
    prediction: PredictionData | None,
    now: float,
) -> tuple[float | None, tuple[float, float] | None]:
    if prediction is None or (reference := prediction.predict(now)) is None:
        return None, None

    return reference.average, estimate_levels(
        reference_value=reference.average,
        stdev=reference.stdev,
        direction=meta.direction,
        levels=meta.params.levels,
        bound=meta.params.bound,
    )


def _update_prediction(
    store: PredictionStore,
    meta: PredictionInfo,
    get_recorded_data: Callable[[str, int, int], MetricRecord | None],
) -> PredictionData | None:
    logger.log(
        VERBOSE,
        "Predicting %s / %s / %s",
        meta.metric,
        meta.params.period,
        meta.valid_interval[0],
    )
    if (prediction := compute_prediction(meta, get_recorded_data)) is None:
        return None
    store.save_prediction(meta, prediction)
    return prediction


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
                case 0:
                    return None
                case None:
                    return None
                case _:
                    reference_deviation = stdev
        case _:
            assert_never(levels_type)

    return (
        reference + sig * warn * reference_deviation,
        reference + sig * crit * reference_deviation,
    )
