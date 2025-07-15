#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import math
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Literal, NamedTuple, Protocol, Self

from pydantic import BaseModel

from cmk.ccc.hostaddress import HostName

from cmk.agent_based.prediction_backend import PredictionInfo

from ..misc import pnp_cleanup
from ..paths import predictions_dir
from ..servicename import ServiceName
from ._grouping import time_slices

logger = logging.getLogger("cmk.prediction")


LevelsSpec = tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]


_DAY = 86400


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
    NAME_TEMPLATE = "{meta.metric}/{meta.params.period}-{meta.valid_interval[0]}-{meta.direction}"
    RETENTION = {
        "wday": 7 * _DAY,
        "day": 31 * _DAY,
        "hour": 3 * _DAY,
        "minute": 3 * _DAY,
    }

    def __init__(
        self,
        host_name: HostName,
        service_name: ServiceName,
    ) -> None:
        # Watch out. The CMC has to agree on the path.
        self.path: Path = predictions_dir / host_name / pnp_cleanup(service_name)

    @property
    def meta_file_path_template(self) -> str:
        # make base dir safe for .format call
        safe_template = str(self.path).replace("{", "{{").replace("}", "}}")
        return safe_template + f"/{self.NAME_TEMPLATE}{self.INFO_FILE_SUFFIX}"

    @classmethod
    def relative_data_file(cls, meta: PredictionInfo) -> Path:
        return Path(cls.NAME_TEMPLATE.format(meta=meta)).with_suffix(cls.DATA_FILE_SUFFIX)

    def _data_file(self, meta: PredictionInfo) -> Path:
        return self.path / self.relative_data_file(meta=meta)

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

    def save_prediction(self, meta: PredictionInfo, prediction: PredictionData) -> None:
        data_file = self._data_file(meta)
        data_file.parent.mkdir(exist_ok=True, parents=True)
        data_file.write_text(prediction.model_dump_json())

    def iter_all_metadata_files(self) -> Iterable[Path]:
        if not self.path.exists():
            return ()
        return self.path.rglob(f"*{self.INFO_FILE_SUFFIX}")

    def remove_outdated_predictions(self, now: float) -> None:
        for info_path in self.iter_all_metadata_files():
            period, start_time_str = info_path.name.split("-")[:2]

            if (now - float(start_time_str)) > self.RETENTION[period]:
                info_path.unlink(missing_ok=True)
                info_path.with_suffix(self.DATA_FILE_SUFFIX).unlink(missing_ok=True)

    def iter_all_valid_predictions(
        self, now: float
    ) -> Iterator[tuple[PredictionInfo, PredictionData | None]]:
        for info_path in self.iter_all_metadata_files():
            try:
                meta = PredictionInfo.model_validate_json(info_path.read_text())
            except FileNotFoundError:
                continue

            if not meta.valid_interval[0] <= now < meta.valid_interval[1]:
                continue

            data_path = info_path.with_suffix(self.DATA_FILE_SUFFIX)

            try:
                if info_path.stat().st_mtime <= data_path.stat().st_mtime:
                    yield meta, PredictionData.model_validate_json(data_path.read_text())
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
    raw_slices = [
        (
            response.window,
            response.values,
            from_time - start,
        )
        for start, end in time_windows
        if (response := get_recorded_data(f"{info.metric}.max", start, end))
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
    "Statistically summarize all the upsampled RRD data"
    return [  # can't inline this b/c it is unit tested :-/
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
