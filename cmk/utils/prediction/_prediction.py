#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import math
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Final, NamedTuple, NewType

import livestatus

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils import dateutils
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

logger = logging.getLogger("cmk.prediction")

Seconds = int
Timestamp = int
TimeRange = tuple[int, int]

TimeWindow = tuple[Timestamp, Timestamp, Seconds]
RRDColumnFunction = Callable[[Timestamp, Timestamp], "TimeSeries"]
TimeSeriesValue = float | None
TimeSeriesValues = list[TimeSeriesValue]
ConsolidationFunctionName = str
Timegroup = NewType("Timegroup", str)
EstimatedLevel = float | None
EstimatedLevels = tuple[EstimatedLevel, EstimatedLevel, EstimatedLevel, EstimatedLevel]
PredictionParameters = dict[str, Any]  # TODO: improve this type

_DataStatValue = float | None
_DataStat = list[_DataStatValue]
_TimeSlices = list[tuple[Timestamp, Timestamp]]
DataStats = list[_DataStat]

_GroupByFunction = Callable[[Timestamp], tuple[Timegroup, Timestamp]]


class _PeriodInfo(NamedTuple):
    slice: int
    groupby: _GroupByFunction
    valid: int


@dataclass(frozen=True)
class PredictionInfo:
    name: Timegroup
    time: int
    range: tuple[Timestamp, Timestamp]
    cf: ConsolidationFunctionName
    dsname: MetricName
    slice: int
    params: PredictionParameters

    @classmethod
    def loads(cls, raw: str, *, name: Timegroup) -> "PredictionInfo":
        data = json.loads(raw)
        range_ = data["range"]
        return cls(
            name=name,  # explicitly passed. (not in `data` before 2.1)
            time=int(data["time"]),
            range=(Timestamp(range_[0]), Timestamp(range_[1])),
            cf=ConsolidationFunctionName(data["cf"]),
            dsname=MetricName(data["dsname"]),
            slice=int(data["slice"]),
            params=dict(data["params"]),
        )

    def dumps(self) -> str:
        return json.dumps(asdict(self))


@dataclass(frozen=True)
class PredictionData:
    columns: list[str]
    points: DataStats
    num_points: int
    data_twindow: list[Timestamp]
    step: Seconds

    @classmethod
    def loads(cls, raw: str) -> "PredictionData":
        data = json.loads(raw)
        return cls(
            columns=[str(e) for e in data["columns"]],
            points=[[None if e is None else float(e) for e in elist] for elist in data["points"]],
            num_points=int(data["num_points"]),
            data_twindow=[Timestamp(e) for e in data["data_twindow"]],
            step=Seconds(data["step"]),
        )

    def dumps(self) -> str:
        return json.dumps(asdict(self))


def is_dst(timestamp: float) -> bool:
    """Check wether a certain time stamp lies with in daylight saving time (DST)"""
    return bool(time.localtime(timestamp).tm_isdst)


def timezone_at(timestamp: float) -> int:
    """Returns the timezone *including* DST shift at a certain point of time"""
    return time.altzone if is_dst(timestamp) else time.timezone


def rrd_timestamps(time_window: TimeWindow) -> list[Timestamp]:
    start, end, step = time_window
    return [] if step == 0 else [t + step for t in range(start, end, step)]


def aggregation_functions(
    series: TimeSeriesValues, aggr: ConsolidationFunctionName | None
) -> TimeSeriesValue:
    """Aggregate data in series list according to aggr

    If series has None values they are dropped before aggregation"""
    cleaned_series = [x for x in series if x is not None]
    if not cleaned_series:
        return None

    aggr = "max" if aggr is None else aggr.lower()
    match aggr:
        case "average":
            return fmean(cleaned_series)
        case "max":
            return max(cleaned_series)
        case "min":
            return min(cleaned_series)
        case _:
            raise ValueError(f"Invalid Aggregation function {aggr}, only max, min, average allowed")


