#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This script migrates legacy graphing objects from given file paths like
  - metric_info[...] = {...}
  - check_metrics[...] = {...}
  - perfometer_info.append(...)
  - graph_info[...] = {...}

The migrated objects will be printed to stdout. It's recommended to use '--debug' in order to see
whether all objects from a file can be migrated. Header, imports, comments or other objects are not
taken into account.
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import math
import sys
import traceback
import types
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TextIO

from cmk.utils.metrics import MetricName

from cmk.gui.graphing._perfometer import (  # pylint: disable=cmk-module-layer-violation
    _DualPerfometerSpec,
    _LinearPerfometerSpec,
    _StackedPerfometerSpec,
    LogarithmicPerfometerSpec,
    PerfometerSpec,
)
from cmk.gui.graphing._utils import (  # pylint: disable=cmk-module-layer-violation
    AutomaticDict,
    CheckMetricEntry,
    MetricInfo,
    RawGraphTemplate,
)
from cmk.gui.utils.speaklater import LazyString  # pylint: disable=cmk-module-layer-violation

from cmk.graphing.v1 import Color
from cmk.graphing.v1 import graph as graph_api
from cmk.graphing.v1 import Localizable
from cmk.graphing.v1 import metric as metric_api
from cmk.graphing.v1 import perfometer as perfometer_api
from cmk.graphing.v1 import PhysicalUnit, RGB, ScientificUnit
from cmk.graphing.v1 import translation as translation_api
from cmk.graphing.v1 import Unit

_LOGGER = logging.getLogger(__file__)


def _show_exception(e: Exception) -> None:
    _LOGGER.error("".join(traceback.format_exception(e)))


#   .--parser--------------------------------------------------------------.
#   |                                                                      |
#   |                   _ __   __ _ _ __ ___  ___ _ __                     |
#   |                  | '_ \ / _` | '__/ __|/ _ \ '__|                    |
#   |                  | |_) | (_| | |  \__ \  __/ |                       |
#   |                  | .__/ \__,_|_|  |___/\___|_|                       |
#   |                  |_|                                                 |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class Unparseable:
    namespace: Literal["metric", "translation", "perfometer", "graph"]
    name: str


_UNIT_MAP = {
    "": Unit.NUMBER,
    "count": Unit.COUNT,
    "%": Unit.PERCENTAGE,
    "s": Unit.SECOND,
    "1/s": Unit.PER_SECOND,
    "hz": Unit.HERTZ,
    "bytes": Unit.BYTES_IEC,
    "bytes/s": Unit.BYTES_IEC_PER_SECOND,
    "s/s": Unit.SECONDS_PER_SECOND,
    "bits": Unit.BITS_IEC,
    "bits/s": Unit.BITS_IEC_PER_SECOND,
    "bytes/d": Unit.BYTES_IEC_PER_DAY,
    "c": Unit.DEGREE_CELSIUS,
    "a": Unit.AMPERE,
    "v": Unit.VOLT,
    "w": Unit.WATT,
    "va": Unit.VOLT_AMPERE,
    "wh": Unit.ELETRICAL_ENERGY,
    "dbm": Unit.DECIBEL_MILLIWATT,
    "dbmv": Unit.DECIBEL_MILLIVOLT,
    "db": Unit.DECIBEL,
    "ppm": Unit.PARTS_PER_MILLION,
    "%/m": Unit.PERCENTAGE_PER_METER,
    "bar": Unit.BAR,
    "pa": Unit.PASCAL,
    "l/s": Unit.LITER_PER_SECOND,
    "rpm": Unit.REVOLUTIONS_PER_MINUTE,
    "bytes/op": Unit.BYTES_IEC_PER_OPERATION,
    "EUR": Unit.EURO,
    "RCU": Unit.READ_CAPACITY_UNIT,
    "WCU": Unit.WRITE_CAPACITY_UNIT,
}
# The following colors are calculated by minimum distance.
_COLOR_MAP = {
    "11/a": Color.DARK_VIOLET,
    "11/b": Color.ORCHID,
    "12/a": Color.FUCHSIA,
    "12/b": Color.VIOLET,
    "13/a": Color.FUCHSIA,
    "13/b": Color.VIOLET,
    "14/a": Color.ORANGE_RED,
    "14/b": Color.SANDY_BROWN,
    "15/a": Color.DARK_ORANGE,
    "15/b": Color.SANDY_BROWN,
    "16/a": Color.ORANGE,
    "16/b": Color.SANDY_BROWN,
    "21/a": Color.GOLD,
    "21/b": Color.DARK_GOLDENROD,
    "22/a": Color.GOLD,
    "22/b": Color.GOLDENROD,
    "23/a": Color.YELLOW,
    "23/b": Color.GOLDENROD,
    "24/a": Color.YELLOW,
    "24/b": Color.YELLOW_GREEN,
    "25/a": Color.GREEN_YELLOW,
    "25/b": Color.YELLOW_GREEN,
    "26/a": Color.CHARTREUSE,
    "26/b": Color.LAWN_GREEN,
    "31/a": Color.MEDIUM_SPRING_GREEN,
    "31/b": Color.MEDIUM_SPRING_GREEN,
    "32/a": Color.AQUA,
    "32/b": Color.DARK_TURQUOISE,
    "33/a": Color.AQUA,
    "33/b": Color.DARK_TURQUOISE,
    "34/a": Color.DEEP_SKYBLUE,
    "34/b": Color.DARK_TURQUOISE,
    "35/a": Color.DEEP_SKYBLUE,
    "35/b": Color.LIGHT_SEA_GREEN,
    "36/a": Color.DODGER_BLUE,
    "36/b": Color.DODGER_BLUE,
    "41/a": Color.DODGER_BLUE,
    "41/b": Color.CORNFLOWER_BLUE,
    "42/a": Color.BLUE,
    "42/b": Color.CORNFLOWER_BLUE,
    "43/a": Color.BLUE,
    "43/b": Color.MEDIUM_SLATE_BLUE,
    "44/a": Color.BLUE,
    "44/b": Color.MEDIUM_SLATE_BLUE,
    "45/a": Color.BLUE_VIOLET,
    "45/b": Color.MEDIUM_PURPLE,
    "46/a": Color.DARK_VIOLET,
    "46/b": Color.MEDIUM_ORCHID,
    "51/a": Color.GRAY,
    "51/b": Color.GRAY,
    "52/a": Color.SADDLE_BROWN,
    "52/b": Color.DIM_GRAY,
    "53/a": Color.SADDLE_BROWN,
    "53/b": Color.SIENNA,
}


