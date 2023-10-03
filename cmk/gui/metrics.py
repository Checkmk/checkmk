#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Frequently used variable names:
# perf_data_string:   Raw performance data as sent by the core, e.g "foo=17M;1;2;4;5"
# perf_data:          Split performance data, e.g. [("foo", "17", "M", "1", "2", "4", "5")]
# translated_metrics: Completely parsed and translated into metrics, e.g. { "foo" : { "value" : 17.0, "unit" : { "render" : ... }, ... } }
# color:              RGB color representation ala HTML, e.g. "#ffbbc3" or "#FFBBC3", len() is always 7!
# color_rgb:          RGB color split into triple (r, g, b), where r,b,g in (0.0 .. 1.0)
# unit_name:          The ID of a unit, e.g. "%"
# unit:               The definition-dict of a unit like in unit_info
# graph_template:     Template for a graph. Essentially a dict with the key "metrics"

import abc
import json
import math
from collections.abc import Callable, Sequence
from typing import Any

import cmk.utils
import cmk.utils.plugin_registry
import cmk.utils.render
from cmk.utils.exceptions import MKGeneralException

import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.graphing import _color as graphing_color
from cmk.gui.graphing import _unit_info as graphing_unit_info
from cmk.gui.graphing import _utils as graphing_utils
from cmk.gui.graphing import (
    DualPerfometerSpec,
    LegacyPerfometer,
    LinearPerfometerSpec,
    LogarithmicPerfometerSpec,
    perfometer_info,
    PerfometerSpec,
    StackedPerfometerSpec,
)
from cmk.gui.graphing._expression import parse_expression
from cmk.gui.graphing._graph_specification import GraphMetric, parse_raw_graph_specification
from cmk.gui.graphing._html_render import (
    host_service_graph_dashlet_cmk,
    host_service_graph_popup_cmk,
)
from cmk.gui.graphing._unit_info import unit_info
from cmk.gui.graphing._utils import CombinedSingleMetricSpec, parse_perf_data, translate_metrics
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import TranslatedMetrics, UnitInfo
from cmk.gui.view_utils import get_themed_perfometer_bg_color

PerfometerExpression = str | int | float
RequiredMetricNames = set[str]

#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |  Typical code for loading Multisite plugins of this module           |
#   '----------------------------------------------------------------------'


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("metrics", globals())

    fixup_perfometer_info()


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.metrics as legacy_api_module
    import cmk.gui.plugins.metrics.utils as legacy_plugin_utils

    for name in (
        "check_metrics",
        "G",
        "GB",
        "graph_info",
        "GraphTemplate",
        "K",
        "KB",
        "m",
        "M",
        "MAX_CORES",
        "MAX_NUMBER_HOPS",
        "MB",
        "metric_info",
        "P",
        "PB",
        "scale_symbols",
        "skype_mobile_devices",
        "T",
        "TB",
        "time_series_expression_registry",
    ):
        legacy_api_module.__dict__[name] = graphing_utils.__dict__[name]
        legacy_plugin_utils.__dict__[name] = graphing_utils.__dict__[name]

    legacy_api_module.__dict__["perfometer_info"] = perfometer_info
    legacy_plugin_utils.__dict__["perfometer_info"] = perfometer_info

    legacy_api_module.__dict__["unit_info"] = graphing_unit_info.__dict__["unit_info"]
    legacy_plugin_utils.__dict__["unit_info"] = graphing_unit_info.__dict__["unit_info"]

    for name in (
        "darken_color",
        "indexed_color",
        "lighten_color",
        "MONITORING_STATUS_COLORS",
        "parse_color",
        "parse_color_into_hexrgb",
        "render_color",
        "scalar_colors",
    ):
        legacy_api_module.__dict__[name] = graphing_color.__dict__[name]
        legacy_plugin_utils.__dict__[name] = graphing_color.__dict__[name]

    # Avoid needed imports, see CMK-12147
    globals().update(
        {
            "indexed_color": graphing_color.indexed_color,
            "metric_info": graphing_utils.metric_info,
            "check_metrics": graphing_utils.check_metrics,
            "graph_info": graphing_utils.graph_info,
        }
    )


