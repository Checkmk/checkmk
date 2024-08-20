#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import assert_never, Protocol, Self

from cmk.gui.config import active_config, Config
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.gui.valuespec import Age, Filesize, Float, Integer, Percentage

from cmk.ccc.plugin_registry import Registry
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api

from ._color import parse_color_from_api
from ._formatter import (
    AutoPrecision,
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    SIFormatter,
    StandardScientificFormatter,
    StrictPrecision,
    TimeFormatter,
)
from ._legacy import unit_info, UnitInfo
from ._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    TimeNotation,
)


class UnitsFromAPI(Registry[UnitInfo]):
    def plugin_name(self, instance: UnitInfo) -> str:
        return instance.id


_units_from_api = UnitsFromAPI()


def _vs_type(
    notation: (
        metrics_api.DecimalNotation
        | metrics_api.SINotation
        | metrics_api.IECNotation
        | metrics_api.StandardScientificNotation
        | metrics_api.EngineeringScientificNotation
        | metrics_api.TimeNotation
    ),
    symbol: str,
    precision_digits: int,
) -> type[Age] | type[Float] | type[Integer] | type[Percentage]:
    if isinstance(notation, metrics_api.TimeNotation):
        return Age
    if symbol.startswith("%"):
        return Percentage
    if precision_digits == 0:
        return Integer
    return Float


def _make_unit_info(
    *,
    unit_id: str,
    notation: (
        metrics_api.DecimalNotation
        | metrics_api.SINotation
        | metrics_api.IECNotation
        | metrics_api.StandardScientificNotation
        | metrics_api.EngineeringScientificNotation
        | metrics_api.TimeNotation
    ),
    symbol: str,
    precision: metrics_api.AutoPrecision | metrics_api.StrictPrecision,
    conversion: Callable[[float], float],
) -> UnitInfo:

    internal_precision: AutoPrecision | StrictPrecision
    match precision:
        case metrics_api.AutoPrecision(digits):
            internal_precision = AutoPrecision(digits=digits)
        case metrics_api.StrictPrecision(digits):
            internal_precision = StrictPrecision(digits=digits)
        case _:
            assert_never(precision)

    formatter: NotationFormatter
    match notation:
        case metrics_api.DecimalNotation():
            formatter = DecimalFormatter(symbol, internal_precision)
            js_formatter = "DecimalFormatter"
        case metrics_api.SINotation():
            formatter = SIFormatter(symbol, internal_precision)
            js_formatter = "SIFormatter"
        case metrics_api.IECNotation():
            formatter = IECFormatter(symbol, internal_precision)
            js_formatter = "IECFormatter"
        case metrics_api.StandardScientificNotation():
            formatter = StandardScientificFormatter(symbol, internal_precision)
            js_formatter = "StandardScientificFormatter"
        case metrics_api.EngineeringScientificNotation():
            formatter = EngineeringScientificFormatter(symbol, internal_precision)
            js_formatter = "EngineeringScientificFormatter"
        case metrics_api.TimeNotation():
            formatter = TimeFormatter(symbol, internal_precision)
            js_formatter = "TimeFormatter"

    match precision:
        case metrics_api.AutoPrecision():
            precision_title = f"auto precision {precision.digits}"
        case metrics_api.StrictPrecision():
            precision_title = f"strict precision {precision.digits}"

    return UnitInfo(
        id=unit_id,
        title=" ".join([symbol or "no symbol", f"({formatter.ident()}, {precision_title})"]),
        symbol=symbol,
        render=formatter.render,
        js_render=f"""v => new cmk.number_format.{js_formatter}(
    "{symbol}",
    new cmk.number_format.{precision.__class__.__name__}({precision.digits}),
).render(v)""",
        conversion=conversion,
        formatter_ident=formatter.ident(),
        valuespec=_vs_type(notation, symbol, precision.digits),
    )


@dataclass(frozen=True)
class _Conversion:
    target_symbol: str
    converter: Callable[[float], float]