class TimeSeries:
    """Describes the returned time series returned by livestatus

    - Timestamped values are valid for the measurement interval:
        [timestamp-step; timestamp[
      which means they are at the end of the interval.
    - The Series describes the interval [start; end[
    - Start has no associated value to it.

    args:
        data : list
            Includes [start, end, step, *values]
        timewindow: tuple
            describes (start, end, step), in this case data has only values
        conversion:
            optional conversion to account for user-specific unit settings
        **metadata:
            additional information arguments

    """

    def __init__(
        self,
        data: TimeSeriesValues,
        time_window: TimeWindow | None = None,
        conversion: Callable[[float], float] = lambda v: v,
        **metadata: str,
    ) -> None:
        if time_window is None:
            if not data or data[0] is None or data[1] is None or data[2] is None:
                raise ValueError(data)

            time_window = int(data[0]), int(data[1]), int(data[2])
            data = data[3:]

        assert time_window is not None
        self.start = int(time_window[0])
        self.end = int(time_window[1])
        self.step = int(time_window[2])
        self.values = [v if v is None else conversion(v) for v in data]
        self.metadata = metadata

    @property
    def twindow(self) -> TimeWindow:
        return self.start, self.end, self.step

    def bfill_upsample(self, twindow: TimeWindow, shift: Seconds) -> TimeSeriesValues:
        """Upsample by backward filling values

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        """
        upsa = []
        i = 0
        start, end, step = twindow
        current_times = rrd_timestamps(self.twindow)
        if start != self.start or end != self.end or step != self.step:
            for t in range(start, end, step):
                if t >= current_times[i] + shift:
                    i += 1
                upsa.append(self.values[i])

            return upsa

        return self.values

    def downsample(
        self, twindow: TimeWindow, cf: ConsolidationFunctionName | None = "max"
    ) -> TimeSeriesValues:
        """Downsample time series by consolidation function

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        cf : str ('max', 'average', 'min')
             consolidation function imitating RRD methods
        """
        dwsa = []
        co: TimeSeriesValues = []
        start, end, step = twindow
        desired_times = rrd_timestamps(twindow)
        if start != self.start or end != self.end or step != self.step:
            i = 0
            for t, val in self.time_data_pairs():
                if t > desired_times[i]:
                    dwsa.append(aggregation_functions(co, cf))
                    co = []
                    i += 1
                co.append(val)

            diff_len = len(desired_times) - len(dwsa)
            if diff_len > 0:
                dwsa.append(aggregation_functions(co, cf))
                dwsa += [None] * (diff_len - 1)

            return dwsa
        return self.values

    def time_data_pairs(self) -> list[tuple[Timestamp, TimeSeriesValue]]:
        return list(zip(rrd_timestamps(self.twindow), self.values))

    def __repr__(self) -> str:
        return f"TimeSeries({self.values}, timewindow={self.twindow})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeSeries):
            return NotImplemented

        return (
            self.start == other.start
            and self.end == other.end
            and self.step == other.step
            and self.values == other.values
        )

    def __getitem__(self, i: int) -> TimeSeriesValue:
        return self.values[i]

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[TimeSeriesValue]:
        yield from self.values

    def count(self, /, v: TimeSeriesValue) -> int:
        return self.values.count(v)


def lq_logic(filter_condition: str, values: list[str], join: str) -> str:
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    conditions = "".join(f"{filter_condition} {livestatus.lqencode(x)}\n" for x in values)
    connective = "%s: %d\n" % (join, len(values)) if len(values) > 1 else ""
    return conditions + connective


def livestatus_lql(
    host_names: list[str],
    columns: list[str],
    service_description: ServiceName | None = None,
) -> str:
    query_filter = "Columns: %s\n" % " ".join(columns)
    query_filter += lq_logic(
        "Filter: host_name =",
        host_names,
        "Or",
    )
    if service_description == "_HOST_" or service_description is None:
        what = "host"
    else:
        what = "service"
        query_filter += lq_logic("Filter: service_description =", [service_description], "Or")
    return f"GET {what}s\n{query_filter}"


def get_rrd_data(
    connection: livestatus.SingleSiteConnection,
    hostname: str,
    service_description: str,
    metric_name: str,
    cf: ConsolidationFunctionName,
    fromtime: Timestamp,
    untiltime: Timestamp,
    max_entries: int = 400,
) -> TimeSeries:
    """Fetch RRD historic metrics data of a specific service, within the specified time range

    returns a TimeSeries object holding interval and data information

    Query to livestatus always returns if database is found, thus:
    - Values can be None when there is no data for a given timestamp
    - Reply from livestatus/rrdtool is always enough to describe the
      queried interval. That means, the returned bounds are always outside
      the queried interval.

    LEGEND
    O timestamps of measurements
    | query values, fromtime and untiltime
    x returned start, no data contained
    v returned data rows, includes end y

    --O---O---O---O---O---O---O---O
            |---------------|
          x---v---v---v---v---y

    """

    step = 1
    rpn = f"{metric_name}.{cf.lower()}"  # "MAX" -> "max"
    point_range = ":".join(
        livestatus.lqencode(str(x)) for x in (fromtime, untiltime, step, max_entries)
    )
    column = f"rrddata:m1:{rpn}:{point_range}"

    lql = livestatus_lql([hostname], [column], service_description) + "OutputFormat: python\n"

    try:
        response = connection.query_value(lql)
    except livestatus.MKLivestatusNotFoundError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException(f"Cannot get historic metrics via Livestatus: {e}")

    if response is None:
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    return TimeSeries(response)


