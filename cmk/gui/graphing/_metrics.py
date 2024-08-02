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
from cmk.gui.utils.speaklater import LazyString

from ._color import (
    get_gray_tone,
    get_palette_color_by_index,
    parse_color_from_api,
    parse_color_into_hexrgb,
)
from ._from_api import get_unit_info, metrics_from_api, register_unit
from ._legacy import metric_info, MetricInfo, unit_info, UnitInfo


def _get_legacy_metric_info(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricInfo:
    if metric_name in metric_info:
        return metric_info[metric_name]
    color_counter.update({"metric": 1})
    return MetricInfo(
        title=metric_name.title(),
        unit="",
        color=get_palette_color_by_index(color_counter["metric"]),
    )


@dataclass(frozen=True)
class MetricInfoExtended:
    name: MetricName
    title: str | LazyString
    unit_info: UnitInfo
    color: str


def get_extended_metric_info_with_color(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricInfoExtended:
    if metric_name.startswith("predict_lower_"):
        if (lookup_metric_name := metric_name[14:]) in metrics_from_api:
            mfa = metrics_from_api[lookup_metric_name]
            return MetricInfoExtended(
                name=metric_name,
                title=(
                    _("Prediction of ")
                    + mfa.title.localize(translate_to_current_language)
                    + _(" (lower levels)")
                ),
                unit_info=get_unit_info(register_unit(mfa.unit).id),
                color=get_gray_tone(color_counter),
            )

        mi_ = _get_legacy_metric_info(lookup_metric_name, color_counter)
        mi = MetricInfo(
            title=_("Prediction of ") + mi_["title"] + _(" (lower levels)"),
            unit=mi_["unit"],
            color=get_gray_tone(color_counter),
        )
    elif metric_name.startswith("predict_"):
        if (lookup_metric_name := metric_name[8:]) in metrics_from_api:
            mfa = metrics_from_api[lookup_metric_name]
            return MetricInfoExtended(
                name=metric_name,
                title=(
                    _("Prediction of ")
                    + mfa.title.localize(translate_to_current_language)
                    + _(" (upper levels)")
                ),
                unit_info=get_unit_info(register_unit(mfa.unit).id),
                color=get_gray_tone(color_counter),
            )

        mi_ = _get_legacy_metric_info(lookup_metric_name, color_counter)
        mi = MetricInfo(
            title=_("Prediction of ") + mi_["title"] + _(" (upper levels)"),
            unit=mi_["unit"],
            color=get_gray_tone(color_counter),
        )
    elif metric_name in metrics_from_api:
        mfa = metrics_from_api[metric_name]
        return MetricInfoExtended(
            name=metric_name,
            title=mfa.title.localize(translate_to_current_language),
            unit_info=get_unit_info(register_unit(mfa.unit).id),
            color=parse_color_from_api(mfa.color),
        )
    else:
        mi = _get_legacy_metric_info(metric_name, color_counter)

    return MetricInfoExtended(
        name=metric_name,
        title=mi["title"],
        unit_info=unit_info[mi["unit"]],
        color=parse_color_into_hexrgb(mi["color"]),
    )


def get_extended_metric_info(metric_name: str) -> MetricInfoExtended:
    return get_extended_metric_info_with_color(metric_name, Counter())


def registered_metrics() -> Iterator[tuple[str, str]]:
    for metric_id, mie in metrics_from_api.items():
        yield metric_id, str(mie.title)
    for metric_id, mi in metric_info.items():
        yield metric_id, str(mi["title"])