class _ConfiguredUnitConverter(Protocol):
    @classmethod
    def attempt(cls, source_symbol: str) -> Self | None: ...

    def get_conversion(self, active_config_: Config, user_: LoggedInUser) -> _Conversion: ...


@dataclass(frozen=True)
class _TemperatureUnitConverter:
    source_unit: TemperatureUnit

    @classmethod
    def attempt(cls, source_symbol: str) -> Self | None:
        match source_symbol:
            case "°C":
                return cls(TemperatureUnit.CELSIUS)
            case "°F":
                return cls(TemperatureUnit.FAHRENHEIT)
            case _:
                return None

    def get_conversion(self, active_config_: Config, user_: LoggedInUser) -> _Conversion:
        match self.source_unit:
            case TemperatureUnit.CELSIUS:
                conversions = {
                    TemperatureUnit.CELSIUS: _Conversion("°C", lambda c: c),
                    TemperatureUnit.FAHRENHEIT: _Conversion("°F", lambda c: c * 1.8 + 32),
                }
            case TemperatureUnit.FAHRENHEIT:
                conversions = {
                    TemperatureUnit.CELSIUS: _Conversion("°C", lambda f: (f - 32) / 1.8),
                    TemperatureUnit.FAHRENHEIT: _Conversion("°F", lambda f: f),
                }
        return conversions[
            TemperatureUnit(
                active_config_.default_temperature_unit
                if (user_setting := user_.get_attribute("temperature_unit")) is None
                else user_setting
            )
        ]


def _construct_unit_info(unit_id: str, conversion: _Conversion) -> UnitInfo:
    notation_name, rest = unit_id.split("_", 1)
    _symbol, precision_name, raw_precision_digits = rest.rsplit("_", 2)

    notation: (
        metrics_api.DecimalNotation
        | metrics_api.SINotation
        | metrics_api.IECNotation
        | metrics_api.StandardScientificNotation
        | metrics_api.EngineeringScientificNotation
        | metrics_api.TimeNotation
    )
    match notation_name:
        case "DecimalNotation":
            notation = metrics_api.DecimalNotation(conversion.target_symbol)
        case "SINotation":
            notation = metrics_api.SINotation(conversion.target_symbol)
        case "IECNotation":
            notation = metrics_api.IECNotation(conversion.target_symbol)
        case "StandardScientificNotation":
            notation = metrics_api.StandardScientificNotation(conversion.target_symbol)
        case "EngineeringScientificNotation":
            notation = metrics_api.EngineeringScientificNotation(conversion.target_symbol)
        case "TimeNotation":
            notation = metrics_api.TimeNotation()

    precision: metrics_api.AutoPrecision | metrics_api.StrictPrecision
    match precision_name:
        case "AutoPrecision":
            precision = metrics_api.AutoPrecision(int(raw_precision_digits))
        case "StrictPrecision":
            precision = metrics_api.StrictPrecision(int(raw_precision_digits))

    return _make_unit_info(
        unit_id=unit_id,
        notation=notation,
        symbol=conversion.target_symbol,
        precision=precision,
        conversion=conversion.converter,
    )


def _compute_unit_info(
    unit_id: str,
    unit_info_: UnitInfo,
    active_config_: Config,
    user_: LoggedInUser,
    converters: Sequence[type[_ConfiguredUnitConverter]],
) -> UnitInfo:
    for converter_cls in converters:
        if (converter := converter_cls.attempt(unit_info_.symbol)) is None:
            continue
        conversion = converter.get_conversion(active_config_, user_)
        if unit_info_.symbol == conversion.target_symbol:
            continue
        return _construct_unit_info(unit_id, conversion)
    return unit_info_


