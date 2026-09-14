#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

import pytest

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.graphing._prediction_page import _predictions_of, _selected_title
from cmk.gui.graphing._prediction_source import Direction
from cmk.gui.http import request as request_
from cmk.utils.prediction import PredictionData

_VALID_FROM = 1700000000
_VALID_UNTIL = _VALID_FROM + 86400
_ANOTHER_DAY = _VALID_FROM - 86400


def _info(
    metric: str,
    direction: Direction,
    valid_from: int = _VALID_FROM,
    period: Literal["wday", "day", "hour", "minute"] = "wday",
    duration: int = 86400,
) -> PredictionInfo:
    return PredictionInfo(
        valid_interval=(valid_from, valid_from + duration),
        metric=metric,
        direction=direction,
        params=PredictionParameters(period=period, horizon=90, levels=("absolute", (2.0, 4.0))),
    )


@dataclass
class _FakePredictions:
    stored: Sequence[PredictionInfo]

    def query_predicted_metrics(self) -> Sequence[str]:
        return sorted({info.metric for info in self.stored})

    def query_available_predictions(self, metric: str) -> Iterator[PredictionInfo]:
        yield from (info for info in self.stored if info.metric == metric)

    def query_prediction_data(self, meta: PredictionInfo) -> PredictionData:
        raise NotImplementedError


def test_a_metric_predicted_in_both_directions_becomes_one_graph() -> None:
    querier = _FakePredictions([_info("util", "upper"), _info("util", "lower")])

    predictions = _predictions_of(querier, ["util"])

    assert len(predictions) == 1


def test_two_hourly_predictions_of_one_day_stay_separate_graphs() -> None:
    querier = _FakePredictions(
        [
            _info("util", "upper", valid_from=_VALID_FROM, period="hour", duration=3600),
            _info("util", "upper", valid_from=_VALID_FROM + 3600, period="hour", duration=3600),
        ]
    )

    predictions = _predictions_of(querier, ["util"])

    assert len(predictions) == 2


def test_a_graph_knows_which_directions_it_has_levels_for() -> None:
    querier = _FakePredictions([_info("util", "upper"), _info("util", "lower")])

    [prediction] = _predictions_of(querier, ["util"])

    assert list(prediction.directions) == ["lower", "upper"]


def test_a_metric_predicted_in_one_direction_only_says_so() -> None:
    querier = _FakePredictions([_info("util", "upper")])

    [prediction] = _predictions_of(querier, ["util"])

    assert list(prediction.directions) == ["upper"]


def test_every_predicted_metric_of_the_service_gets_its_own_graph() -> None:
    querier = _FakePredictions([_info("util", "upper"), _info("load", "upper")])

    predictions = _predictions_of(querier, list(querier.query_predicted_metrics()))

    assert [str(prediction.metric_name) for prediction in predictions] == ["load", "util"]


def test_a_graph_is_drawn_over_the_day_its_prediction_is_valid_for() -> None:
    querier = _FakePredictions([_info("util", "upper")])

    [prediction] = _predictions_of(querier, ["util"])

    assert (prediction.valid_from, prediction.valid_until) == (_VALID_FROM, _VALID_UNTIL)


def test_each_stored_day_is_offered_separately() -> None:
    querier = _FakePredictions(
        [_info("util", "upper"), _info("util", "upper", valid_from=_ANOTHER_DAY)]
    )

    predictions = _predictions_of(querier, ["util"])

    assert len({prediction.title for prediction in predictions}) == 2


def test_a_service_without_any_prediction_says_so_rather_than_drawing_nothing() -> None:
    with pytest.raises(MKGeneralException, match="no prediction information"):
        _selected_title([])


def test_the_day_the_user_picked_wins(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
) -> None:
    request_.set_var("prediction_selection", "tuesday")

    assert _selected_title(["monday", "tuesday"]) == "tuesday"


def test_a_day_that_is_no_longer_stored_falls_back_to_an_offered_one(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
) -> None:
    request_.set_var("prediction_selection", "last year")

    assert _selected_title(["monday", "tuesday"]) == "monday"


@pytest.mark.parametrize("titles", [["only"], ["first", "second"]])
def test_the_oldest_stored_day_is_shown_by_default(
    titles: Sequence[str],
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
) -> None:
    assert _selected_title(titles) == titles[0]
