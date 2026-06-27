#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping
from dataclasses import replace

from ._objects import (
    MetricName,
    MetricTranslation,
    PerformanceData,
    RRDMetricData,
    RRDOriginal,
)

_PREDICT_PREFIXES = ("predict_lower_", "predict_")


def _split_predict_prefix(metric_name: str) -> tuple[str, str]:
    for prefix in _PREDICT_PREFIXES:
        if metric_name.startswith(prefix):
            return prefix, metric_name[len(prefix) :]
    return "", metric_name


def _translations_for_command(
    check_command: str,
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]],
) -> Mapping[MetricName, MetricTranslation]:
    if not check_command:
        return {}
    if check_command in translations:
        return translations[check_command]
    if check_command.startswith("check_mk-mgmt_"):
        return translations.get(check_command.replace("check_mk-mgmt_", "check_mk-", 1), {})
    return {}


def _find_translation(
    metric_name: MetricName,
    translations: Mapping[MetricName, MetricTranslation],
) -> MetricTranslation:
    if (translation := translations.get(metric_name)) is not None:
        return translation
    for pattern, translation in translations.items():
        if pattern.startswith("~") and re.compile(pattern[1:]).match(metric_name):
            return translation
    return MetricTranslation(name=metric_name)


def _reverse_translations(
    canonical_name: MetricName,
    translations: Mapping[MetricName, MetricTranslation],
) -> Mapping[MetricName, float]:
    # The old RRD column names that rename to `canonical_name`, each with its scale. After a metric is
    # renamed (RenameTo), its historic data still lives under the former column name, so fetching these
    # too lets a graph spanning the rename keep its pre-rename segment. Regex (`~`) patterns map many
    # names onto one and cannot be inverted, so they are skipped (the same 1-to-1 restriction as legacy).
    return {
        old_name: translation.scale
        for old_name, translation in translations.items()
        if not old_name.startswith("~") and translation.name == canonical_name
    }


def translate_performance_data(
    performance_data: PerformanceData,
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]],
) -> Mapping[MetricName, RRDMetricData]:
    command_translations = _translations_for_command(performance_data.check_command, translations)
    result: dict[MetricName, RRDMetricData] = {}
    for perf_value in performance_data.values:
        prefix, bare_name = _split_predict_prefix(perf_value.metric_name)
        translation = _find_translation(MetricName(bare_name), command_translations)
        name = MetricName(f"{prefix}{translation.name}")
        scale = translation.scale

        def _scaled(value: float | None, scale: float = scale) -> float | None:
            return None if value is None else value * scale

        original = RRDOriginal(metric_name=perf_value.metric_name, scale=scale)
        originals = [*result[name].originals, original] if name in result else [original]
        result[name] = RRDMetricData(
            value=_scaled(perf_value.value),
            originals=originals,
            lower_warning=_scaled(perf_value.lower_warning),
            lower_critical=_scaled(perf_value.lower_critical),
            warning=_scaled(perf_value.warning),
            critical=_scaled(perf_value.critical),
            minimum=_scaled(perf_value.minimum),
            maximum=_scaled(perf_value.maximum),
        )

    # Append the deprecated (pre-rename) column names as further originals so the historic segment is
    # fetched and merged in. The current name's originals stay first, so live data wins on overlap.
    for name, data in list(result.items()):
        prefix, bare_name = _split_predict_prefix(name)
        present = {original.metric_name for original in data.originals}
        deprecated = [
            RRDOriginal(metric_name=old_column, scale=scale)
            for old_name, scale in _reverse_translations(
                MetricName(bare_name), command_translations
            ).items()
            if (old_column := MetricName(f"{prefix}{old_name}")) not in present
        ]
        if deprecated:
            result[name] = replace(data, originals=[*data.originals, *deprecated])
    return result