def rrd_datacolum(
    connection: livestatus.SingleSiteConnection,
    hostname: str,
    service_description: str,
    metric_name: str,
    cf: ConsolidationFunctionName,
) -> RRDColumnFunction:
    "Partial helper function to get rrd data"

    def time_boundaries(fromtime: Timestamp, untiltime: Timestamp) -> TimeSeries:
        return get_rrd_data(
            connection, hostname, service_description, metric_name, cf, fromtime, untiltime
        )

    return time_boundaries


class PredictionStore:
    def __init__(
        self,
        host_name: str,
        service_description: str,
        dsname: str,
    ) -> None:
        self._dir = Path(
            cmk.utils.paths.var_dir,
            "prediction",
            host_name,
            cmk.utils.pnp_cleanup(service_description),
            cmk.utils.pnp_cleanup(dsname),
        )

    def available_predictions(self) -> Iterable[PredictionInfo]:
        return (
            tg_info
            for f in self._dir.glob("*.info")
            if (tg_info := self.get_info(Timegroup(f.stem))) is not None
        )

    def _data_file(self, timegroup: Timegroup) -> Path:
        return self._dir / timegroup

    def _info_file(self, timegroup: Timegroup) -> Path:
        return self._dir / f"{timegroup}.info"

    def save_predictions(
        self,
        info: PredictionInfo,
        data_for_pred: PredictionData,
    ) -> None:
        self._dir.mkdir(exist_ok=True, parents=True)
        with self._info_file(info.name).open("w") as fname:
            fname.write(info.dumps())
        with self._data_file(info.name).open("w") as fname:
            fname.write(data_for_pred.dumps())

    def clean_prediction_files(self, timegroup: Timegroup, force: bool = False) -> None:
        # In previous versions it could happen that the files were created with 0 bytes of size
        # which was never handled correctly so that the prediction could never be used again until
        # manual removal of the files. Clean this up.
        for file_path in [self._data_file(timegroup), self._info_file(timegroup)]:
            with suppress(FileNotFoundError):
                if force or file_path.stat().st_size == 0:
                    file_path.unlink()
                    logger.log(VERBOSE, "Removed obsolete prediction %s", file_path.name)

    def get_info(self, timegroup: Timegroup) -> PredictionInfo | None:
        raw = self._read_file(self._info_file(timegroup))
        return None if raw is None else PredictionInfo.loads(raw, name=timegroup)

    def get_data(self, timegroup: Timegroup) -> PredictionData | None:
        raw = self._read_file(self._data_file(timegroup))
        return None if raw is None else PredictionData.loads(raw)

    def _read_file(self, file_path: Path) -> str | None:
        try:
            with file_path.open() as fh:
                return fh.read()
        except OSError:
            logger.log(VERBOSE, "No previous prediction for group %s available.", file_path.stem)
        except ValueError:
            logger.log(VERBOSE, "Invalid prediction file %s, old format", file_path)
            self.clean_prediction_files(Timegroup(file_path.stem), force=True)
        return None


def compute_prediction(
    timegroup: Timegroup,
    prediction_store: PredictionStore,
    params: PredictionParameters,
    now: int,
    period_info: _PeriodInfo,
    hostname: str,
    service_description: str,
    dsname: str,
    cf: ConsolidationFunctionName,
) -> PredictionData:
    logger.log(VERBOSE, "Calculating prediction data for time group %s", timegroup)
    prediction_store.clean_prediction_files(timegroup, force=True)

    time_windows = _time_slices(now, int(params["horizon"] * 86400), period_info, timegroup)

    rrd_datacolumn = rrd_datacolum(
        livestatus.LocalConnection(), hostname, service_description, dsname, cf
    )

    data_for_pred = _calculate_data_for_prediction(time_windows, rrd_datacolumn)

    info = PredictionInfo(
        name=timegroup,
        time=now,
        range=time_windows[0],
        cf=cf,
        dsname=dsname,
        slice=period_info.slice,
        params=params,
    )
    prediction_store.save_predictions(info, data_for_pred)

    return data_for_pred


def _window_start(timestamp: int, span: int) -> int:
    """If time is partitioned in SPAN intervals, how many seconds is TIMESTAMP away from the start

    It works well across time zones, but has an unfair behavior with daylight savings time."""
    return (timestamp - timezone_at(timestamp)) % span