def fixup_perfometer_info() -> None:
    _convert_legacy_tuple_perfometers(perfometer_info)


# During implementation of the metric system the perfometers were first defined using
# tuples. This has been replaced with a dict based syntax. This function converts the
# old known formats from tuple to dict.
# All shipped perfometers have been converted to the dict format with 1.5.0i3.
# TODO: Remove this one day.
def _convert_legacy_tuple_perfometers(perfometers: list[LegacyPerfometer | PerfometerSpec]) -> None:
    for index, perfometer in reversed(list(enumerate(perfometers))):
        if isinstance(perfometer, dict):
            continue

        if not isinstance(perfometer, tuple) or len(perfometer) != 2:
            raise MKGeneralException(_("Invalid perfometer declaration: %r") % perfometer)

        # Convert legacy tuple based perfometer
        perfometer_type, perfometer_args = perfometer[0], perfometer[1]
        if perfometer_type == "dual":
            sub_performeters = perfometer_args[:]
            _convert_legacy_tuple_perfometers(sub_performeters)
            perfometers[index] = {
                "type": "dual",
                "perfometers": sub_performeters,
            }

        elif perfometer_type == "stacked":
            sub_performeters = perfometer_args[:]
            _convert_legacy_tuple_perfometers(sub_performeters)
            perfometers[index] = {
                "type": "stacked",
                "perfometers": sub_performeters,
            }

        elif perfometer_type == "linear" and len(perfometer_args) == 3:
            required, total, label = perfometer_args
            perfometers[index] = {
                "type": "linear",
                "segments": required,
                "total": total,
                "label": label,
            }

        else:
            logger.warning(
                _("Could not convert perfometer to dict format: %r. Ignoring this one."), perfometer
            )
            perfometers.pop(index)


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'
# A few helper function to be used by the definitions


def metric_to_text(metric: dict[str, Any], value: int | float | None = None) -> str:
    if value is None:
        value = metric["value"]
    return metric["unit"]["render"](value)


# aliases to be compatible to old plugins
physical_precision = cmk.utils.render.physical_precision
age_human_readable = cmk.utils.render.approx_age

# .
#   .--Evaluation----------------------------------------------------------.
#   |          _____            _             _   _                        |
#   |         | ____|_   ____ _| |_   _  __ _| |_(_) ___  _ __             |
#   |         |  _| \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \            |
#   |         | |___ \ V / (_| | | |_| | (_| | |_| | (_) | | | |           |
#   |         |_____| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Parsing of performance data into metrics, evaluation of expressions |
#   '----------------------------------------------------------------------'


def translate_perf_data(
    perf_data_string: str, check_command: str | None = None
) -> TranslatedMetrics:
    perf_data, check_command = parse_perf_data(perf_data_string, check_command)
    return translate_metrics(perf_data, check_command)


# .
#   .--Perf-O-Meters-------------------------------------------------------.
#   |  ____            __        ___        __  __      _                  |
#   | |  _ \ ___ _ __ / _|      / _ \      |  \/  | ___| |_ ___ _ __ ___   |
#   | | |_) / _ \ '__| |_ _____| | | |_____| |\/| |/ _ \ __/ _ \ '__/ __|  |
#   | |  __/  __/ |  |  _|_____| |_| |_____| |  | |  __/ ||  __/ |  \__ \  |
#   | |_|   \___|_|  |_|        \___/      |_|  |_|\___|\__\___|_|  |___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Implementation of Perf-O-Meters                                     |
#   '----------------------------------------------------------------------'


MetricRendererStack = list[list[tuple[int | float, str]]]


