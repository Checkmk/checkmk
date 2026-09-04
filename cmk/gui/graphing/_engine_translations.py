#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import MetricName, PerformanceData

from ._engine_perfdata import RawPerformanceData, RawPerformanceValue

_PREDICT_PREFIXES = ("predict_lower_", "predict_")

type _TranslationSpec = (
    translations_v1.RenameTo | translations_v1.ScaleBy | translations_v1.RenameToAndScaleBy
)


@dataclass(frozen=True, kw_only=True)
class RRDOriginal:
    metric_name: MetricName
    scale: float


def _normalize_check_command(
    check_command: (
        translations_v1.PassiveCheck
        | translations_v1.ActiveCheck
        | translations_v1.HostCheckCommand
        | translations_v1.NagiosPlugin
    ),
) -> str:
    match check_command:
        case translations_v1.PassiveCheck():
            name = check_command.name
            return name if name.startswith("check_mk-") else f"check_mk-{name}"
        case translations_v1.ActiveCheck():
            name = check_command.name
            return name if name.startswith("check_mk_active-") else f"check_mk_active-{name}"
        case translations_v1.HostCheckCommand():
            name = check_command.name
            return name if name.startswith("check-mk-") else f"check-mk-{name}"
        case translations_v1.NagiosPlugin():
            name = (
                check_command.name
                if check_command.name.startswith("check_")
                else f"check_{check_command.name}"
            )
            return name.replace(".", "_")
        case _:
            assert_never(check_command)