def _parse_legacy_unit(legacy_unit: str) -> Unit | PhysicalUnit:
    if legacy_unit in _UNIT_MAP:
        return _UNIT_MAP[legacy_unit]
    _LOGGER.info("Unit %r not found, use 'PhysicalUnit'", legacy_unit)
    return PhysicalUnit(Localizable(legacy_unit), legacy_unit)


@dataclass(frozen=True)
class _Distance:
    distance: float
    color: Color

    @classmethod
    def from_colors(cls, legacy: RGB, new: Color) -> _Distance:
        return cls(
            math.sqrt(
                pow(legacy.red - new.value.red, 2)
                + pow(legacy.green - new.value.green, 2)
                + pow(legacy.blue - new.value.blue, 2)
            ),
            new,
        )


def _color_from_hexstr(hexstr: str) -> Color:
    rgb = RGB(*(int(hexstr.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)))
    return min(
        (_Distance.from_colors(rgb, color) for color in Color),
        key=lambda d: d.distance,
    ).color


def _parse_legacy_metric_info(name: str, info: MetricInfo) -> metric_api.Metric:
    if (legacy_color := info["color"]) in _COLOR_MAP:
        color = _COLOR_MAP[legacy_color]
    elif legacy_color.startswith("#"):
        color = _color_from_hexstr(legacy_color)
    else:
        raise ValueError(legacy_color)

    return metric_api.Metric(
        name,
        Localizable(str(info["title"])),
        _parse_legacy_unit(info["unit"]),
        color,
    )


def _parse_legacy_metric_infos(
    debug: bool, unparseables: list[Unparseable], metric_info: Mapping[str, MetricInfo]
) -> Iterator[metric_api.Metric]:
    for name, info in metric_info.items():
        try:
            yield _parse_legacy_metric_info(name, info)
        except Exception as e:
            _show_exception(e)
            if debug:
                raise e
            unparseables.append(Unparseable("metric", name))


def _parse_legacy_check_metrics(
    debug: bool,
    unparseables: list[Unparseable],
    check_metrics: Mapping[str, Mapping[MetricName, CheckMetricEntry]],
) -> Iterator[translation_api.Translation]:
    by_translations: dict[
        tuple[
            tuple[
                str,
                translation_api.Renaming
                | translation_api.Scaling
                | translation_api.RenamingAndScaling,
            ],
            ...,
        ],
        list[
            translation_api.PassiveCheck
            | translation_api.ActiveCheck
            | translation_api.HostCheckCommand
            | translation_api.NagiosPlugin
        ],
    ] = {}
    for name, info in check_metrics.items():
        check_command: translation_api.PassiveCheck | translation_api.ActiveCheck | translation_api.HostCheckCommand | translation_api.NagiosPlugin
        if name.startswith("check_mk-"):
            check_command = translation_api.PassiveCheck(name[9:])
        elif name.startswith("check_mk_active-"):
            check_command = translation_api.ActiveCheck(name[16:])
        elif name.startswith("check-mk-"):
            check_command = translation_api.HostCheckCommand(name[9:])
        elif name.startswith("check_"):
            check_command = translation_api.NagiosPlugin(name[6:])
        else:
            unparseables.append(Unparseable("translation", name))
            raise ValueError(name)

        translations_: list[
            tuple[
                str,
                translation_api.Renaming
                | translation_api.Scaling
                | translation_api.RenamingAndScaling,
            ]
        ] = []
        for legacy_name, attrs in info.items():
            match "name" in attrs, "scale" in attrs:
                case True, True:
                    translations_.append(
                        (
                            legacy_name,
                            translation_api.RenamingAndScaling(attrs["name"], attrs["scale"]),
                        )
                    )
                case True, False:
                    translations_.append((legacy_name, translation_api.Renaming(attrs["name"])))
                case False, True:
                    translations_.append((legacy_name, translation_api.Scaling(attrs["scale"])))
                case _:
                    continue

        by_translations.setdefault(tuple(sorted(translations_, key=lambda t: t[0])), []).append(
            check_command
        )

    for sorted_translations, check_commands in by_translations.items():
        name = "_".join([c.name for c in check_commands])
        try:
            yield translation_api.Translation(name, check_commands, dict(sorted_translations))
        except Exception as e:
            _show_exception(e)
            if debug:
                raise e
            unparseables.append(Unparseable("translation", name))