class MetricometerRenderer(abc.ABC):
    """Abstract base class for all metricometer renderers"""

    @classmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_stack(self) -> MetricRendererStack:
        """Return a list of perfometer elements

        Each element is represented by a 2 element tuple where the first element is
        the width in px and the second element the hex color code of this element.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_label(self) -> str:
        """Returns the label to be shown on top of the rendered stack

        When the perfometer type definition has a "label" element, this will be used.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_sort_value(self) -> float:
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        raise NotImplementedError()

    @staticmethod
    def _render_value(unit: UnitInfo, value: float) -> str:
        return unit.get("perfometer_render", unit["render"])(value)


class MetricometerRendererRegistry(cmk.utils.plugin_registry.Registry[type[MetricometerRenderer]]):
    def plugin_name(self, instance):
        return instance.type_name()

    def get_renderer(
        self, perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics
    ) -> MetricometerRenderer:
        if perfometer["type"] == "logarithmic":
            return MetricometerRendererLogarithmic(perfometer, translated_metrics)
        if perfometer["type"] == "linear":
            return MetricometerRendererLinear(perfometer, translated_metrics)
        if perfometer["type"] == "dual":
            return MetricometerRendererDual(perfometer, translated_metrics)
        if perfometer["type"] == "stacked":
            return MetricometerRendererStacked(perfometer, translated_metrics)
        raise ValueError(perfometer["type"])


renderer_registry = MetricometerRendererRegistry()


