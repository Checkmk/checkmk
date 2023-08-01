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
import string
from collections.abc import Callable, Sequence
from typing import Any

import cmk.utils
import cmk.utils.plugin_registry
import cmk.utils.render
from cmk.utils.exceptions import MKGeneralException

import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.graphing import _utils as graphing_utils
from cmk.gui.graphing._graph_specification import MetricExpression, parse_raw_graph_specification
from cmk.gui.graphing._utils import (
    CombinedGraphMetric,
    CombinedSingleMetricSpec,
    evaluate,
    LegacyPerfometer,
    parse_perf_data,
    perfometer_info,
    translate_metrics,
    unit_info,
)
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.metrics.html_render import (
    host_service_graph_dashlet_cmk,
    host_service_graph_popup_cmk,
)
from cmk.gui.type_defs import PerfometerSpec, TranslatedMetrics, UnitInfo
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

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
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
        "darken_color",
        "G",
        "GB",
        "graph_info",
        "GraphTemplate",
        "indexed_color",
        "K",
        "KB",
        "lighten_color",
        "m",
        "M",
        "MAX_CORES",
        "MAX_NUMBER_HOPS",
        "MB",
        "metric_info",
        "MONITORING_STATUS_COLORS",
        "P",
        "parse_color",
        "parse_color_into_hexrgb",
        "PB",
        "perfometer_info",
        "render_color",
        "scalar_colors",
        "scale_symbols",
        "skype_mobile_devices",
        "T",
        "TB",
        "time_series_expression_registry",
        "unit_info",
    ):
        legacy_api_module.__dict__[name] = graphing_utils.__dict__[name]
        legacy_plugin_utils.__dict__[name] = graphing_utils.__dict__[name]

    # Avoid needed imports, see CMK-12147
    globals().update(
        {
            "indexed_color": graphing_utils.indexed_color,
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
        if perfometer_type in ("dual", "stacked"):
            sub_performeters = perfometer_args[:]
            _convert_legacy_tuple_perfometers(sub_performeters)

            perfometers[index] = {
                "type": perfometer_type,
                "perfometers": sub_performeters,
            }

        elif perfometer_type == "linear" and len(perfometer_args) == 3:
            required, total, label = perfometer_args

            perfometers[index] = {
                "type": perfometer_type,
                "segments": required,
                "total": total,
                "label": label,
            }

        else:
            logger.warning(
                _("Could not convert perfometer to dict format: %r. Ignoring this one."), perfometer
            )
            perfometers.pop(index)


def _lookup_required_expressions(
    perfometer: LegacyPerfometer | PerfometerSpec,
) -> list[PerfometerExpression]:
    if not isinstance(perfometer, dict):
        raise MKGeneralException(_("Legacy performeter encountered: %r") % perfometer)

    try:
        return perfometer["_required"]
    except KeyError:
        pass

    # calculate the list of metric expressions of the perfometers
    return perfometer.setdefault("_required", _perfometer_expressions(perfometer))


def _lookup_required_names(
    perfometer: LegacyPerfometer | PerfometerSpec,
) -> RequiredMetricNames | None:
    if not isinstance(perfometer, dict):
        raise MKGeneralException(_("Legacy performeter encountered: %r") % perfometer)

    try:
        return perfometer["_required_names"]
    except KeyError:
        pass

    # calculate the trivial metric names that can later be used to filter
    # perfometers without the need to evaluate the expressions.
    return perfometer.setdefault(
        "_required_names",
        _required_trivial_metric_names(_lookup_required_expressions(perfometer)),
    )


def _perfometer_expressions(perfometer: PerfometerSpec) -> list[PerfometerExpression]:
    """Returns all metric expressions of a perfometer
    This is used for checking which perfometer can be displayed for a given service later.
    """
    required: list[PerfometerExpression] = []

    if perfometer["type"] == "linear":
        required += perfometer["segments"][:]

    elif perfometer["type"] == "logarithmic":
        required.append(perfometer["metric"])

    elif perfometer["type"] in ("stacked", "dual"):
        if "perfometers" not in perfometer:
            raise MKGeneralException(
                _("Perfometers of type 'stacked' and 'dual' need the element 'perfometers' (%r)")
                % perfometer
            )

        for sub_perfometer in perfometer["perfometers"]:
            required += _perfometer_expressions(sub_perfometer)

    else:
        raise NotImplementedError(_("Invalid perfometer type: %s") % perfometer["type"])

    if "label" in perfometer and perfometer["label"] is not None:
        required.append(perfometer["label"][0])
    if "total" in perfometer:
        required.append(perfometer["total"])

    return required


def _required_trivial_metric_names(
    required_expressions: list[PerfometerExpression],
) -> RequiredMetricNames | None:
    """Extract the trivial metric names from a list of expressions.
    Ignores numeric parts. Returns None in case there is a non trivial
    metric found. This means the trivial filtering can not be used.
    """
    required_metric_names = set()

    allowed_chars = string.ascii_letters + string.digits + "_"

    for entry in required_expressions:
        if isinstance(entry, str):
            if any(char not in allowed_chars for char in entry):
                # Found a non trivial metric expression. Totally skip this mechanism
                return None

            required_metric_names.add(entry)

    return required_metric_names


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


class Perfometers:
    def get_first_matching_perfometer(
        self, translated_metrics: TranslatedMetrics
    ) -> PerfometerSpec | None:
        for perfometer in perfometer_info:
            if not isinstance(perfometer, dict):
                continue
            if self._perfometer_possible(perfometer, translated_metrics):
                return perfometer
        return None

    def _perfometer_possible(
        self, perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics
    ) -> bool:
        if not translated_metrics:
            return False

        required_names = _lookup_required_names(perfometer)
        if self._skip_perfometer_by_trivial_metrics(required_names, translated_metrics):
            return False

        for req in _lookup_required_expressions(perfometer):
            try:
                evaluate(req, translated_metrics)
            except Exception:
                return False

        if "condition" in perfometer:
            try:
                value, _color, _unit = evaluate(perfometer["condition"], translated_metrics)
                if value == 0.0:
                    return False
            except Exception:
                return False

        if "total" in perfometer:
            return self._total_values_exists(perfometer["total"], translated_metrics)

        return True

    def _skip_perfometer_by_trivial_metrics(
        self,
        required_metric_names: RequiredMetricNames | None,
        translated_metrics: TranslatedMetrics,
    ) -> bool:
        """Whether or not a perfometer can be skipped by simple metric name matching instead of expression evaluation

        Performance optimization: Try to reduce the amount of perfometers to evaluate by
        comparing the strings in the "required" metrics with the translated metrics.
        We only look at the simple "requried expressions" that don't make use of formulas.
        In case there is a formula, we can not skip the perfometer and have to evaluate
        it.
        """
        if required_metric_names is None:
            return False

        available_metric_names = set(translated_metrics.keys())
        return not required_metric_names.issubset(available_metric_names)

    def _total_values_exists(
        self, value: str | int | float, translated_metrics: TranslatedMetrics
    ) -> bool:
        """
        Only if the value has a suffix like ':min'/':max' we need to check if the value actually exists in the scalar data
        The value could be a percentage value (e.g. '100.0') in this case no need to look here for missing data
        """
        if not isinstance(value, str):
            return True

        if ":" not in value:
            return True

        perf_name, perf_param = value.split(":", 1)
        if perf_param not in translated_metrics[perf_name]["scalar"].keys():
            return False

        return True


MetricRendererStack = list[list[tuple[int | float, str]]]


class MetricometerRenderer(abc.ABC):
    """Abstract base class for all metricometer renderers"""

    @classmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    def __init__(self, perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics) -> None:
        super().__init__()
        self._perfometer = perfometer
        self._translated_metrics = translated_metrics

    @abc.abstractmethod
    def get_stack(self) -> MetricRendererStack:
        """Return a list of perfometer elements

        Each element is represented by a 2 element tuple where the first element is
        the width in px and the second element the hex color code of this element.
        """
        raise NotImplementedError()

    def get_label(self) -> str:
        """Returns the label to be shown on top of the rendered stack

        When the perfometer type definition has a "label" element, this will be used.
        Otherwise the perfometer type specific label of _get_type_label() will be used.
        """

        # "label" option in all Perf-O-Meters overrides automatic label
        if "label" in self._perfometer:
            if self._perfometer["label"] is None:
                return ""

            expr, unit_name = self._perfometer["label"]
            value, unit, _color = evaluate(expr, self._translated_metrics)
            unit = unit_info[unit_name] if unit_name else unit

            if isinstance(expr, int | float):
                value = unit.get("conversion", lambda v: v)(expr)

            return self._render_value(unit, value)

        return self._get_type_label()

    @abc.abstractmethod
    def _get_type_label(self) -> str:
        """Returns the label for this perfometer type"""
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
        subclass = self[perfometer["type"]]
        return subclass(perfometer, translated_metrics)


renderer_registry = MetricometerRendererRegistry()


@renderer_registry.register
class MetricometerRendererLogarithmic(MetricometerRenderer):
    @classmethod
    def type_name(cls) -> str:
        return "logarithmic"

    def __init__(self, perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics) -> None:
        super().__init__(perfometer, translated_metrics)

        if self._perfometer is not None and "metric" not in self._perfometer:
            raise MKGeneralException(
                _('Missing key "metric" in logarithmic perfometer: %r') % self._perfometer
            )

    def get_stack(self) -> MetricRendererStack:
        value, unit, color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return [
            self.get_stack_from_values(
                value,
                *self.estimate_parameters_for_converted_units(
                    unit.get(
                        "conversion",
                        lambda v: v,
                    )
                ),
                color,
            )
        ]

    def _get_type_label(self) -> str:
        value, unit, _color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return self._render_value(unit, value)

    def get_sort_value(self) -> float:
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        value, _unit, _color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return value

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
        h_50 = self._perfometer["half_value"]
        f_10 = self._perfometer["exponent"]
        h_50_c = conversion(self._perfometer["half_value"])
        return (
            h_50_c,
            conversion(h_50 * f_10) / h_50_c,
        )


@renderer_registry.register
class MetricometerRendererLinear(MetricometerRenderer):
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
                value, _unit, color = evaluate(ex, self._translated_metrics)
                entry.append((100.0 * value / total, color))

            # Paint rest only, if it is positive and larger than one promille
            if total - summed > 0.001:
                entry.append((100.0 * (total - summed) / total, get_themed_perfometer_bg_color()))

        return [entry]

    def _evaluate_total(self, total_expression: MetricExpression | int | float) -> float:
        if isinstance(total_expression, float | int):
            return self._unit().get("conversion", lambda v: v)(total_expression)
        total, _unit, _color = evaluate(total_expression, self._translated_metrics)
        return total

    def _unit(self) -> UnitInfo:
        # We assume that all expressions across all segments have the same unit
        _value, unit, _color = evaluate(self._perfometer["segments"][0], self._translated_metrics)
        return unit

    def _get_type_label(self) -> str:
        return self._render_value(self._unit(), self._get_summed_values())

    def get_sort_value(self) -> float:
        """Use the first segment value for sorting"""
        value, _unit, _color = evaluate(self._perfometer["segments"][0], self._translated_metrics)
        return value

    def _get_summed_values(self):
        summed = 0.0
        for ex in self._perfometer["segments"]:
            value, _unit, _color = evaluate(ex, self._translated_metrics)
            summed += value
        return summed


@renderer_registry.register
class MetricometerRendererStacked(MetricometerRenderer):
    @classmethod
    def type_name(cls) -> str:
        return "stacked"

    def get_stack(self) -> MetricRendererStack:
        stack = []
        for sub_perfometer in self._perfometer["perfometers"]:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            stack.append(sub_stack[0])

        return stack

    def _get_type_label(self) -> str:
        sub_labels = []
        for sub_perfometer in self._perfometer["perfometers"]:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_value(self) -> float:
        """Use the number of the first stack element."""
        sub_perfometer = self._perfometer["perfometers"][0]
        renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
        return renderer.get_sort_value()


@renderer_registry.register
class MetricometerRendererDual(MetricometerRenderer):
    @classmethod
    def type_name(cls) -> str:
        return "dual"

    def __init__(self, perfometer, translated_metrics) -> None:  # type: ignore[no-untyped-def]
        super().__init__(perfometer, translated_metrics)

        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer["perfometers"])
            )

    def get_stack(self) -> MetricRendererStack:
        content: list[tuple[int | float, str]] = []
        for nr, sub_perfometer in enumerate(self._perfometer["perfometers"]):
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

    def _get_type_label(self) -> str:
        sub_labels = []
        for sub_perfometer in self._perfometer["perfometers"]:
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
        for sub_perfometer in self._perfometer["perfometers"]:
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
        [CombinedSingleMetricSpec], Sequence[CombinedGraphMetric]
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
        [CombinedSingleMetricSpec], Sequence[CombinedGraphMetric]
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
        graph_display_id=json.loads(request.get_str_input_mandatory("id")),
    )