_Operators = Literal["+", "*", "-", "/"]


def _drop_consolidation_func_name(expression: str) -> str:
    if expression.endswith(".max"):
        return expression[:-4]
    if expression.endswith(".min"):
        return expression[:-4]
    if expression.endswith(".average"):
        return expression[:-8]
    return expression


def _parse_scalar_name(
    scalar_name: str, metric_name: str
) -> metric_api.WarningOf | metric_api.CriticalOf | metric_api.MinimumOf | metric_api.MaximumOf:
    match scalar_name:
        case "warn":
            return metric_api.WarningOf(metric_name)
        case "crit":
            return metric_api.CriticalOf(metric_name)
        case "min":
            return metric_api.MinimumOf(metric_name, color=Color.GRAY)
        case "max":
            return metric_api.MaximumOf(metric_name, color=Color.GRAY)
    raise ValueError(scalar_name)


def _make_percent(
    percent_value: (
        str
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
    ),
    metric_name: str,
    explicit_title: str,
    explicit_color: Color,
) -> metric_api.Fraction:
    return metric_api.Fraction(
        Localizable(explicit_title),
        Unit.PERCENTAGE,
        explicit_color,
        dividend=metric_api.Product(
            # Title, unit, color have no impact
            Localizable(""),
            Unit.NUMBER,
            Color.BLACK,
            [
                metric_api.Constant(
                    # Title, unit, color have no impact
                    Localizable(""),
                    Unit.NUMBER,
                    Color.BLACK,
                    100.0,
                ),
                percent_value,
            ],
        ),
        divisor=metric_api.MaximumOf(
            # Color has no impact
            metric_name,
            color=Color.BLACK,
        ),
    )


def _parse_single_expression(
    expression: str, explicit_title: str, explicit_color: Color
) -> (
    str
    | metric_api.Constant
    | metric_api.WarningOf
    | metric_api.CriticalOf
    | metric_api.MinimumOf
    | metric_api.MaximumOf
    | metric_api.Sum
    | metric_api.Product
    | metric_api.Difference
    | metric_api.Fraction
):
    expression = _drop_consolidation_func_name(expression)
    if percent := expression.endswith("(%)"):
        expression = expression[:-3]

    if ":" in expression:
        expression, scalar_name = expression.split(":")
        metric_name = expression
        scalar = _parse_scalar_name(scalar_name, metric_name)
        return (
            _make_percent(scalar, metric_name, explicit_title, explicit_color)
            if percent
            else scalar
        )

    metric_name = expression
    return (
        _make_percent(metric_name, metric_name, explicit_title, explicit_color)
        if percent
        else metric_name
    )


def _resolve_stack(
    stack: Sequence[
        str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
        | _Operators
    ],
    explicit_title: str,
    explicit_unit_name: str,
    explicit_color: Color,
) -> (
    str
    | metric_api.Constant
    | metric_api.WarningOf
    | metric_api.CriticalOf
    | metric_api.MinimumOf
    | metric_api.MaximumOf
    | metric_api.Sum
    | metric_api.Product
    | metric_api.Difference
    | metric_api.Fraction
):
    resolved: list[
        str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
    ] = []
    for element in stack:
        if (isinstance(element, str) and element not in ("+", "*", "-", "/")) or isinstance(
            element,
            (
                metric_api.Constant,
                metric_api.WarningOf,
                metric_api.CriticalOf,
                metric_api.MinimumOf,
                metric_api.MaximumOf,
                metric_api.Sum,
                metric_api.Product,
                metric_api.Difference,
                metric_api.Fraction,
            ),
        ):
            resolved.append(element)
            continue

        right = resolved.pop()
        left = resolved.pop()

        match element:
            case "+":
                resolved.append(
                    metric_api.Sum(
                        Localizable(explicit_title),
                        explicit_color,
                        [left, right],
                    )
                )
            case "*":
                resolved.append(
                    metric_api.Product(
                        Localizable(explicit_title),
                        _parse_legacy_unit(explicit_unit_name),
                        explicit_color,
                        [left, right],
                    )
                )
            case "-":
                resolved.append(
                    metric_api.Difference(
                        Localizable(explicit_title),
                        explicit_color,
                        minuend=left,
                        subtrahend=right,
                    )
                )
            case "/":
                # Handle zero division by always adding a tiny bit to the divisor
                resolved.append(
                    metric_api.Fraction(
                        Localizable(explicit_title),
                        _parse_legacy_unit(explicit_unit_name),
                        explicit_color,
                        dividend=left,
                        divisor=metric_api.Sum(
                            # Title, color have no impact
                            Localizable(""),
                            Color.BLACK,
                            [
                                right,
                                metric_api.Constant(
                                    # Title, unit, color have no impact
                                    Localizable(""),
                                    Unit.NUMBER,
                                    Color.BLACK,
                                    1e-16,
                                ),
                            ],
                        ),
                    )
                )

    return resolved[0]


