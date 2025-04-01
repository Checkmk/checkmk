#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum, unique
from typing import Any, NewType

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import check_levels_predictive
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable

Project = str


@dataclass(frozen=True)
class ResourceKey:
    key: str
    prefix: str = "resource"


@dataclass(frozen=True)
class MetricKey:
    key: str
    prefix: str = "metric"


@dataclass(frozen=True)
class AggregationKey:
    key: str


LabelKey = ResourceKey | MetricKey
Key = LabelKey | AggregationKey


@dataclass(frozen=True)
class GCPLabels:
    _data: Mapping[str, Mapping[str, Mapping[str, str]]]

    def __getitem__(self, key: LabelKey) -> str:
        return self._data[key.prefix]["labels"][key.key]


@dataclass(frozen=True)
class GCPAggregation:
    _data: Mapping[str, str]

    def __getitem__(self, key: AggregationKey) -> str:
        return self._data[key.key]


@dataclass(frozen=True)
class GCPResult:
    _ts: Mapping[str, Any]
    labels: GCPLabels
    aggregation: GCPAggregation

    @classmethod
    def deserialize(cls, data: str) -> "GCPResult":
        parsed = json.loads(data)
        return cls(
            _ts=parsed["ts"],
            labels=GCPLabels(parsed["ts"]),
            aggregation=GCPAggregation(parsed["aggregation"]),
        )

    @property
    def metric_type(self) -> str:
        return self._ts["metric"]["type"]

    @property
    def value_type(self) -> int:
        return self._ts["value_type"]

    @property
    def points(self) -> Sequence[Mapping[str, Any]]:
        return self._ts["points"]


AssetType = NewType("AssetType", str)


@dataclass(frozen=True)
class GCPAsset:
    _asset: Mapping[str, Any]

    @classmethod
    def deserialize(cls, data: str) -> "GCPAsset":
        return cls(_asset=json.loads(data))

    @property
    def resource_data(self) -> Mapping[str, Any]:
        return self._asset["resource"]["data"]

    @property
    def location(self) -> str:
        return self._asset["resource"]["location"]

    @property
    def asset_type(self) -> AssetType:
        return self._asset["asset_type"]


@dataclass(frozen=True)
class SectionItem:
    rows: Sequence[GCPResult]


@dataclass(frozen=True)
class Config:
    services: Sequence[str]

    def is_enabled(self, service: str) -> bool:
        return service in self.services


PiggyBackSection = Sequence[GCPResult]
Item = str
AssetTypeSection = Mapping[Item, GCPAsset]
Section = Mapping[Item, SectionItem]


@dataclass(frozen=True)
class AssetSection:
    config: Config
    _assets: Mapping[AssetType, AssetTypeSection]

    def __getitem__(self, key: AssetType) -> AssetTypeSection:
        return self._assets.get(key, {})

    def get(
        self, key: AssetType, default: AssetTypeSection | None = None
    ) -> AssetTypeSection | None:
        return self._assets.get(key, default)

    def __contains__(self, key: AssetType) -> bool:
        return key in self._assets


def parse_gcp(
    string_table: StringTable, label_key: LabelKey, extract: Callable[[str], str] = lambda x: x
) -> Section:
    rows = [GCPResult.deserialize(row[0]) for row in string_table]
    items = {row.labels[label_key] for row in rows}
    return {
        extract(item): SectionItem([r for r in rows if r.labels[label_key] == item])
        for item in items
    }


def parse_piggyback(string_table: StringTable) -> PiggyBackSection:
    return [GCPResult.deserialize(row[0]) for row in string_table]


@dataclass(frozen=True)
class GCPAlignerMap:
    gcp_aligner: int  # google.cloud.monitoring_v3.types.Aggregation.Aligner value
    percentile: int


PERCENTILE_MAPPING = [
    GCPAlignerMap(gcp_aligner=18, percentile=99),
    GCPAlignerMap(gcp_aligner=19, percentile=95),
    GCPAlignerMap(gcp_aligner=20, percentile=50),
]


