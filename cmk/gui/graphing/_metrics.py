#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from cmk.utils.metrics import MetricName

from cmk.gui.i18n import _, translate_to_current_language

from ._color import get_gray_tone, get_palette_color_by_index, parse_color_into_hexrgb
from ._formatter import AutoPrecision
from ._from_api import metrics_from_api
from ._legacy import metric_info, MetricInfo, unit_info, UnitInfo
from ._unit import ConvertibleUnitSpecification, DecimalNotation


def _get_legacy_metric_info(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricInfo | None:
    if not (mi := metric_info.get(metric_name)):
        return None
    color_counter.update({"metric": 1})
    return mi


@dataclass(frozen=True)
class MetricSpec:
    name: MetricName
    title: str
    unit_spec: UnitInfo | ConvertibleUnitSpecification
    color: str


def _fallback_metric_spec(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricSpec:
    color_counter.update({"metric": 1})
    return MetricSpec(
        name=metric_name,
        title=metric_name.title(),
        unit_spec=ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=""),
            precision=AutoPrecision(digits=2),
        ),
        color=parse_color_into_hexrgb(get_palette_color_by_index(color_counter["metric"])),
    )


def get_metric_spec_with_color(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricSpec:
    metric_info_prediction = None
    if metric_name.startswith("predict_lower_"):
        if (lookup_metric_name := metric_name[14:]) in metrics_from_api:
            mfa = metrics_from_api[lookup_metric_name]
            return MetricSpec(
                name=metric_name,
                title=(
                    _("Prediction of ")
                    + mfa.title_localizer(translate_to_current_language)
                    + _(" (lower levels)")
                ),
                unit_spec=mfa.unit_spec,
                color=get_gray_tone(color_counter),
            )

        if mi := _get_legacy_metric_info(lookup_metric_name, color_counter):
            metric_info_prediction = MetricInfo(
                title=_("Prediction of ") + mi["title"] + _(" (lower levels)"),
                unit=mi["unit"],
                color=get_gray_tone(color_counter),
            )
        else:
            fallback = _fallback_metric_spec(lookup_metric_name, color_counter)
            return MetricSpec(
                name=fallback.name,
                title=_("Prediction of ") + fallback.title + _(" (lower levels)"),
                unit_spec=fallback.unit_spec,
                color=get_gray_tone(color_counter),
            )

    elif metric_name.startswith("predict_"):
        if (lookup_metric_name := metric_name[8:]) in metrics_from_api:
            mfa = metrics_from_api[lookup_metric_name]
            return MetricSpec(
                name=metric_name,
                title=(
                    _("Prediction of ")
                    + mfa.title_localizer(translate_to_current_language)
                    + _(" (upper levels)")
                ),
                unit_spec=mfa.unit_spec,
                color=get_gray_tone(color_counter),
            )

        if mi := _get_legacy_metric_info(lookup_metric_name, color_counter):
            metric_info_prediction = MetricInfo(
                title=_("Prediction of ") + mi["title"] + _(" (upper levels)"),
                unit=mi["unit"],
                color=get_gray_tone(color_counter),
            )
        else:
            fallback = _fallback_metric_spec(lookup_metric_name, color_counter)
            return MetricSpec(
                name=fallback.name,
                title=_("Prediction of ") + fallback.title + _(" (upper levels)"),
                unit_spec=fallback.unit_spec,
                color=get_gray_tone(color_counter),
            )
    elif metric_name in metrics_from_api:
        mfa = metrics_from_api[metric_name]
        return MetricSpec(
            name=metric_name,
            title=mfa.title_localizer(translate_to_current_language),
            unit_spec=mfa.unit_spec,
            color=mfa.color,
        )

    if mi := (metric_info_prediction or _get_legacy_metric_info(metric_name, color_counter)):
        return MetricSpec(
            name=metric_name,
            title=str(mi["title"]),
            unit_spec=unit_info[mi["unit"]],
            color=parse_color_into_hexrgb(mi["color"]),
        )

    return _fallback_metric_spec(metric_name, color_counter)


def get_metric_spec(metric_name: str) -> MetricSpec:
    return get_metric_spec_with_color(metric_name, Counter())


def registered_metrics() -> Iterator[tuple[str, str]]:
    for metric_id, mie in metrics_from_api.items():
        yield metric_id, mie.title_localizer(translate_to_current_language)
    for metric_id, mi in metric_info.items():
        yield metric_id, str(mi["title"])