def _group_by_wday(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    wday = time.localtime(t).tm_wday
    return Timegroup(dateutils.weekday_ids()[wday]), _window_start(t, 86400)


def _group_by_day(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    return Timegroup("everyday"), _window_start(t, 86400)


def _group_by_day_of_month(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    mday = time.localtime(t).tm_mday
    return Timegroup(str(mday)), _window_start(t, 86400)


def _group_by_everyhour(t: Timestamp) -> tuple[Timegroup, Timestamp]:
    return Timegroup("everyhour"), _window_start(t, 3600)


PREDICTION_PERIODS: Final = {
    "wday": _PeriodInfo(
        slice=86400,  # 7 slices
        groupby=_group_by_wday,
        valid=7,
    ),
    "day": _PeriodInfo(
        slice=86400,  # 31 slices
        groupby=_group_by_day_of_month,
        valid=28,
    ),
    "hour": _PeriodInfo(
        slice=86400,  # 1 slice
        groupby=_group_by_day,
        valid=1,
    ),
    "minute": _PeriodInfo(
        slice=3600,  # 1 slice
        groupby=_group_by_everyhour,
        valid=24,
    ),
}


def _time_slices(
    timestamp: Timestamp,
    horizon: Seconds,
    period_info: _PeriodInfo,
    timegroup: Timegroup,
) -> _TimeSlices:
    "Collect all slices back into the past until time horizon is reached"
    timestamp = int(timestamp)
    abs_begin = timestamp - horizon
    slices = []

    # Note: due to the f**king DST, we can have several shifts between DST
    # and non-DST during a computation. Treatment is unfair on those longer
    # or shorter days. All days have 24hrs. DST swaps within slices are
    # being ignored, we work with slice shifts. The DST flag is checked
    # against the query timestamp. In general that means test is done at
    # the beginning of the day(because predictive levels refresh at
    # midnight) and most likely before DST swap is applied.

    # Have fun understanding the tests for this function.
    for begin in range(timestamp, abs_begin, -period_info.slice):
        tg, start, end = _get_prediction_timegroup(begin, period_info)[:3]
        if tg == timegroup:
            slices.append((start, end))
    return slices


def _get_prediction_timegroup(
    t: Timestamp,
    period_info: _PeriodInfo,
) -> tuple[Timegroup, Timestamp, Timestamp, Seconds]:
    """
    Return:
    timegroup: name of the group, like 'monday' or '12'
    from_time: absolute epoch time of the first second of the
    current slice.
    until_time: absolute epoch time of the first second *not* in the slice
    rel_time: seconds offset of now in the current slice
    """
    # Convert to local timezone
    timegroup, rel_time = period_info.groupby(t)
    from_time = t - rel_time
    until_time = from_time + period_info.slice
    return timegroup, from_time, until_time, rel_time


def _calculate_data_for_prediction(
    time_windows: _TimeSlices,
    rrd_datacolumn: RRDColumnFunction,
) -> PredictionData:
    twindow, slices = _retrieve_grouped_data_from_rrd(rrd_datacolumn, time_windows)

    descriptors = _data_stats(slices)

    return PredictionData(
        columns=["average", "min", "max", "stdev"],
        points=descriptors,
        num_points=len(descriptors),
        data_twindow=list(twindow[:2]),
        step=twindow[2],
    )


def _data_stats(slices: list[TimeSeriesValues]) -> DataStats:
    "Statistically summarize all the upsampled RRD data"

    descriptors: DataStats = []

    for time_column in zip(*slices):
        point_line = [x for x in time_column if x is not None]
        if point_line:
            average = sum(point_line) / float(len(point_line))
            descriptors.append(
                [
                    average,
                    min(point_line),
                    max(point_line),
                    _std_dev(point_line, average),
                ]
            )
        else:
            descriptors.append([None, None, None, None])

    return descriptors


def _std_dev(point_line: list[float], average: float) -> float:
    samples = len(point_line)
    # In the case of a single data-point an unbiased standard deviation is
    # undefined. In this case we take the magnitude of the measured value
    # itself as a measure of the dispersion.
    if samples == 1:
        return abs(average)
    return math.sqrt(
        abs(sum(p**2 for p in point_line) - average**2 * samples) / float(samples - 1)
    )


def _retrieve_grouped_data_from_rrd(
    rrd_column: RRDColumnFunction,
    time_windows: _TimeSlices,
) -> tuple[TimeWindow, list[TimeSeriesValues]]:
    "Collect all time slices and up-sample them to same resolution"
    from_time = time_windows[0][0]

    slices = [(rrd_column(start, end), from_time - start) for start, end in time_windows]

    # The resolutions of the different time ranges differ. We upsample
    # to the best resolution. We assume that the youngest slice has the
    # finest resolution.
    twindow = slices[0][0].twindow
    if twindow[2] == 0:
        raise RuntimeError("Got no historic metrics")

    return twindow, [ts.bfill_upsample(twindow, shift) for ts, shift in slices]
