#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

import cmk.utils
import cmk.utils.plugin_registry
import cmk.utils.render

import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.exceptions import MKGeneralException, MKInternalError, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.metrics.html_render import (
    host_service_graph_dashlet_cmk,
    host_service_graph_popup_cmk,
)

# Needed for legacy (pre 1.6) plugins and for cross-module imports (e.g. in dashboards plugin)
from cmk.gui.plugins.metrics.utils import (  # noqa: F401 # pylint: disable=unused-import
    check_metrics,
    darken_color,
    evaluate,
    G,
    GB,
    generic_graph_template,
    get_graph_range,
    get_graph_templates,
    get_palette_color_by_index,
    graph_info,
    hsv_to_hexrgb,
    indexed_color,
    K,
    KB,
    LegacyPerfometer,
    m,
    M,
    MAX_CORES,
    MB,
    metric_info,
    P,
    parse_color,
    parse_color_into_hexrgb,
    parse_perf_data,
    PB,
    perfometer_info,
    perfvar_translation,
    render_color,
    render_color_icon,
    replace_expressions,
    scalar_colors,
    scale_symbols,
    T,
    TB,
    translate_metrics,
    translated_metrics_from_row,
    TranslatedMetrics,
    unit_info,
)
from cmk.gui.type_defs import PerfometerSpec
from cmk.gui.view_utils import get_themed_perfometer_bg_color

PerfometerExpression = Union[str, int, float]
RequiredMetricNames = Set[str]

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

    fixup_graph_info()
    fixup_unit_info()
    fixup_perfometer_info()


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.metrics as api_module
    import cmk.gui.plugins.metrics.utils as plugin_utils

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
        api_module.__dict__[name] = plugin_utils.__dict__[name]


def fixup_graph_info() -> None:
    # create back link from each graph to its id.
    for graph_id, graph in graph_info.items():
        graph["id"] = graph_id


def fixup_unit_info() -> None:
    # create back link from each unit to its id.
    for unit_id, unit in unit_info.items():
        unit["id"] = unit_id
        unit.setdefault("description", unit["title"])


def fixup_perfometer_info() -> None:
    _convert_legacy_tuple_perfometers(perfometer_info)


# During implementation of the metric system the perfometers were first defined using
# tuples. This has been replaced with a dict based syntax. This function converts the
# old known formats from tuple to dict.
# All shipped perfometers have been converted to the dict format with 1.5.0i3.
# TODO: Remove this one day.
def _convert_legacy_tuple_perfometers(
    perfometers: List[Union[LegacyPerfometer, PerfometerSpec]]
) -> None:
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
    perfometer: Union[LegacyPerfometer, PerfometerSpec]
) -> List[PerfometerExpression]:

    if not isinstance(perfometer, dict):
        raise MKGeneralException(_("Legacy performeter encountered: %r") % perfometer)

    try:
        return perfometer["_required"]
    except KeyError:
        pass

    # calculate the list of metric expressions of the perfometers
    return perfometer.setdefault("_required", _perfometer_expressions(perfometer))


def _lookup_required_names(
    perfometer: Union[LegacyPerfometer, PerfometerSpec]
) -> Optional[RequiredMetricNames]:

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


def _perfometer_expressions(perfometer: PerfometerSpec) -> List[PerfometerExpression]:
    """Returns all metric expressions of a perfometer
    This is used for checking which perfometer can be displayed for a given service later.
    """
    required: List[PerfometerExpression] = []

    if perfometer["type"] == "linear":
        required += perfometer["segments"][:]

    elif perfometer["type"] == "logarithmic":
        required.append(perfometer["metric"])

    elif perfometer["type"] in ("stacked", "dual"):
        if "perfometers" not in perfometer:
            raise MKGeneralException(
                _("Perfometers of type 'stacked' and 'dual' need " "the element 'perfometers' (%r)")
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
    required_expressions: List[PerfometerExpression],
) -> Optional[RequiredMetricNames]:
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


def metric_to_text(metric: Dict[str, Any], value: Optional[Union[int, float]] = None) -> str:
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
    perf_data_string: str, check_command: Optional[str] = None
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
    ) -> Optional[PerfometerSpec]:
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
        required_metric_names: Optional[RequiredMetricNames],
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
        self, value: Union[str, int, float], translated_metrics: TranslatedMetrics
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


MetricRendererStack = List[List[Tuple[Union[int, float], str]]]


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
            if unit_name:
                unit = unit_info[unit_name]
            return unit["render"](value)

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


class MetricometerRendererRegistry(cmk.utils.plugin_registry.Registry[Type[MetricometerRenderer]]):
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
        value, _unit, color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return [
            self.get_stack_from_values(
                value, self._perfometer["half_value"], self._perfometer["exponent"], color
            )
        ]

    def _get_type_label(self) -> str:
        value, unit, _color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return unit["render"](value)

    def get_sort_value(self) -> float:
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        value, _unit, _color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return value

    @staticmethod
    def get_stack_from_values(
        value: Union[str, int, float],
        half_value: Union[int, float],
        base: Union[int, float],
        color: str,
    ) -> List[Tuple[Union[int, float], str]]:
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


@renderer_registry.register
class MetricometerRendererLinear(MetricometerRenderer):
    @classmethod
    def type_name(cls) -> str:
        return "linear"

    def get_stack(self) -> MetricRendererStack:
        entry = []

        summed = self._get_summed_values()

        if "total" in self._perfometer:
            total, _unit, _color = evaluate(self._perfometer["total"], self._translated_metrics)
        else:
            total = summed

        if total == 0:
            entry.append((100.0, get_themed_perfometer_bg_color()))

        else:
            for ex in self._perfometer["segments"]:
                value, _unit, color = evaluate(ex, self._translated_metrics)
                entry.append((100.0 * value / total, color))

            # Paint rest only, if it is positive and larger than one promille
            if total - summed > 0.001:
                entry.append((100.0 * (total - summed) / total, get_themed_perfometer_bg_color()))

        return [entry]

    def _get_type_label(self) -> str:
        # Use unit of first metrics for output of sum. We assume that all
        # stackes metrics have the same unit anyway
        _value, unit, _color = evaluate(self._perfometer["segments"][0], self._translated_metrics)
        return unit["render"](self._get_summed_values())

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

    def __init__(self, perfometer, translated_metrics):
        super().__init__(perfometer, translated_metrics)

        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly " "two definitions, not %d")
                % len(perfometer["perfometers"])
            )

    def get_stack(self) -> MetricRendererStack:
        content: List[Tuple[Union[int, float], str]] = []
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
@cmk.gui.pages.register("host_service_graph_popup")
def page_host_service_graph_popup() -> None:
    site_id = request.var("site")
    host_name = request.var("host_name")
    service_description = request.get_str_input("service")
    host_service_graph_popup_cmk(site_id, host_name, service_description)


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


@cmk.gui.pages.register("graph_dashlet")
def page_graph_dashlet() -> None:
    spec = request.var("spec")
    if not spec:
        raise MKUserError("spec", _("Missing spec parameter"))
    graph_identification = json.loads(request.get_str_input_mandatory("spec"))

    render = request.var("render")
    if not render:
        raise MKUserError("render", _("Missing render parameter"))
    custom_graph_render_options = json.loads(request.get_str_input_mandatory("render"))

    host_service_graph_dashlet_cmk(graph_identification, custom_graph_render_options)
