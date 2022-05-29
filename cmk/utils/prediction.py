#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Literal, NewType, Optional, Tuple

import livestatus

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostName, MetricName, Seconds, ServiceName, Timestamp

logger = logging.getLogger("cmk.prediction")

TimeWindow = Tuple[Timestamp, Timestamp, Seconds]
RRDColumnFunction = Callable[[Timestamp, Timestamp], "TimeSeries"]
TimeSeriesValue = Optional[float]
TimeSeriesValues = List[TimeSeriesValue]
ConsolidationFunctionName = str
Timegroup = NewType("Timegroup", str)
EstimatedLevel = Optional[float]
EstimatedLevels = Tuple[EstimatedLevel, EstimatedLevel, EstimatedLevel, EstimatedLevel]
PredictionParameters = Dict[str, Any]  # TODO: improve this type

_DataStatValue = Optional[float]
_DataStat = List[_DataStatValue]
DataStats = List[_DataStat]

_LevelsType = Literal["absolute", "relative", "stdev"]
_LevelsSpec = Tuple[_LevelsType, Tuple[float, float]]


@dataclass(frozen=True)
class PredictionInfo:
    name: Timegroup
    time: int
    range: Tuple[Timestamp, Timestamp]
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
    columns: List[str]
    points: DataStats
    num_points: int
    data_twindow: List[Timestamp]
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


def rrd_timestamps(twindow: TimeWindow) -> List[Timestamp]:
    start, end, step = twindow
    if step == 0:
        return []
    return [t + step for t in range(start, end, step)]


def aggregation_functions(
    series: TimeSeriesValues, aggr: Optional[ConsolidationFunctionName]
) -> TimeSeriesValue:
    """Aggregate data in series list according to aggr

    If series has None values they are dropped before aggregation"""
    if aggr is None:
        aggr = "max"
    aggr = aggr.lower()

    if not series or all(x is None for x in series):
        return None

    cleaned_series = [x for x in series if x is not None]

    if aggr == "average":
        return sum(cleaned_series) / float(len(cleaned_series))
    if aggr == "max":
        return max(cleaned_series)
    if aggr == "min":
        return min(cleaned_series)

    raise ValueError("Invalid Aggregation function %s, only max, min, average allowed" % aggr)


class TimeSeries:
    """Describes the returned time series returned by livestatus

    - Timestamped values are valid for the measurement interval:
        [timestamp-step; timestamp[
      which means they are at the end of the interval.
    - The Series describes the interval [start; end[
    - Start has no associated value to it.

    args:
        data : List
            Includes [start, end, step, *values]
        timewindow: tuple
            describes (start, end, step), in this case data has only values
        **metadata:
            additional information arguments

    """

    def __init__(
        self,
        data: TimeSeriesValues,
        timewindow: Optional[tuple[Timestamp, Timestamp, Seconds]] = None,
        **metadata: str,
    ) -> None:
        if timewindow is None:
            if not data or data[0] is None or data[1] is None or data[2] is None:
                raise ValueError(data)

            timewindow = int(data[0]), int(data[1]), int(data[2])
            data = data[3:]

        assert timewindow is not None
        self.start = int(timewindow[0])
        self.end = int(timewindow[1])
        self.step = int(timewindow[2])
        self.values = data
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
        self, twindow: TimeWindow, cf: ConsolidationFunctionName = "max"
    ) -> TimeSeriesValues:
        """Downsample time series by consolidation function

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        cf : str ('max', 'average', 'min')
             consolidation function imitating RRD methods
        """
        dwsa = []
        i = 0
        co: TimeSeriesValues = []
        start, end, step = twindow
        desired_times = rrd_timestamps(twindow)
        if start != self.start or end != self.end or step != self.step:
            for t, val in self.time_data_pairs():
                if t > desired_times[i]:
                    dwsa.append(aggregation_functions(co, cf))
                    co = []
                    i += 1
                co.append(val)

            diff_len = len(desired_times) - len(dwsa)
            if diff_len > 0:
                dwsa.append(aggregation_functions(co, cf))
                dwsa = dwsa + [None] * (diff_len - 1)

            return dwsa
        return self.values

    def time_data_pairs(self) -> List[Tuple[Timestamp, TimeSeriesValue]]:
        return list(zip(rrd_timestamps(self.twindow), self.values))

    def __repr__(self) -> str:
        return "TimeSeries(%s, timewindow=%s)" % (self.values, self.twindow)

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