def _parse_expression(
    expression: str, explicit_title: str
) -> (
    str
    | metric_api.Constant
    | metric_api.WarningOf
    | metric_api.CriticalOf
    | metric_api.MinimumOf
    | metric_api.MaximumOf
    | metric_api.Sum
    | metric_api.Product
    | metric_api.Difference
    | metric_api.Fraction
):
    if "#" in expression:
        expression, explicit_hexstr_color = expression.rsplit("#", 1)
        explicit_color = _color_from_hexstr(f"#{explicit_hexstr_color}")
    else:
        explicit_color = Color.GRAY

    explicit_unit_name = ""
    if "@" in expression:
        expression, explicit_unit_name = expression.rsplit("@", 1)

    stack: list[
        _Operators
        | str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
    ] = []
    for word in expression.split(","):
        match word:
            case "+":
                stack.append("+")
            case "*":
                stack.append("*")
            case "-":
                stack.append("-")
            case "/":
                stack.append("/")
            case "MIN" | "MAX" | "AVERAGE" | "MERGE" | ">" | ">=" | "<" | "<=":
                raise ValueError(word)
            case _:
                stack.append(_parse_single_expression(word, explicit_title, explicit_color))

    return _resolve_stack(stack, explicit_title, explicit_unit_name, explicit_color)


def _raw_metric_names(
    quantity: (
        str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
    ),
) -> Iterator[str]:
    match quantity:
        case str():
            yield quantity
        case metric_api.WarningOf() | metric_api.CriticalOf() | metric_api.MinimumOf() | metric_api.MaximumOf():
            yield quantity.name
        case metric_api.Sum():
            for s in quantity.summands:
                yield from _raw_metric_names(s)
        case metric_api.Product():
            for f in quantity.factors:
                yield from _raw_metric_names(f)
        case metric_api.Difference():
            yield from _raw_metric_names(quantity.minuend)
            yield from _raw_metric_names(quantity.subtrahend)
        case metric_api.Fraction():
            yield from _raw_metric_names(quantity.dividend)
            yield from _raw_metric_names(quantity.divisor)


def _perfometer_name(
    segments: Sequence[
        str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
    ],
) -> str:
    return "_".join([n for s in segments for n in _raw_metric_names(s)])


def _parse_legacy_linear_perfometer(
    legacy_linear_perfometer: _LinearPerfometerSpec,
) -> perfometer_api.Perfometer:
    if "condition" in legacy_linear_perfometer:
        # Note: there are perfometers with 'condition' which exclude each other.
        # We have to migrate them manually.
        raise ValueError("condition")

    if "label" in legacy_linear_perfometer:
        _LOGGER.info("Perfometer field 'label' will not be migrated")

    legacy_total = legacy_linear_perfometer["total"]
    segments = [_parse_expression(s, "") for s in legacy_linear_perfometer["segments"]]
    return perfometer_api.Perfometer(
        _perfometer_name(segments),
        perfometer_api.FocusRange(
            perfometer_api.Closed(0),
            perfometer_api.Closed(
                legacy_total
                if isinstance(legacy_total, (int, float))
                else _parse_expression(legacy_total, "")
            ),
        ),
        segments,
    )


def _compute_85_border(base: int | float, half_value: int | float) -> int:
    return int(pow(base, 3.5) * half_value)


def _parse_legacy_logarithmic_perfometer(
    legacy_logarithmic_perfometer: LogarithmicPerfometerSpec,
) -> perfometer_api.Perfometer:
    segments = [_parse_expression(legacy_logarithmic_perfometer["metric"], "")]
    return perfometer_api.Perfometer(
        _perfometer_name(segments),
        perfometer_api.FocusRange(
            perfometer_api.Closed(0),
            perfometer_api.Open(
                _compute_85_border(
                    legacy_logarithmic_perfometer["exponent"],
                    legacy_logarithmic_perfometer["half_value"],
                )
            ),
        ),
        segments,
    )


def _parse_legacy_dual_perfometer(
    legacy_dual_perfometer: _DualPerfometerSpec,
) -> perfometer_api.Bidirectional:
    legacy_left, legacy_right = legacy_dual_perfometer["perfometers"]

    if legacy_left["type"] == "linear":
        left = _parse_legacy_linear_perfometer(legacy_left)
    elif legacy_left["type"] == "logarithmic":
        left = _parse_legacy_logarithmic_perfometer(legacy_left)
    else:
        raise ValueError(legacy_left)

    if legacy_right["type"] == "linear":
        right = _parse_legacy_linear_perfometer(legacy_right)
    elif legacy_right["type"] == "logarithmic":
        right = _parse_legacy_logarithmic_perfometer(legacy_right)
    else:
        raise ValueError(legacy_right)

    return perfometer_api.Bidirectional(
        f"{left.name}_{right.name}",
        left=left,
        right=right,
    )


