#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable, Mapping

from cmk.graphing.v1 import metrics as metrics_v1

from ._from_api import metric_display_attributes
from ._objects import (
    MetricName,
    MetricTranslation,
    PerformanceData,
    RRDMetricData,
    RRDOriginal,
)

# A predictive metric keeps its prefix on the translated name but is matched by the bare name.
_PREDICT_PREFIXES = ("predict_lower_", "predict_")


def _split_predict_prefix(metric_name: str) -> tuple[str, str]:
    for prefix in _PREDICT_PREFIXES:
        if metric_name.startswith(prefix):
            return prefix, metric_name[len(prefix) :]
    return "", metric_name


def _translations_for_command(
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]],
    check_command: str,
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


def translate_performance_data(
    performance_data: PerformanceData,
    translations: Mapping[str, Mapping[MetricName, MetricTranslation]],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
) -> Mapping[MetricName, RRDMetricData]:
    """Translate raw performance data of a single service into RRD metric data.

    Renaming and scaling are applied here: each value (and its scalar bounds) is multiplied by the
    translation scale, and the display attributes are taken from the registered metric definition
    of the renamed metric. Several raw metrics that rename to the same target are merged, keeping
    every contributing original.
    """
    command_translations = _translations_for_command(translations, performance_data.check_command)
    result: dict[MetricName, RRDMetricData] = {}
    for perf_value in performance_data.values:
        prefix, bare_name = _split_predict_prefix(perf_value.metric_name)
        translation = _find_translation(MetricName(bare_name), command_translations)
        name = MetricName(f"{prefix}{translation.name}")
        scale = translation.scale

        def _scaled(value: float | None, scale: float = scale) -> float | None:
            return None if value is None else value * scale

        original = RRDOriginal(metric_name=perf_value.metric_name, scale=scale)
        title, unit, color = metric_display_attributes(name, metrics, localizer)
        # A later raw metric renaming to the same target overrides the values; originals accumulate.
        originals = [*result[name].originals, original] if name in result else [original]
        result[name] = RRDMetricData(
            value=_scaled(perf_value.value),
            originals=originals,
            title=title,
            unit=unit,
            color=color,
            lower_warning=_scaled(perf_value.lower_warning),
            lower_critical=_scaled(perf_value.lower_critical),
            warning=_scaled(perf_value.warning),
            critical=_scaled(perf_value.critical),
            minimum=_scaled(perf_value.minimum),
            maximum=_scaled(perf_value.maximum),
        )
    return result