def lq_logic(filter_condition: str, values: List[str], join: str) -> str:
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    conditions = "".join("%s %s\n" % (filter_condition, livestatus.lqencode(x)) for x in values)
    connective = "%s: %d\n" % (join, len(values)) if len(values) > 1 else ""
    return conditions + connective


def livestatus_lql(
    host_names: List[HostName],
    columns: List[str],
    service_description: Optional[ServiceName] = None,
) -> str:
    query_filter = "Columns: %s\n" % " ".join(columns)
    query_filter += lq_logic(
        "Filter: host_name =",
        [str(hostname) for hostname in host_names],
        "Or",
    )
    if service_description == "_HOST_" or service_description is None:
        what = "host"
    else:
        what = "service"
        query_filter += lq_logic("Filter: service_description =", [service_description], "Or")
    return "GET %ss\n%s" % (what, query_filter)


def get_rrd_data(
    hostname: HostName,
    service_description: ServiceName,
    varname: MetricName,
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
    rpn = "%s.%s" % (varname, cf.lower())  # "MAX" -> "max"
    point_range = ":".join(
        livestatus.lqencode(str(x)) for x in (fromtime, untiltime, step, max_entries)
    )
    column = "rrddata:m1:%s:%s" % (rpn, point_range)

    lql = livestatus_lql([hostname], [column], service_description) + "OutputFormat: python\n"

    try:
        connection = livestatus.SingleSiteConnection(
            "unix:%s" % cmk.utils.paths.livestatus_unix_socket
        )
        response = connection.query_value(lql)
    except livestatus.MKLivestatusNotFoundError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Cannot get historic metrics via Livestatus: %s" % e)

    if response is None:
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    return TimeSeries(response)


def rrd_datacolum(
    hostname: HostName,
    service_description: ServiceName,
    varname: MetricName,
    cf: ConsolidationFunctionName,
) -> RRDColumnFunction:
    "Partial helper function to get rrd data"

    def time_boundaries(fromtime: Timestamp, untiltime: Timestamp) -> TimeSeries:
        return get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime)

    return time_boundaries


class PredictionStore:
    def __init__(
        self,
        host_name: HostName,
        service_description: ServiceName,
        dsname: MetricName,
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

    def get_info(self, timegroup: Timegroup) -> Optional[PredictionInfo]:
        raw = self._read_file(self._info_file(timegroup))
        return None if raw is None else PredictionInfo.loads(raw, name=timegroup)

    def get_data(self, timegroup: Timegroup) -> Optional[PredictionData]:
        raw = self._read_file(self._data_file(timegroup))
        return None if raw is None else PredictionData.loads(raw)

    def _read_file(self, file_path: Path) -> Optional[str]:
        try:
            with file_path.open() as fh:
                return fh.read()
        except IOError:
            logger.log(VERBOSE, "No previous prediction for group %s available.", file_path.stem)
        except ValueError:
            logger.log(VERBOSE, "Invalid prediction file %s, old format", file_path)
            self.clean_prediction_files(Timegroup(file_path.stem), force=True)
        return None


def estimate_levels(
    *,
    reference_value: Optional[float],
    stdev: Optional[float],
    levels_lower: Optional[_LevelsSpec],
    levels_upper: Optional[_LevelsSpec],
    levels_upper_lower_bound: Optional[Tuple[float, float]],
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
    stdev: Optional[float],
    levels_factor: float,
) -> Tuple[float, float]:

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
    stdev: Optional[float],
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