def _parse_legacy_stacked_perfometer(
    legacy_stacked_perfometer: _StackedPerfometerSpec,
) -> perfometer_api.Stacked:
    legacy_upper, legacy_lower = legacy_stacked_perfometer["perfometers"]

    if legacy_upper["type"] == "linear":
        upper = _parse_legacy_linear_perfometer(legacy_upper)
    elif legacy_upper["type"] == "logarithmic":
        upper = _parse_legacy_logarithmic_perfometer(legacy_upper)
    else:
        raise ValueError(legacy_upper)

    if legacy_lower["type"] == "linear":
        lower = _parse_legacy_linear_perfometer(legacy_lower)
    elif legacy_lower["type"] == "logarithmic":
        lower = _parse_legacy_logarithmic_perfometer(legacy_lower)
    else:
        raise ValueError(legacy_lower)

    return perfometer_api.Stacked(
        f"{lower.name}_{upper.name}",
        lower=lower,
        upper=upper,
    )


def _parse_legacy_perfometer_infos(
    debug: bool,
    unparseables: list[Unparseable],
    perfometer_info: Sequence[PerfometerSpec],
) -> Iterator[perfometer_api.Perfometer | perfometer_api.Bidirectional | perfometer_api.Stacked]:
    for idx, info in enumerate(perfometer_info):
        try:
            if info["type"] == "linear":
                yield _parse_legacy_linear_perfometer(info)
            elif info["type"] == "logarithmic":
                yield _parse_legacy_logarithmic_perfometer(info)
            elif info["type"] == "dual":
                yield _parse_legacy_dual_perfometer(info)
            elif info["type"] == "stacked":
                yield _parse_legacy_stacked_perfometer(info)
        except Exception as e:
            _show_exception(e)
            if debug:
                raise e
            unparseables.append(Unparseable("perfometer", str(idx)))


def _parse_legacy_metric(
    legacy_metric: tuple[str, str] | tuple[str, str, str]
) -> (
    str
    | metric_api.Constant
    | metric_api.WarningOf
    | metric_api.CriticalOf
    | metric_api.MinimumOf
    | metric_api.MaximumOf
    | metric_api.Sum
    | metric_api.Product
    | metric_api.Difference
    | metric_api.Fraction
):
    expression, _line_type, *rest = legacy_metric
    return _parse_expression(expression, str(rest[0]) if rest else "")


def _parse_legacy_metrics(
    legacy_metrics: Sequence,
) -> tuple[Sequence, Sequence, Sequence, Sequence]:
    lower_compound_lines = []
    lower_simple_lines = []
    upper_compound_lines = []
    upper_simple_lines = []
    for legacy_metric in legacy_metrics:
        match legacy_metric[1]:
            case "-line":
                lower_simple_lines.append(_parse_legacy_metric(legacy_metric))
            case "-area":
                lower_compound_lines.append(_parse_legacy_metric(legacy_metric))
            case "-stack":
                lower_compound_lines.append(_parse_legacy_metric(legacy_metric))
            case "line":
                upper_simple_lines.append(_parse_legacy_metric(legacy_metric))
            case "area":
                upper_compound_lines.append(_parse_legacy_metric(legacy_metric))
            case "stack":
                upper_compound_lines.append(_parse_legacy_metric(legacy_metric))
            case _:
                raise ValueError(legacy_metric)

    return lower_compound_lines, lower_simple_lines, upper_compound_lines, upper_simple_lines


def _parse_legacy_scalars(
    legacy_scalars: Sequence[str | tuple[str, str | LazyString]]
) -> Sequence[
    str | metric_api.WarningOf | metric_api.CriticalOf | metric_api.MinimumOf | metric_api.MaximumOf
]:
    quantities: list[
        str
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
    ] = []
    for legacy_scalar in legacy_scalars:
        if isinstance(legacy_scalar, str):
            quantity = _parse_expression(legacy_scalar, "")
        elif isinstance(legacy_scalar, tuple):
            quantity = _parse_expression(legacy_scalar[0], str(legacy_scalar[1]))
        else:
            raise ValueError(legacy_scalar)

        # There are scalars which are calculated via RPN. We have to migrate them manually.
        if isinstance(
            quantity,
            (
                str,
                metric_api.WarningOf,
                metric_api.CriticalOf,
                metric_api.MinimumOf,
                metric_api.MaximumOf,
            ),
        ):
            quantities.append(quantity)
        else:
            raise ValueError(quantity)

    return quantities


def _parse_legacy_range(
    legacy_range: tuple[str | int | float, str | int | float] | None
) -> graph_api.MinimalRange | None:
    if legacy_range is None:
        return None

    legacy_lower, legacy_upper = legacy_range
    return graph_api.MinimalRange(
        lower=(
            legacy_lower
            if isinstance(legacy_lower, (int | float))
            else _parse_expression(legacy_lower, "")
        ),
        upper=(
            legacy_upper
            if isinstance(legacy_upper, (int | float))
            else _parse_expression(legacy_upper, "")
        ),
    )