def register_unit_info(unit: metrics_api.Unit) -> UnitInfo:
    unit_id = (
        f"{unit.notation.__class__.__name__}_{unit.notation.symbol}"
        f"_{unit.precision.__class__.__name__}_{unit.precision.digits}"
    )
    return _compute_unit_info(
        unit_id,
        _units_from_api.register(
            _make_unit_info(
                unit_id=unit_id,
                notation=unit.notation,
                symbol=unit.notation.symbol,
                precision=unit.precision,
                conversion=lambda v: v,
            )
        ),
        active_config,
        user,
        [_TemperatureUnitConverter],
    )


def get_unit_info(unit_id: str) -> UnitInfo:
    if unit_id in _units_from_api:
        return _compute_unit_info(
            unit_id,
            _units_from_api[unit_id],
            active_config,
            user,
            [_TemperatureUnitConverter],
        )
    if unit_id in unit_info.keys():
        return unit_info[unit_id]
    return unit_info[""]


@dataclass(frozen=True)
class RegisteredUnit:
    name: str
    symbol: str
    title: str
    description: str
    valuespec: type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage]


def registered_units() -> Sequence[RegisteredUnit]:
    return sorted(
        [
            RegisteredUnit(
                name,
                info.symbol,
                info.title,
                info.description or info.title,
                info.valuespec or Float,
            )
            for (name, info) in unit_info.items()
        ]
        + [
            RegisteredUnit(
                name,
                info.symbol,
                info.title,
                info.description or info.title,
                info.valuespec or Float,
            )
            for (name, info) in _units_from_api.items()
        ],
        key=lambda x: x.title,
    )


@dataclass(frozen=True)
class RegisteredMetric:
    name: str
    title_localizer: Callable[[Callable[[str], str]], str]
    unit_spec: ConvertibleUnitSpecification
    color: str


def parse_metric_from_api(metric_from_api: metrics_api.Metric) -> RegisteredMetric:
    return RegisteredMetric(
        name=metric_from_api.name,
        title_localizer=metric_from_api.title.localize,
        unit_spec=parse_unit_from_api(metric_from_api.unit),
        color=parse_color_from_api(metric_from_api.color),
    )


def parse_unit_from_api(unit_from_api: metrics_api.Unit) -> ConvertibleUnitSpecification:
    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    )
    match unit_from_api.notation:
        case metrics_api.DecimalNotation(symbol):
            notation = DecimalNotation(symbol=symbol)
        case metrics_api.SINotation(symbol):
            notation = SINotation(symbol=symbol)
        case metrics_api.IECNotation(symbol):
            notation = IECNotation(symbol=symbol)
        case metrics_api.StandardScientificNotation(symbol):
            notation = StandardScientificNotation(symbol=symbol)
        case metrics_api.EngineeringScientificNotation(symbol):
            notation = EngineeringScientificNotation(symbol=symbol)
        case metrics_api.TimeNotation():
            notation = TimeNotation(symbol=unit_from_api.notation.symbol)
        case _:
            assert_never(unit_from_api.notation)

    precision: AutoPrecision | StrictPrecision
    match unit_from_api.precision:
        case metrics_api.AutoPrecision(digits):
            precision = AutoPrecision(digits=digits)
        case metrics_api.StrictPrecision(digits):
            precision = StrictPrecision(digits=digits)
        case _:
            assert_never(unit_from_api.precision)

    return ConvertibleUnitSpecification(
        notation=notation,
        precision=precision,
    )


class MetricsFromAPI(Registry[RegisteredMetric]):
    def plugin_name(self, instance: RegisteredMetric) -> str:
        return instance.name


metrics_from_api = MetricsFromAPI()


class PerfometersFromAPI(
    Registry[perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked]
):
    def plugin_name(
        self,
        instance: (
            perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked
        ),
    ) -> str:
        return instance.name


perfometers_from_api = PerfometersFromAPI()


class GraphsFromAPI(Registry[graphs_api.Graph | graphs_api.Bidirectional]):
    def plugin_name(self, instance: graphs_api.Graph | graphs_api.Bidirectional) -> str:
        return instance.name


graphs_from_api = GraphsFromAPI()
