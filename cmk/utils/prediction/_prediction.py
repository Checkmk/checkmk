#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import math
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Final, Literal, NamedTuple, Protocol, Self

from pydantic import BaseModel

from cmk.utils.log import VERBOSE

from cmk.agent_based.prediction_backend import PredictionInfo

from ._grouping import time_slices

logger = logging.getLogger("cmk.prediction")


LevelsSpec = tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]


class MetricRecord(Protocol):
    @property
    def window(self) -> range:
        ...

    @property
    def values(self) -> Sequence[float | None]:
        ...


class DataStat(NamedTuple):
    average: float
    min_: float
    max_: float
    stdev: float | None

    @classmethod
    def from_values(cls, values: Sequence[float]) -> Self:
        """Statistically summarize all the measured values"""
        average = sum(values) / float(len(values))
        return cls(
            average=average,
            min_=min(values),
            max_=max(values),
            stdev=_std_dev(values, average),
        )


class PredictionData(BaseModel, frozen=True):
    points: list[DataStat | None]
    start: int
    step: int

    def predict(self, timestamp: float) -> DataStat | None:
        unbound_index = round((timestamp - self.start) / self.step)
        # NOTE: A one hour prediction is valid for 24 hours, while the time range only covers one hour.
        # This is why we have to wrap larger indices back into the available list.
        # For consistenty we allow negative times as well.
        return self.points[unbound_index % len(self.points)]


class PredictionStore:
    DATA_FILE_SUFFIX = ""
    INFO_FILE_SUFFIX = ".info"

    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path: Final = path

    @staticmethod
    def relative_basename(metric: str, period: str, valid_from: int) -> Path:
        return Path(metric, f"{period}-{valid_from}")

    @classmethod
    def relative_data_file(cls, meta: PredictionInfo) -> Path:
        return PredictionStore.relative_basename(
            meta.metric, meta.params.period, meta.valid_interval[0]
        ).with_suffix(cls.DATA_FILE_SUFFIX)

    def _base_file(self, metric: str, period: str, valid_from: int) -> Path:
        return self.path / self.relative_basename(metric, period, valid_from)

    def _info_file(self, metric: str, period: str, valid_from: int) -> Path:
        return self._base_file(metric, period, valid_from).with_suffix(self.INFO_FILE_SUFFIX)

    def _data_file(self, metric: str, period: str, valid_from: int) -> Path:
        return self._base_file(metric, period, valid_from).with_suffix(self.DATA_FILE_SUFFIX)

    @staticmethod
    def filter_prediction_files_by_metric(
        metric: str, prediction_files: Iterable[Path]
    ) -> Iterator[Path]:
        yield from (
            prediction_file
            for prediction_file in prediction_files
            # note that a metric name cannot have a '/' in it.
            if metric in prediction_file.parts
        )

    def save_prediction(
        self,
        meta: PredictionInfo,
        data: PredictionData,
    ) -> None:
        info_file = self._info_file(meta.metric, meta.params.period, meta.valid_interval[0])
        info_file.parent.mkdir(exist_ok=True, parents=True)
        info_file.write_text(meta.model_dump_json())
        self._data_file(meta.metric, meta.params.period, meta.valid_interval[0]).write_text(
            data.model_dump_json()
        )

    def remove_prediction(self, metric: str, period: str, valid_from: int) -> None:
        self._data_file(metric, period, valid_from).unlink(missing_ok=True)
        self._info_file(metric, period, valid_from).unlink(missing_ok=True)

    def get_info(self, metric: str, period: str, valid_from: int) -> PredictionInfo | None:
        file_path = self._info_file(metric, period, valid_from)
        try:
            return PredictionInfo.model_validate_json(file_path.read_text())
        except FileNotFoundError as exc:
            logger.log(VERBOSE, "No prediction meta data: %s", exc)
        return None

    def get_data(self, meta: PredictionInfo) -> PredictionData | None:
        file_path = self._data_file(meta.metric, meta.params.period, meta.valid_interval[0])
        try:
            return PredictionData.model_validate_json(file_path.read_text())
        except FileNotFoundError as exc:
            logger.log(VERBOSE, "No prediction: %s", exc)
        return None


def compute_prediction(
    info: PredictionInfo,
    get_recorded_data: Callable[[str, int, int], MetricRecord | None],
) -> PredictionData | None:
    time_windows = time_slices(
        info.valid_interval[0], info.params.horizon * 86400, info.params.period
    )

    from_time = time_windows[0][0]
    raw_slices = [
        (
            response.window,
            response.values,
            from_time - start,
        )
        for start, end in time_windows
        if (response := get_recorded_data(f"{info.metric}.max", start, end))
    ]

    return _calculate_data_for_prediction(raw_slices[0][0], raw_slices) if raw_slices else None


def _calculate_data_for_prediction(
    youngest_range: range,
    raw_slices: Sequence[tuple[range, Sequence[float | None], int]],
) -> PredictionData:
    # Upsample all time slices to same resolution
    # We assume that the youngest slice has the finest resolution.
    slices = [
        _forward_fill_resample(
            current_range,
            values,
            range(youngest_range.start - shift, youngest_range.stop - shift, youngest_range.step),
        )
        for current_range, values, shift in raw_slices
    ]

    return PredictionData(
        points=_data_stats(slices),
        start=youngest_range.start,
        step=youngest_range.step,
    )


def _forward_fill_resample(
    current_range: range, values: Sequence[float | None], new_range: range
) -> Sequence[float | None]:
    if current_range == new_range:
        return values

    idx_max = len(values) - 1
    return [
        values[max(0, min(int((t - current_range.start) / current_range.step), idx_max))]
        for t in new_range
    ]


def _data_stats(slices: Iterable[Iterable[float | None]]) -> list[DataStat | None]:
    "Statistically summarize all the upsampled RRD data"
    return [  # can't inline this b/c it is unit tested :-/
        DataStat.from_values(point_line)
        if (point_line := [x for x in time_column if x is not None])
        else None
        for time_column in zip(*slices)
    ]


def _std_dev(point_line: Sequence[float], average: float) -> float | None:
    samples = len(point_line)
    # In the case of a single data-point an unbiased standard deviation is undefined.
    if samples == 1:
        return None
    return math.sqrt(
        abs(sum(p**2 for p in point_line) - average**2 * samples) / float(samples - 1)
    )