def _parse_legacy_graph_info(
    name: str, info: RawGraphTemplate
) -> tuple[graph_api.Graph | None, graph_api.Graph | None]:
    quantities = _parse_legacy_scalars(info.get("scalars", []))

    (
        lower_compound_lines,
        lower_simple_lines,
        upper_compound_lines,
        upper_simple_lines,
    ) = _parse_legacy_metrics(info["metrics"])

    lower: graph_api.Graph | None = None
    if lower_compound_lines or lower_simple_lines:
        lower = graph_api.Graph(
            name,
            Localizable(str(info["title"])),
            minimal_range=_parse_legacy_range(info.get("range")),
            compound_lines=lower_compound_lines,
            simple_lines=lower_simple_lines,
            optional=info.get("optional_metrics", []),
            conflicting=info.get("conflicting_metrics", []),
        )

    upper: graph_api.Graph | None = None
    if upper_compound_lines or upper_simple_lines:
        upper = graph_api.Graph(
            name,
            Localizable(str(info["title"])),
            minimal_range=_parse_legacy_range(info.get("range")),
            compound_lines=upper_compound_lines,
            simple_lines=list(upper_simple_lines) + list(quantities),
            optional=info.get("optional_metrics", []),
            conflicting=info.get("conflicting_metrics", []),
        )

    return lower, upper


def _parse_legacy_graph_infos(
    debug: bool,
    unparseables: list[Unparseable],
    graph_info: AutomaticDict,
) -> Iterator[graph_api.Graph | graph_api.Bidirectional]:
    for name, info in graph_info.items():
        try:
            lower, upper = _parse_legacy_graph_info(name, info)
        except Exception as e:
            _show_exception(e)
            if debug:
                raise e
            unparseables.append(Unparseable("graph", name))
            continue

        if lower is not None and upper is not None:
            yield graph_api.Bidirectional(
                f"{lower.name}_{upper.name}",
                Localizable(str(info["title"])),
                lower=lower,
                upper=upper,
            )
        elif lower is not None and upper is None:
            yield lower
        elif lower is None and upper is not None:
            yield upper


# .
#   .--repr----------------------------------------------------------------.
#   |                                                                      |
#   |                         _ __ ___ _ __  _ __                          |
#   |                        | '__/ _ \ '_ \| '__|                         |
#   |                        | | |  __/ |_) | |                            |
#   |                        |_|  \___| .__/|_|                            |
#   |                                 |_|                                  |
#   '----------------------------------------------------------------------'


def _list_repr(l: Sequence[str]) -> str:
    trailing_comma = "," if len(l) > 1 else ""
    return f"[{', '.join(l)}{trailing_comma}]"


def _kwarg_repr(k: str, v: str) -> str:
    return f"{k}={v}"


def _dict_repr(d: Mapping[str, str]) -> str:
    d_ = [f"{k}: {v}" for k, v in d.items()]
    trailing_comma = "," if len(d) > 1 else ""
    return f"{{{', '.join(d_)}{trailing_comma}}}"


def _name_repr(name: str) -> str:
    return f"{name!r}"


def _title_repr(title: Localizable) -> str:
    return f'Localizable("{str(title.localize(lambda v: v))}")'


def _unit_repr(unit: Unit | PhysicalUnit | ScientificUnit) -> str:
    match unit:
        case Unit():
            return f"Unit.{unit.name}"
        case PhysicalUnit():
            return f"PhysicalUnit({_title_repr(unit.title)}, {_name_repr(unit.symbol)})"
        case ScientificUnit():
            return f"ScientificUnit({_title_repr(unit.title)}, {_name_repr(unit.symbol)})"


def _color_repr(color: Color) -> str:
    return f"Color.{color.name}"


def _inst_repr(
    namespace: Literal["metric", "translation", "perfometer", "graph"],
    inst: object,
    args: Sequence[str],
) -> str:
    trailing_comma = "," if len(args) > 1 else ""
    return f"{namespace}.{inst.__class__.__name__}({', '.join(args)}{trailing_comma})"


def metric_repr(metric: metric_api.Metric) -> str:
    return _inst_repr(
        "metric",
        metric,
        [
            _name_repr(metric.name),
            _title_repr(metric.title),
            _unit_repr(metric.unit),
            _color_repr(metric.color),
        ],
    )


def _quantity_repr(
    quantity: (
        str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
    ),
) -> str:
    match quantity:
        case str():
            return _name_repr(quantity)
        case metric_api.Constant():
            args = [
                _title_repr(quantity.title),
                _unit_repr(quantity.unit),
                _color_repr(quantity.color),
                str(quantity.value),
            ]
        case metric_api.WarningOf():
            args = [
                _name_repr(quantity.name),
            ]
        case metric_api.CriticalOf():
            args = [
                _name_repr(quantity.name),
            ]
        case metric_api.MinimumOf():
            args = [
                _name_repr(quantity.name),
                _color_repr(quantity.color),
            ]
        case metric_api.MaximumOf():
            args = [
                _name_repr(quantity.name),
                _color_repr(quantity.color),
            ]
        case metric_api.Sum():
            args = [
                _title_repr(quantity.title),
                _color_repr(quantity.color),
                _list_repr([_quantity_repr(f) for f in quantity.summands]),
            ]
        case metric_api.Product():
            args = [
                _title_repr(quantity.title),
                _unit_repr(quantity.unit),
                _color_repr(quantity.color),
                _list_repr([_quantity_repr(f) for f in quantity.factors]),
            ]
        case metric_api.Difference():
            args = [
                _title_repr(quantity.title),
                _color_repr(quantity.color),
                _kwarg_repr("minuend", _quantity_repr(quantity.minuend)),
                _kwarg_repr("subtrahend", _quantity_repr(quantity.subtrahend)),
            ]
        case metric_api.Fraction():
            args = [
                _title_repr(quantity.title),
                _unit_repr(quantity.unit),
                _color_repr(quantity.color),
                _kwarg_repr("dividend", _quantity_repr(quantity.dividend)),
                _kwarg_repr("divisor", _quantity_repr(quantity.divisor)),
            ]
    return _inst_repr("metric", quantity, args)