@renderer_registry.register
class MetricometerRendererLogarithmic(MetricometerRenderer):
    def __init__(
        self,
        perfometer: LogarithmicPerfometerSpec,
        translated_metrics: TranslatedMetrics,
    ) -> None:
        if "metric" not in perfometer:
            raise MKGeneralException(
                _('Missing key "metric" in logarithmic perfometer: %r') % perfometer
            )

        self._metric = parse_expression(perfometer["metric"], translated_metrics)
        self._half_value = perfometer["half_value"]
        self._exponent = perfometer["exponent"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "logarithmic"

    def get_stack(self) -> MetricRendererStack:
        result = self._metric.evaluate(self._translated_metrics)
        return [
            self.get_stack_from_values(
                result.value,
                *self.estimate_parameters_for_converted_units(
                    result.unit_info.get(
                        "conversion",
                        lambda v: v,
                    )
                ),
                result.color,
            )
        ]

    def get_label(self) -> str:
        result = self._metric.evaluate(self._translated_metrics)
        return self._render_value(result.unit_info, result.value)

    def get_sort_value(self) -> float:
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        return self._metric.evaluate(self._translated_metrics).value

    @staticmethod
    def get_stack_from_values(
        value: str | int | float,
        half_value: int | float,
        base: int | float,
        color: str,
    ) -> list[tuple[int | float, str]]:
        """
        half_value: if value == half_value, the perfometer is filled by 50%
        base: if we multiply value by base, the perfometer is filled by another 10%, unless we hit
        the min/max cutoffs
        """
        # Negative values are printed like positive ones (e.g. time offset)
        value = abs(float(value))
        if value == 0.0:
            pos = 0.0
        else:
            half_value = float(half_value)
            h = math.log(half_value, base)  # value to be displayed at 50%
            pos = 50 + 10.0 * (math.log(value, base) - h)
            pos = min(max(2, pos), 98)

        return [(pos, color), (100 - pos, get_themed_perfometer_bg_color())]

    def estimate_parameters_for_converted_units(
        self, conversion: Callable[[float], float]
    ) -> tuple[float, float]:
        """
        Estimate a new half_value (50%-value) and a new exponent (10%-factor) for converted units.

        Regarding the 50%-value, we can simply apply the conversion. However, regarding the 10%-
        factor, it's certainly wrong to simply directly apply the conversion. For example, doing
        that for the conversion degree celsius -> degree fahrenheit would yield a 10%-factor of 28.5
        for degree fahrenheit (compared to 1.2 for degree celsius).

        Instead, we estimate a new factor as follows:
        h_50: 50%-value for original units
        f_10: 10%-factor for original units
        c: conversion function
        h_50_c = c(h_50): 50%-value for converted units aka. converted 50%-value
        f_10_c: 10%-factor for converted units

        f_10_c = c(h_50 * f_10) / h_50_c
                 --------------
                 converted 60%-value
                 -----------------------
                 ratio of converted 60%- to converted 50%-value
        """
        h_50 = self._half_value
        f_10 = self._exponent
        h_50_c = conversion(self._half_value)
        return (
            h_50_c,
            conversion(h_50 * f_10) / h_50_c,
        )


@renderer_registry.register
class MetricometerRendererLinear(MetricometerRenderer):
    def __init__(
        self,
        perfometer: LinearPerfometerSpec,
        translated_metrics: TranslatedMetrics,
    ) -> None:
        self._perfometer = perfometer
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "linear"

    def get_stack(self) -> MetricRendererStack:
        entry = []

        summed = self._get_summed_values()

        if (
            total := (
                summed
                if (total_expression := self._perfometer.get("total")) is None
                else self._evaluate_total(total_expression)
            )
        ) == 0:
            entry.append((100.0, get_themed_perfometer_bg_color()))

        else:
            for ex in self._perfometer["segments"]:
                result = parse_expression(ex, self._translated_metrics).evaluate(
                    self._translated_metrics
                )
                entry.append((100.0 * result.value / total, result.color))

            # Paint rest only, if it is positive and larger than one promille
            if total - summed > 0.001:
                entry.append((100.0 * (total - summed) / total, get_themed_perfometer_bg_color()))

        return [entry]

    def get_label(self) -> str:
        # "label" option in all Perf-O-Meters overrides automatic label
        if "label" in self._perfometer:
            if self._perfometer["label"] is None:
                return ""

            expr, unit_name = self._perfometer["label"]
            result = parse_expression(expr, self._translated_metrics).evaluate(
                self._translated_metrics
            )
            unit_info_ = unit_info[unit_name] if unit_name else result.unit_info

            if isinstance(expr, int | float):
                value = unit_info_.get("conversion", lambda v: v)(expr)
            else:
                value = result.value

            return self._render_value(unit_info_, value)

        return self._render_value(self._unit(), self._get_summed_values())

    def _evaluate_total(self, total_expression: str | int | float) -> float:
        if isinstance(total_expression, float | int):
            return self._unit().get("conversion", lambda v: v)(total_expression)
        return (
            parse_expression(total_expression, self._translated_metrics)
            .evaluate(self._translated_metrics)
            .value
        )

    def _unit(self) -> UnitInfo:
        # We assume that all expressions across all segments have the same unit
        return (
            parse_expression(self._perfometer["segments"][0], self._translated_metrics)
            .evaluate(self._translated_metrics)
            .unit_info
        )

    def get_sort_value(self) -> float:
        """Use the first segment value for sorting"""
        return (
            parse_expression(self._perfometer["segments"][0], self._translated_metrics)
            .evaluate(self._translated_metrics)
            .value
        )

    def _get_summed_values(self):
        return sum(
            parse_expression(ex, self._translated_metrics).evaluate(self._translated_metrics).value
            for ex in self._perfometer["segments"]
        )


@renderer_registry.register
class MetricometerRendererStacked(MetricometerRenderer):
    def __init__(
        self,
        perfometer: StackedPerfometerSpec,
        translated_metrics: TranslatedMetrics,
    ) -> None:
        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer["perfometers"])
            )
        self._perfometers = perfometer["perfometers"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "stacked"

    def get_stack(self) -> MetricRendererStack:
        stack = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            stack.append(sub_stack[0])

        return stack

    def get_label(self) -> str:
        sub_labels = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_value(self) -> float:
        """Use the number of the first stack element."""
        sub_perfometer = self._perfometers[0]
        renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
        return renderer.get_sort_value()


@renderer_registry.register
class MetricometerRendererDual(MetricometerRenderer):
    def __init__(
        self,
        perfometer: DualPerfometerSpec,
        translated_metrics: TranslatedMetrics,
    ) -> None:
        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer["perfometers"])
            )
        self._perfometers = perfometer["perfometers"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "dual"

    def get_stack(self) -> MetricRendererStack:
        content: list[tuple[int | float, str]] = []
        for nr, sub_perfometer in enumerate(self._perfometers):
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            if len(sub_stack) != 1:
                raise MKInternalError(
                    _("Perf-O-Meter of type 'dual' must only contain plain Perf-O-Meters")
                )

            half_stack = [(int(value / 2.0), color) for (value, color) in sub_stack[0]]
            if nr == 0:
                half_stack.reverse()
            content += half_stack

        return [content]

    def get_label(self) -> str:
        sub_labels = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_value(self) -> float:
        """Sort by max(left, right)

        E.g. for traffic graphs it seems to be useful to
        make it sort by the maximum traffic independent of the direction.
        """
        sub_sort_values = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
            sub_sort_values.append(renderer.get_sort_value())

        return max(*sub_sort_values)


# .
#   .--Hover-Graph---------------------------------------------------------.
#   |     _   _                           ____                 _           |
#   |    | | | | _____   _____ _ __      / ___|_ __ __ _ _ __ | |__        |
#   |    | |_| |/ _ \ \ / / _ \ '__|____| |  _| '__/ _` | '_ \| '_ \       |
#   |    |  _  | (_) \ V /  __/ | |_____| |_| | | | (_| | |_) | | | |      |
#   |    |_| |_|\___/ \_/ \___|_|        \____|_|  \__,_| .__/|_| |_|      |
#   |                                                   |_|                |
#   '----------------------------------------------------------------------'


# This page is called for the popup of the graph icon of hosts/services.
def page_host_service_graph_popup(
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[GraphMetric]
    ],
) -> None:
    """Registered as `host_service_graph_popup`."""
    site_id = request.var("site")
    host_name = request.var("host_name")
    service_description = request.get_str_input("service")
    host_service_graph_popup_cmk(
        site_id,
        host_name,
        service_description,
        resolve_combined_single_metric_spec,
    )