def _specs_for_command(
    check_command: str,
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[str, _TranslationSpec]:
    if not check_command:
        return {}

    def _matches(candidate: str) -> Mapping[str, _TranslationSpec]:
        merged: dict[str, _TranslationSpec] = {}
        for translation in registered_translations:
            if candidate in (_normalize_check_command(cmd) for cmd in translation.check_commands):
                merged.update(translation.translations)
        return merged

    if direct := _matches(check_command):
        return direct
    if check_command.startswith("check_mk-mgmt_"):
        return _matches(check_command.replace("check_mk-mgmt_", "check_mk-", 1))
    return {}


def _name_and_scale(old_name: MetricName, spec: _TranslationSpec) -> tuple[MetricName, float]:
    match spec:
        case translations_v1.RenameTo():
            return MetricName(spec.metric_name), 1.0
        case translations_v1.ScaleBy():
            return old_name, spec.factor
        case translations_v1.RenameToAndScaleBy():
            return MetricName(spec.metric_name), spec.factor
        case _:
            assert_never(spec)


def _split_predict_prefix(metric_name: str) -> tuple[str, str]:
    for prefix in _PREDICT_PREFIXES:
        if metric_name.startswith(prefix):
            return prefix, metric_name[len(prefix) :]
    return "", metric_name


def _find_name_and_scale(
    metric_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
) -> tuple[MetricName, float]:
    if (spec := specs.get(metric_name)) is not None:
        return _name_and_scale(metric_name, spec)
    for pattern, spec in specs.items():
        if pattern.startswith("~") and re.compile(pattern[1:]).match(metric_name):
            return _name_and_scale(metric_name, spec)
    return metric_name, 1.0


def _reverse_names(
    canonical_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
) -> Mapping[MetricName, float]:
    result: dict[MetricName, float] = {}
    for old_name, spec in specs.items():
        if old_name.startswith("~"):
            continue
        name, scale = _name_and_scale(MetricName(old_name), spec)
        if name == canonical_name:
            result[MetricName(old_name)] = scale
    return result


def reverse_translated_names(
    canonical_name: MetricName,
    registered_translations: Sequence[translations_v1.Translation],
) -> frozenset[MetricName]:
    # Every raw metric name whose data may belong to this metric, across all check commands: the
    # name itself plus every name any translation renames to it. A regex translation ("~.*rta")
    # maps many names onto one and so cannot be reversed.
    return frozenset(
        {canonical_name}
        | {
            name
            for translation in registered_translations
            for name in _reverse_names(canonical_name, translation.translations)
        }
    )


def _deprecated_originals(
    metric_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
    present: Collection[MetricName],
) -> Iterator[RRDOriginal]:
    prefix, bare_name = _split_predict_prefix(metric_name)
    for old_name, scale in _reverse_names(MetricName(bare_name), specs).items():
        if (column := MetricName(f"{prefix}{old_name}")) not in present:
            yield RRDOriginal(metric_name=column, scale=scale)


@dataclass(frozen=True, kw_only=True)
class _TranslatedColumn:
    original: RRDOriginal
    raw_value: RawPerformanceValue


def _translated_columns(
    specs: Mapping[str, _TranslationSpec],
    raw_values: Mapping[MetricName, RawPerformanceValue],
) -> Mapping[MetricName, Sequence[_TranslatedColumn]]:
    columns: dict[MetricName, list[_TranslatedColumn]] = {}
    for original_name, raw_value in raw_values.items():
        prefix, bare_name = _split_predict_prefix(original_name)
        name, scale = _find_name_and_scale(MetricName(bare_name), specs)
        columns.setdefault(MetricName(f"{prefix}{name}"), []).append(
            _TranslatedColumn(
                original=RRDOriginal(metric_name=original_name, scale=scale),
                raw_value=raw_value,
            )
        )
    return columns


def rrd_originals(
    metric_name: MetricName,
    raw_performance_data: RawPerformanceData,
    registered_translations: Sequence[translations_v1.Translation],
) -> Sequence[RRDOriginal]:
    # The columns a metric's performance data was translated from, each with that translation's
    # factor: a translation that only scales thereby reaches the series just like it reaches the
    # values and the thresholds. A metric without performance data falls back to its own column -
    # no translation applies to a column the perf data never carried, so it is unscaled.
    specs = _specs_for_command(raw_performance_data.check_command, registered_translations)
    columns = _translated_columns(specs, raw_performance_data.values).get(metric_name)
    present = (
        [column.original for column in columns]
        if columns
        else [RRDOriginal(metric_name=metric_name, scale=1.0)]
    )
    return [
        *present,
        *_deprecated_originals(metric_name, specs, {original.metric_name for original in present}),
    ]


def map_metric_names(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[MetricName, MetricName]:
    specs = _specs_for_command(check_command, registered_translations)
    mapping: dict[MetricName, MetricName] = {}
    for raw_metric_name in raw_metric_names:
        prefix, bare_name = _split_predict_prefix(raw_metric_name)
        name, _scale = _find_name_and_scale(MetricName(bare_name), specs)
        mapping[raw_metric_name] = MetricName(f"{prefix}{name}")
    return mapping


def translate_metric_names(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    registered_translations: Sequence[translations_v1.Translation],
) -> frozenset[MetricName]:
    return frozenset(
        map_metric_names(check_command, raw_metric_names, registered_translations).values()
    )


def _scaled(value: float | None, scale: float) -> float | None:
    return None if value is None else value * scale


def _performance_data(column: _TranslatedColumn) -> PerformanceData:
    raw_value = column.raw_value
    scale = column.original.scale
    return PerformanceData(
        value=_scaled(raw_value.value, scale),
        lower_warning=_scaled(raw_value.lower_warning, scale),
        lower_critical=_scaled(raw_value.lower_critical, scale),
        warning=_scaled(raw_value.warning, scale),
        critical=_scaled(raw_value.critical, scale),
        minimum=_scaled(raw_value.minimum, scale),
        maximum=_scaled(raw_value.maximum, scale),
    )


def translate_performance_data(
    check_command: str,
    raw_values: Mapping[MetricName, RawPerformanceValue],
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[MetricName, PerformanceData]:
    specs = _specs_for_command(check_command, registered_translations)
    return {
        name: _performance_data(columns[-1])
        for name, columns in _translated_columns(specs, raw_values).items()
    }
