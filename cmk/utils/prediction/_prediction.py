#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, NamedTuple, Protocol, Self

from pydantic import BaseModel

from cmk.agent_based.prediction_backend import PredictionInfo

from ._file_layout import iter_prediction_files, meta_file_template, relative_data_file
from ._grouping import parse_period_name, PeriodName, time_slices

_DAY = 86400

_RRD_CONSOLIDATION_FUNCTION: Final = "max"

_RETENTION: Final[Mapping[PeriodName, int]] = {
    "wday": 7 * _DAY,
    "day": 31 * _DAY,
    "hour": 3 * _DAY,
    "minute": 3 * _DAY,
}


class MetricRecord(Protocol):
    @property
    def window(self) -> range: ...

    @property
    def values(self) -> Sequence[float | None]: ...


class DataStat(NamedTuple):
    average: float
    min_: float
    max_: float
    stdev: float | None

    @classmethod
    def from_values(cls, values: Sequence[float]) -> Self:
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


@dataclass(frozen=True)
class PredictionStore:
    path: Path

    @property
    def meta_file_path_template(self) -> str:
        return meta_file_template(self.path)

    def save_prediction(self, meta: PredictionInfo, prediction: PredictionData) -> None:
        data_file = self.path / relative_data_file(meta)
        data_file.parent.mkdir(exist_ok=True, parents=True)
        data_file.write_text(prediction.model_dump_json())

    def remove_outdated_predictions(self, now: float) -> None:
        for files in iter_prediction_files(self.path):
            period, start_time_str = files.info.name.split("-")[:2]
            if (period_name := parse_period_name(period)) is None:
                continue

            if (now - float(start_time_str)) > _RETENTION[period_name]:
                files.unlink()

    def iter_all_valid_predictions(
        self, now: float
    ) -> Iterator[tuple[PredictionInfo, PredictionData | None]]:
        for files in iter_prediction_files(self.path):
            try:
                meta = PredictionInfo.model_validate_json(files.info.read_text())
            except FileNotFoundError:
                continue

            if not meta.valid_interval[0] <= now < meta.valid_interval[1]:
                continue

            try:
                if files.info.stat().st_mtime <= files.data.stat().st_mtime:
                    yield meta, PredictionData.model_validate_json(files.data.read_text())
                    continue
            except FileNotFoundError:
                pass

            yield meta, None


def compute_prediction(
    info: PredictionInfo,
    get_recorded_data: Callable[[str, int, int], MetricRecord | None],
    now: float,
) -> PredictionData | None:
    time_windows = time_slices(
        int(now),
        info.params.horizon * 86400,
        info.params.period,
    )

    from_time = time_windows[0][0]
    rpn = f"{info.metric}.{_RRD_CONSOLIDATION_FUNCTION}"
    raw_slices = [
        (
            response.window,
            response.values,
            from_time - start,
        )
        for start, end in time_windows
        if (response := get_recorded_data(rpn, start, end))
    ]

    return (
        _calculate_data_for_prediction(raw_slices[0][0], raw_slices)
        if raw_slices
        else PredictionData(
            points=[None],
            start=from_time,
            step=1,
        )
    )


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
    return [
        (
            DataStat.from_values(point_line)
            if (point_line := [x for x in time_column if x is not None])
            else None
        )
        for time_column in zip(*slices)
    ]


def _std_dev(point_line: Sequence[float], average: float) -> float | None:
    samples = len(point_line)
    # In the case of a single data-point an unbiased standard deviation is undefined.
    if samples == 1:
        return None
    return math.sqrt(abs(sum(p**2 for p in point_line) - average**2 * samples) / float(samples - 1))