def _check_command_repr(
    check_command: translation_api.PassiveCheck
    | translation_api.ActiveCheck
    | translation_api.HostCheckCommand
    | translation_api.NagiosPlugin,
) -> str:
    return _inst_repr(
        "translation",
        check_command,
        [
            _name_repr(check_command.name),
        ],
    )


def _translation_ty_repr(
    translation_ty: translation_api.Renaming
    | translation_api.Scaling
    | translation_api.RenamingAndScaling,
) -> str:
    match translation_ty:
        case translation_api.Renaming():
            args = [_name_repr(translation_ty.rename_to)]
        case translation_api.Scaling():
            args = [str(translation_ty.scale_by)]
        case translation_api.RenamingAndScaling():
            args = [
                _name_repr(translation_ty.rename_to),
                str(translation_ty.scale_by),
            ]
    return _inst_repr("translation", translation_ty, args)


def translation_repr(translation: translation_api.Translation) -> str:
    return _inst_repr(
        "translation",
        translation,
        [
            _name_repr(translation.name),
            _list_repr([_check_command_repr(c) for c in translation.check_commands]),
            _dict_repr(
                {
                    _name_repr(n): _translation_ty_repr(t)
                    for n, t in translation.translations.items()
                }
            ),
        ],
    )


def _bound_value_repr(
    bound_value: int
    | float
    | str
    | metric_api.Constant
    | metric_api.WarningOf
    | metric_api.CriticalOf
    | metric_api.MinimumOf
    | metric_api.MaximumOf
    | metric_api.Sum
    | metric_api.Product
    | metric_api.Difference
    | metric_api.Fraction,
) -> str:
    if isinstance(bound_value, (int, float)):
        return str(bound_value)
    return _quantity_repr(bound_value)


def _bound_repr(bound: perfometer_api.Closed | perfometer_api.Open) -> str:
    return _inst_repr(
        "perfometer",
        bound,
        [
            _bound_value_repr(bound.value),
        ],
    )


def _focus_range_repr(focus_range: perfometer_api.FocusRange) -> str:
    return _inst_repr(
        "perfometer",
        focus_range,
        [
            _bound_repr(focus_range.lower),
            _bound_repr(focus_range.upper),
        ],
    )


def _perfometer_repr(perfometer: perfometer_api.Perfometer) -> str:
    return _inst_repr(
        "perfometer",
        perfometer,
        [
            _name_repr(perfometer.name),
            _focus_range_repr(perfometer.focus_range),
            _list_repr([_quantity_repr(s) for s in perfometer.segments]),
        ],
    )


def _p_bidirectional_repr(perfometer: perfometer_api.Bidirectional) -> str:
    return _inst_repr(
        "perfometer",
        perfometer,
        [
            _name_repr(perfometer.name),
            _kwarg_repr("left", _perfometer_repr(perfometer.left)),
            _kwarg_repr("right", _perfometer_repr(perfometer.right)),
        ],
    )


def _p_stacked_repr(perfometer: perfometer_api.Stacked) -> str:
    return _inst_repr(
        "perfometer",
        perfometer,
        [
            _name_repr(perfometer.name),
            _kwarg_repr("lower", _perfometer_repr(perfometer.lower)),
            _kwarg_repr("upper", _perfometer_repr(perfometer.upper)),
        ],
    )


def perfometer_repr(
    perfometer: perfometer_api.Perfometer | perfometer_api.Bidirectional | perfometer_api.Stacked,
) -> str:
    match perfometer:
        case perfometer_api.Perfometer():
            return _perfometer_repr(perfometer)
        case perfometer_api.Bidirectional():
            return _p_bidirectional_repr(perfometer)
        case perfometer_api.Stacked():
            return _p_stacked_repr(perfometer)


def _minimal_range_repr(minimal_range: graph_api.MinimalRange) -> str:
    return _inst_repr(
        "graph",
        minimal_range,
        [
            _bound_value_repr(minimal_range.lower),
            _bound_value_repr(minimal_range.upper),
        ],
    )


def _g_graph_repr(graph: graph_api.Graph) -> str:
    args = [
        _name_repr(graph.name),
        _title_repr(graph.title),
    ]
    if graph.minimal_range:
        args.append(_kwarg_repr("minimal_range", _minimal_range_repr(graph.minimal_range)))
    if graph.compound_lines:
        args.append(
            _kwarg_repr(
                "compound_lines", _list_repr([_quantity_repr(l) for l in graph.compound_lines])
            )
        )
    if graph.simple_lines:
        args.append(
            _kwarg_repr("simple_lines", _list_repr([_quantity_repr(l) for l in graph.simple_lines]))
        )
    if graph.optional:
        args.append(_kwarg_repr("optional", _list_repr([_name_repr(o) for o in graph.optional])))
    if graph.conflicting:
        args.append(
            _kwarg_repr("conflicting", _list_repr([_name_repr(o) for o in graph.conflicting]))
        )
    return _inst_repr("graph", graph, args)