@dataclass(frozen=True)
class Filter:
    key: Key
    value: str | int


LEVEL_EXTRACTOR_TYPE = Callable[[Mapping[str, Any], str], tuple[float, float] | None]


@dataclass(frozen=True)
class MetricExtractionSpec:
    @unique
    class DType(IntEnum):
        INT = 2
        FLOAT = 3

    metric_type: str
    scale: float = 1.0
    filter_by: Sequence[Filter] | None = None


@dataclass(frozen=True)
class MetricDisplaySpec:
    label: str
    render_func: Callable


@dataclass(frozen=True)
class MetricParamsSpec:
    level_extractor: LEVEL_EXTRACTOR_TYPE


@dataclass(frozen=True)
class MetricSpec:
    extraction: MetricExtractionSpec
    display: MetricDisplaySpec
    params: MetricParamsSpec | None = None


def validate_asset_section(section_gcp_assets: AssetSection | None, service: str) -> AssetSection:
    if section_gcp_assets is None or not section_gcp_assets.config.is_enabled(service):
        return AssetSection(Config(services=[]), _assets={})
    return section_gcp_assets


def _filter_by_value(result: GCPResult, filter_by: Filter) -> bool:
    filter_match = True
    match filter_by.key:
        case MetricKey() | ResourceKey():
            filter_match = result.labels[filter_by.key] == filter_by.value
        case AggregationKey():
            filter_match = result.aggregation[filter_by.key] == filter_by.value
    return filter_match


def get_value(timeseries: Sequence[GCPResult], spec: MetricExtractionSpec) -> float:
    # GCP does not always deliver all metrics. i.e. api/request_count only contains values if
    # api requests have occurred. To ensure all metrics are displayed in check mk we default to
    # 0 in the absence of data.

    if spec.filter_by is not None:
        filter_by = spec.filter_by

        def filter_func(r: GCPResult) -> bool:
            return r.metric_type == spec.metric_type and all(
                _filter_by_value(r, fil) for fil in filter_by
            )

    else:

        def filter_func(r: GCPResult) -> bool:
            return r.metric_type == spec.metric_type

    results = list(r for r in timeseries if filter_func(r))
    # normally, only one result should be retrieved. The aggregation over several results is
    # currently only needed for getting the total request count over the response classes for
    # Google Cloud Run applications
    ret_val = 0.0
    for result in results:
        proto_value = result.points[0]["value"]
        match result.value_type:
            case MetricExtractionSpec.DType.FLOAT:
                value = float(proto_value["double_value"])
            case MetricExtractionSpec.DType.INT:
                value = float(proto_value["int64_value"])
            case _:
                raise NotImplementedError("unknown dtype")
        ret_val += value * spec.scale
    return ret_val


def get_boolean_value(results: Sequence[GCPResult], spec: MetricExtractionSpec) -> bool | None:
    def filter_func(r: GCPResult) -> bool:
        type_match = r.metric_type == spec.metric_type
        if spec.filter_by is None:
            return type_match
        return type_match and all(_filter_by_value(r, fil) for fil in spec.filter_by)

    ret_vals = [int(r.points[-1]["value"]["int64_value"]) for r in results if filter_func(r)]
    if len(ret_vals) > 1:
        raise RuntimeError(
            f"More than one result found when extracting boolean value for {spec.metric_type} with "
            f"filter {spec.filter_by}. Aggregation of boolean values currently not supported"
        )
    if len(ret_vals) == 0:
        return None
    return bool(ret_vals[0])


