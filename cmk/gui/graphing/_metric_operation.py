#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Annotated, final, Literal

from pydantic import BaseModel, computed_field, PlainValidator, SerializeAsAny

from livestatus import SiteId

from cmk.ccc.plugin_registry import Registry

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.time_series import TimeSeries

from ._timeseries import AugmentedTimeSeries, derive_num_points_twindow, time_series_math
from ._type_defs import GraphConsolidationFunction, Operators, RRDData, RRDDataKey


@dataclass(frozen=True)
class TranslationKey:
    host_name: HostName
    service_name: ServiceName


class MetricOperation(BaseModel, ABC, frozen=True):
    @staticmethod
    @abstractmethod
    def operation_name() -> str: ...

    @abstractmethod
    def keys(self) -> Iterator[TranslationKey | RRDDataKey]: ...

    @abstractmethod
    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]: ...

    def fade_odd_color(self) -> bool:
        return True

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def ident(self) -> str:
        return self.operation_name()


class MetricOperationRegistry(Registry[type[MetricOperation]]):
    def plugin_name(self, instance: type[MetricOperation]) -> str:
        return instance.operation_name()


metric_operation_registry = MetricOperationRegistry()


def parse_metric_operation(raw: object) -> MetricOperation:
    match raw:
        case MetricOperation():
            return raw
        case {"ident": str(ident), **rest}:
            return metric_operation_registry[ident].model_validate(rest)
        case dict():
            raise ValueError("Missing 'ident' key in metric operation")
    raise TypeError(raw)


class MetricOpConstant(MetricOperation, frozen=True):
    value: float

    @staticmethod
    def operation_name() -> Literal["constant"]:
        return "constant"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from ()

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([self.value] * num_points, twindow))]


class MetricOpConstantNA(MetricOperation, frozen=True):
    @staticmethod
    def operation_name() -> Literal["constant_na"]:
        return "constant_na"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from ()

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([None] * num_points, twindow))]


class MetricOpOperator(MetricOperation, frozen=True):
    operator_name: Operators
    operands: Sequence[
        Annotated[SerializeAsAny[MetricOperation], PlainValidator(parse_metric_operation)]
    ] = []

    @staticmethod
    def operation_name() -> Literal["operator"]:
        return "operator"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from (k for o in self.operands for k in o.keys())

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        if result := time_series_math(
            self.operator_name,
            [
                operand_evaluated.data
                for operand_evaluated in chain.from_iterable(
                    operand.compute_time_series(rrd_data) for operand in self.operands
                )
            ],
        ):
            return [AugmentedTimeSeries(data=result)]
        return []


class MetricOpRRDSource(MetricOperation, frozen=True):
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsolidationFunction | None
    scale: float

    @staticmethod
    def operation_name() -> Literal["rrd"]:
        return "rrd"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield RRDDataKey(
            self.site_id,
            self.host_name,
            self.service_name,
            self.metric_name,
            self.consolidation_func_name,
            self.scale,
        )

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        if (
            key := RRDDataKey(
                self.site_id,
                self.host_name,
                self.service_name,
                self.metric_name,
                self.consolidation_func_name,
                self.scale,
            )
        ) in rrd_data:
            return [AugmentedTimeSeries(data=rrd_data[key])]

        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([None] * num_points, twindow))]


MetricOpOperator.model_rebuild()
