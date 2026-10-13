#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Literal

from cmk.graphing_engine import FALLBACK_UNIT, Unit
from cmk.gui.color import (
    get_gray_tone,
    get_palette_color_by_index,
    parse_color_into_hexrgb,
)
from cmk.gui.i18n import _, translate_to_current_language

from ._from_api import RegisteredMetric


@dataclass(frozen=True)
class MetricSpec:
    name: str
    title: str
    unit: Unit
    color: str


def _fallback_metric_spec(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricSpec:
    color_counter.update({"metric": 1})
    return MetricSpec(
        name=metric_name,
        title=metric_name,
        unit=FALLBACK_UNIT,
        color=parse_color_into_hexrgb(get_palette_color_by_index(color_counter["metric"])),
    )


def _get_metric_spec_with_color(
    metric_name: str,
    color_counter: Counter[Literal["metric", "predictive"]],
    registered_metrics: Mapping[str, RegisteredMetric],
) -> MetricSpec:
    if metric_name.startswith("predict_lower_"):
        if (lookup_metric_name := metric_name[14:]) in registered_metrics:
            mfa = registered_metrics[lookup_metric_name]
            return MetricSpec(
                name=metric_name,
                title=(
                    _("Prediction of ")
                    + mfa.title_localizer(translate_to_current_language)
                    + _(" (lower levels)")
                ),
                unit=mfa.unit,
                color=get_gray_tone(color_counter),
            )
        fallback = _fallback_metric_spec(lookup_metric_name, color_counter)
        return MetricSpec(
            name=fallback.name,
            title=_("Prediction of ") + fallback.title + _(" (lower levels)"),
            unit=fallback.unit,
            color=get_gray_tone(color_counter),
        )

    if metric_name.startswith("predict_"):
        if (lookup_metric_name := metric_name[8:]) in registered_metrics:
            mfa = registered_metrics[lookup_metric_name]
            return MetricSpec(
                name=metric_name,
                title=(
                    _("Prediction of ")
                    + mfa.title_localizer(translate_to_current_language)
                    + _(" (upper levels)")
                ),
                unit=mfa.unit,
                color=get_gray_tone(color_counter),
            )
        fallback = _fallback_metric_spec(lookup_metric_name, color_counter)
        return MetricSpec(
            name=fallback.name,
            title=_("Prediction of ") + fallback.title + _(" (upper levels)"),
            unit=fallback.unit,
            color=get_gray_tone(color_counter),
        )

    if metric_name in registered_metrics:
        mfa = registered_metrics[metric_name]
        return MetricSpec(
            name=metric_name,
            title=mfa.title_localizer(translate_to_current_language),
            unit=mfa.unit,
            color=mfa.color,
        )

    return _fallback_metric_spec(metric_name, color_counter)


def get_metric_spec(
    metric_name: str,
    registered_metrics: Mapping[str, RegisteredMetric],
) -> MetricSpec:
    return _get_metric_spec_with_color(metric_name, Counter(), registered_metrics)


def registered_metric_ids_and_titles(
    registered_metrics: Mapping[str, RegisteredMetric],
) -> Iterator[tuple[str, str]]:
    for metric_id, mie in registered_metrics.items():
        yield metric_id, mie.title_localizer(translate_to_current_language)