def generic_check(
    metrics: Mapping[str, MetricSpec], timeseries: Sequence[GCPResult], params: Mapping[str, Any]
) -> CheckResult:
    for metric_name, metric_spec in metrics.items():
        value = get_value(timeseries, metric_spec.extraction)
        if metric_spec.params:
            levels_upper = metric_spec.params.level_extractor(params, metric_name)
        else:
            levels_upper = params[metric_name]
        if isinstance(levels_upper, dict):
            yield from check_levels_predictive(
                value,
                metric_name=metric_name,
                render_func=metric_spec.display.render_func,
                levels=levels_upper,
                label=metric_spec.display.label,
            )
        else:
            yield from check_levels_v1(
                value,
                metric_name=metric_name,
                render_func=metric_spec.display.render_func,
                levels_upper=levels_upper,
                label=metric_spec.display.label,
            )


def check(
    spec: Mapping[str, MetricSpec],
    item: str,
    params: Mapping[str, Any],
    section: Section | None,
    asset_type: AssetType,
    all_assets: AssetSection | None,
) -> CheckResult:
    if section is None or not item_in_section(item, asset_type, all_assets):
        return
    timeseries = section.get(item, SectionItem(rows=[])).rows
    yield from generic_check(spec, timeseries, params)


def item_in_section(
    item: str,
    asset_type: AssetType,
    all_assets: AssetSection | None,
) -> bool:
    """We have to check the assets for the item. In the normal section a missing item could also indicate no data.
    This happens for example with a function that is not called."""
    return (
        all_assets is not None
        and (assets := all_assets.get(asset_type)) is not None
        and item in assets
    )


class ServiceNamer:
    def __init__(self, service: str) -> None:
        self.service = service

    def __call__(self, name: str) -> str:
        return f"{self.service} - %s - {name}"

    def summary_name(self) -> str:
        return f"{self.service} - summary"


def service_name_factory(gcp_service: str) -> ServiceNamer:
    return ServiceNamer(gcp_service)


def discovery_summary(section: AssetSection, service: str) -> DiscoveryResult:
    if section.config.is_enabled(service):
        yield Service()


def check_summary(asset_type: AssetType, descriptor: str, section: AssetSection) -> CheckResult:
    n = len(section[asset_type]) if asset_type in section else 0
    appendix = "s" if n != 1 else ""
    yield Result(
        state=State.OK,
        summary=f"{n} {descriptor}{appendix}",
        details=f"Found {n} {descriptor.lower() if not descriptor.isupper() else descriptor}{appendix}",
    )


def _cascading_dropdown_level_extractor(
    params: Mapping[str, Any], metric_name: str
) -> tuple[float, float] | None:
    base_metric_name = "_".join(metric_name.split("_")[:-1])
    (param, levels) = params[base_metric_name]
    if f"{base_metric_name}_{param}" == metric_name:
        return levels
    return None


def _dummy_percentile_level_extractor(params: Mapping[str, Any], metric_name: str) -> None:
    return None


def get_percentile_metric_specs(
    gcp_metric: str,
    check_metric_prefix: str,
    label_prefix: str,
    render_func: Callable,
    scale: float = 1.0,
    additional_filter_by: Sequence[Filter] | None = None,
    parametrized: bool = True,
) -> Mapping[str, MetricSpec]:
    level_extractor = (
        _cascading_dropdown_level_extractor if parametrized else _dummy_percentile_level_extractor
    )

    def _get_spec(gcp_aligner_map: GCPAlignerMap) -> MetricSpec:
        filters = [
            Filter(key=AggregationKey(key="per_series_aligner"), value=gcp_aligner_map.gcp_aligner)
        ]
        if additional_filter_by:
            filters.extend(additional_filter_by)

        return MetricSpec(
            extraction=MetricExtractionSpec(metric_type=gcp_metric, scale=scale, filter_by=filters),
            display=MetricDisplaySpec(
                label=f"{label_prefix} ({gcp_aligner_map.percentile}th percentile)",
                render_func=render_func,
            ),
            params=MetricParamsSpec(level_extractor=level_extractor),
        )

    return {
        f"{check_metric_prefix}_{gcp_aligner_map.percentile}": _get_spec(gcp_aligner_map)
        for gcp_aligner_map in PERCENTILE_MAPPING
    }
