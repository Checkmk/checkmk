#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, Self

from cmk.utils.metrics import MetricName

from cmk.gui.config import active_config, Config
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.gui.valuespec import Age, Filesize, Float, Integer, Percentage

import cmk.ccc.debug
from cmk.ccc.plugin_registry import Registry
from cmk.discover_plugins import discover_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes, graphs, metrics, perfometers, translations

from ._formatter import (
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    SIFormatter,
    StandardScientificFormatter,
    TimeFormatter,
)
from ._unit_info import unit_info, UnitInfo


def load_graphing_plugins() -> (
    DiscoveredPlugins[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ]
):
    discovered_plugins: DiscoveredPlugins[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ] = discover_plugins(
        PluginGroup.GRAPHING,
        entry_point_prefixes(),
        raise_errors=cmk.ccc.debug.enabled(),
    )
    for exc in discovered_plugins.errors:
        logger.error(exc)
    return discovered_plugins


class UnitsFromAPI(Registry[UnitInfo]):
    def plugin_name(self, instance: UnitInfo) -> str:
        return instance.id


_units_from_api = UnitsFromAPI()


def _vs_type(
    notation: (
        metrics.DecimalNotation
        | metrics.SINotation
        | metrics.IECNotation
        | metrics.StandardScientificNotation
        | metrics.EngineeringScientificNotation
        | metrics.TimeNotation
    ),
    symbol: str,
    precision_digits: int,
) -> type[Age] | type[Float] | type[Integer] | type[Percentage]:
    if isinstance(notation, metrics.TimeNotation):
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
        metrics.DecimalNotation
        | metrics.SINotation
        | metrics.IECNotation
        | metrics.StandardScientificNotation
        | metrics.EngineeringScientificNotation
        | metrics.TimeNotation
    ),
    symbol: str,
    precision: metrics.AutoPrecision | metrics.StrictPrecision,
    conversion: Callable[[float], float],
) -> UnitInfo:
    formatter: NotationFormatter
    match notation:
        case metrics.DecimalNotation():
            formatter = DecimalFormatter(symbol, precision)
            js_formatter = "DecimalFormatter"
        case metrics.SINotation():
            formatter = SIFormatter(symbol, precision)
            js_formatter = "SIFormatter"
        case metrics.IECNotation():
            formatter = IECFormatter(symbol, precision)
            js_formatter = "IECFormatter"
        case metrics.StandardScientificNotation():
            formatter = StandardScientificFormatter(symbol, precision)
            js_formatter = "StandardScientificFormatter"
        case metrics.EngineeringScientificNotation():
            formatter = EngineeringScientificFormatter(symbol, precision)
            js_formatter = "EngineeringScientificFormatter"
        case metrics.TimeNotation():
            formatter = TimeFormatter(symbol, precision)
            js_formatter = "TimeFormatter"

    match precision:
        case metrics.AutoPrecision():
            precision_title = f"auto precision {precision.digits}"
        case metrics.StrictPrecision():
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


def register_unit(unit: metrics.Unit) -> UnitInfo:
    if (
        unit_id := (
            f"{unit.notation.__class__.__name__}_{unit.notation.symbol}"
            f"_{unit.precision.__class__.__name__}_{unit.precision.digits}"
        )
    ) in _units_from_api:
        return _units_from_api[unit_id]
    return _units_from_api.register(
        _make_unit_info(
            unit_id=unit_id,
            notation=unit.notation,
            symbol=unit.notation.symbol,
            precision=unit.precision,
            conversion=lambda v: v,
        )
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
        metrics.DecimalNotation
        | metrics.SINotation
        | metrics.IECNotation
        | metrics.StandardScientificNotation
        | metrics.EngineeringScientificNotation
        | metrics.TimeNotation
    )
    match notation_name:
        case "DecimalNotation":
            notation = metrics.DecimalNotation(conversion.target_symbol)
        case "SINotation":
            notation = metrics.SINotation(conversion.target_symbol)
        case "IECNotation":
            notation = metrics.IECNotation(conversion.target_symbol)
        case "StandardScientificNotation":
            notation = metrics.StandardScientificNotation(conversion.target_symbol)
        case "EngineeringScientificNotation":
            notation = metrics.EngineeringScientificNotation(conversion.target_symbol)
        case "TimeNotation":
            notation = metrics.TimeNotation()

    precision: metrics.AutoPrecision | metrics.StrictPrecision
    match precision_name:
        case "AutoPrecision":
            precision = metrics.AutoPrecision(int(raw_precision_digits))
        case "StrictPrecision":
            precision = metrics.StrictPrecision(int(raw_precision_digits))

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
class MetricInfoExtended:
    name: MetricName
    title: str | LazyString
    unit: UnitInfo
    color: str


class MetricsFromAPI(Registry[MetricInfoExtended]):
    def plugin_name(self, instance: MetricInfoExtended) -> str:
        return instance.name


metrics_from_api = MetricsFromAPI()


class PerfometersFromAPI(
    Registry[perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked]
):
    def plugin_name(
        self, instance: perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked
    ) -> str:
        return instance.name


perfometers_from_api = PerfometersFromAPI()


class GraphsFromAPI(Registry[graphs.Graph | graphs.Bidirectional]):
    def plugin_name(self, instance: graphs.Graph | graphs.Bidirectional) -> str:
        return instance.name


graphs_from_api = GraphsFromAPI()