# .
#   .--Graph Dashlet-------------------------------------------------------.
#   |    ____                 _       ____            _     _      _       |
#   |   / ___|_ __ __ _ _ __ | |__   |  _ \  __ _ ___| |__ | | ___| |_     |
#   |  | |  _| '__/ _` | '_ \| '_ \  | | | |/ _` / __| '_ \| |/ _ \ __|    |
#   |  | |_| | | | (_| | |_) | | | | | |_| | (_| \__ \ | | | |  __/ |_     |
#   |   \____|_|  \__,_| .__/|_| |_| |____/ \__,_|___/_| |_|_|\___|\__|    |
#   |                  |_|                                                 |
#   +----------------------------------------------------------------------+
#   |  This page handler is called by graphs embedded in a dashboard.      |
#   '----------------------------------------------------------------------'


def page_graph_dashlet(
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[GraphMetric]
    ],
) -> None:
    """Registered as `graph_dashlet`."""
    spec = request.var("spec")
    if not spec:
        raise MKUserError("spec", _("Missing spec parameter"))
    graph_specification = parse_raw_graph_specification(
        json.loads(request.get_str_input_mandatory("spec"))
    )

    render = request.var("render")
    if not render:
        raise MKUserError("render", _("Missing render parameter"))
    custom_graph_render_options = json.loads(request.get_str_input_mandatory("render"))

    host_service_graph_dashlet_cmk(
        graph_specification,
        custom_graph_render_options,
        resolve_combined_single_metric_spec,
        graph_display_id=request.get_str_input_mandatory("id"),
    )