def _g_bidirectional_repr(graph: graph_api.Bidirectional) -> str:
    return _inst_repr(
        "graph",
        graph,
        [
            _name_repr(graph.name),
            _title_repr(graph.title),
            _kwarg_repr("lower", _g_graph_repr(graph.lower)),
            _kwarg_repr("upper", _g_graph_repr(graph.upper)),
        ],
    )


def _graph_repr(graph: graph_api.Graph | graph_api.Bidirectional) -> str:
    match graph:
        case graph_api.Graph():
            return _g_graph_repr(graph)
        case graph_api.Bidirectional():
            return _g_bidirectional_repr(graph)


# .


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Stop at the very first exception",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show information of objects to be migrated",
    )
    parser.add_argument(
        "filepaths",
        nargs="+",
        help="Path to the files where metrics, translations, perfometers or graphs are implemented",
    )
    return parser.parse_args()


def _setup_logger(debug: bool, verbose: bool) -> None:
    handler: logging.StreamHandler[TextIO] | logging.NullHandler
    if debug or verbose:
        handler = logging.StreamHandler()
    else:
        handler = logging.NullHandler()
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)


def _load_module(filepath: Path) -> types.ModuleType:
    if (spec := importlib.util.spec_from_file_location(f"{filepath.name}", filepath)) is None:
        raise TypeError(spec)
    if (mod := importlib.util.module_from_spec(spec)) is None:
        raise TypeError(mod)
    if spec.loader is None:
        raise TypeError(spec.loader)
    spec.loader.exec_module(mod)
    return mod


def _migrate_file_content(
    debug: bool, path: Path, unparseables: list[Unparseable]
) -> Iterator[
    metric_api.Metric
    | translation_api.Translation
    | perfometer_api.Perfometer
    | perfometer_api.Bidirectional
    | perfometer_api.Stacked
    | graph_api.Graph
    | graph_api.Bidirectional,
]:
    module = _load_module(path)

    if hasattr(module, "metric_info"):
        yield from _parse_legacy_metric_infos(debug, unparseables, module.metric_info)

    if hasattr(module, "check_metrics"):
        yield from _parse_legacy_check_metrics(debug, unparseables, module.check_metrics)

    if hasattr(module, "perfometer_info"):
        yield from _parse_legacy_perfometer_infos(debug, unparseables, module.perfometer_info)

    if hasattr(module, "graph_info"):
        yield from _parse_legacy_graph_infos(debug, unparseables, module.graph_info)


def _obj_repr(
    obj: metric_api.Metric
    | translation_api.Translation
    | perfometer_api.Perfometer
    | perfometer_api.Bidirectional
    | perfometer_api.Stacked
    | graph_api.Graph
    | graph_api.Bidirectional,
) -> str:
    def _obj_var_name() -> str:
        return obj.name.replace(".", "_").replace("-", "_")

    match obj:
        case metric_api.Metric():
            return f"metric_{_obj_var_name()} = {metric_repr(obj)}"
        case translation_api.Translation():
            return f"translation_{_obj_var_name()} = {translation_repr(obj)}"
        case perfometer_api.Perfometer() | perfometer_api.Bidirectional() | perfometer_api.Stacked():
            return f"perfometer_{_obj_var_name()} = {perfometer_repr(obj)}"
        case graph_api.Graph() | graph_api.Bidirectional():
            return f"graph_{_obj_var_name()} = {_graph_repr(obj)}"


def _order_unparseables(
    unparseables_by_path: Mapping[Path, Sequence[Unparseable]]
) -> Mapping[Path, Mapping[Literal["metric", "translation", "perfometer", "graph"], set[str]]]:
    ordered: dict[
        Path, dict[Literal["metric", "translation", "perfometer", "graph"], set[str]]
    ] = {}
    for path, unparseables in unparseables_by_path.items():
        for unparseable in unparseables:
            ordered.setdefault(path, {}).setdefault(unparseable.namespace, set()).add(
                unparseable.name
            )
    return ordered


def main() -> None:
    args = _parse_arguments()
    _setup_logger(args.debug, args.verbose)
    unparseables_by_path: dict[Path, list[Unparseable]] = {}
    for raw_path in args.filepaths:
        path = Path(raw_path)
        try:
            objects = list(
                _migrate_file_content(
                    args.debug,
                    path,
                    unparseables_by_path.setdefault(path, []),
                )
            )
        except Exception:
            if args.debug:
                sys.exit(1)

        print("\n\n".join([_obj_repr(obj) for obj in objects]))

    for path, unparseable_names_by_namespace in sorted(
        _order_unparseables(unparseables_by_path).items()
    ):
        _LOGGER.info(
            "%s\n%s",
            path,
            "\n".join(
                [
                    f"  {namespace}: {', '.join(sorted(unparseable_names))}"
                    for namespace, unparseable_names in unparseable_names_by_namespace.items()
                ]
            ),
        )


if __name__ == "__main__":
    main()
