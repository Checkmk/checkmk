#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
import math
import string
import json
import traceback

import six

import cmk.utils
import cmk.utils.render
import cmk.utils.plugin_registry
from cmk.utils.regex import regex

import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.i18n
import cmk.gui.pages
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.log import logger
from cmk.gui.exceptions import MKGeneralException, MKUserError, MKInternalError

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.metrics.utils import (  # pylint: disable=unused-import
    unit_info, metric_info, check_metrics, perfometer_info, graph_info, scalar_colors, KB, MB, GB,
    TB, PB, m, K, M, G, T, P, evaluate, get_graph_range, replace_expressions,
    generic_graph_template, scale_symbols, hsv_to_hexrgb, render_color, parse_color,
    parse_color_into_hexrgb, render_color_icon, darken_color, get_palette_color_by_index,
    parse_perf_data, perfvar_translation, translate_metrics, get_graph_templates,
)

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
# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False


def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    utils.load_web_plugins("metrics", globals())

    fixup_graph_info()
    fixup_unit_info()
    fixup_perfometer_info()
    loaded_with_language = cmk.gui.i18n.get_current_language()


def fixup_graph_info():
    # create back link from each graph to its id.
    for graph_id, graph in graph_info.items():
        graph["id"] = graph_id


def fixup_unit_info():
    # create back link from each unit to its id.
    for unit_id, unit in unit_info.items():
        unit["id"] = unit_id
        unit.setdefault("description", unit["title"])


def fixup_perfometer_info():
    _convert_legacy_tuple_perfometers(perfometer_info)
    _precalculate_some_perfometer_caches(perfometer_info)


# During implementation of the metric system the perfometers were first defined using
# tuples. This has been replaced with a dict based syntax. This function converts the
# old known formats from tuple to dict.
# All shipped perfometers have been converted to the dict format with 1.5.0i3.
# TODO: Remove this one day.
def _convert_legacy_tuple_perfometers(perfometers):
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
                _("Could not convert perfometer to dict format: %r. Ignoring this one.") %
                perfometer)
            perfometers.pop(index)


def _precalculate_some_perfometer_caches(perfometers):
    for perfometer in perfometers:
        # Precalculate the list of metric expressions of the perfometers
        required_expressions = _perfometer_expressions(perfometer)

        # And also precalculate the trivial metric names that can later be used to filter
        # perfometers without the need to evaluate the expressions.
        required_trivial_metric_names = _required_trivial_metric_names(required_expressions)

        perfometer["_required"] = required_expressions
        perfometer["_required_names"] = required_trivial_metric_names


def _perfometer_expressions(perfometer):
    """Returns all metric expressions of a perfometer
    This is used for checking which perfometer can be displayed for a given service later.
    """
    required = []

    if perfometer["type"] == "linear":
        required += perfometer["segments"][:]

    elif perfometer["type"] == "logarithmic":
        required.append(perfometer["metric"])

    elif perfometer["type"] in ("stacked", "dual"):
        if "perfometers" not in perfometer:
            raise MKGeneralException(
                _("Perfometers of type 'stacked' and 'dual' need "
                  "the element 'perfometers' (%r)") % perfometer)

        for sub_perfometer in perfometer["perfometers"]:
            required += _perfometer_expressions(sub_perfometer)

    else:
        raise NotImplementedError(_("Invalid perfometer type: %s") % perfometer["type"])

    if "label" in perfometer and perfometer["label"] is not None:
        required.append(perfometer["label"][0])
    if "total" in perfometer:
        required.append(perfometer["total"])

    return required


def _required_trivial_metric_names(required_expressions):
    """Extract the trivial metric names from a list of expressions.
    Ignores numeric parts. Returns None in case there is a non trivial
    metric found. This means the trivial filtering can not be used.
    """
    required_metric_names = set()

    allowed_chars = string.ascii_letters + string.digits + "_"

    for entry in required_expressions:
        if isinstance(entry, six.string_types):
            if any(char not in allowed_chars for char in entry):
                # Found a non trivial metric expression. Totally skip this mechanism
                return None

            required_metric_names.add(entry)

    return required_metric_names


#.
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


def metric_to_text(metric, value=None):
    if value is None:
        value = metric["value"]
    return metric["unit"]["render"](value)


# aliases to be compatible to old plugins
physical_precision = cmk.utils.render.physical_precision
age_human_readable = cmk.utils.render.approx_age

#.
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


def translate_perf_data(perf_data_string, check_command=None):
    perf_data, check_command = parse_perf_data(perf_data_string, check_command)
    return translate_metrics(perf_data, check_command)


#.
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


class Perfometers(object):
    def get_matching_perfometers(self, translated_metrics):
        perfometers = []
        for perfometer in perfometer_info:
            if self._perfometer_possible(perfometer, translated_metrics):
                perfometers.append(perfometer)
        return perfometers

    def _perfometer_possible(self, perfometer, translated_metrics):
        if not translated_metrics:
            return False

        if self._skip_perfometer_by_trivial_metrics(perfometer["_required_names"],
                                                    translated_metrics):
            return False

        for req in perfometer["_required"]:
            try:
                evaluate(req, translated_metrics)
            except:
                return False

        if "condition" in perfometer:
            try:
                value, _color, _unit = evaluate(perfometer["condition"], translated_metrics)
                if value == 0.0:
                    return False
            except:
                return False

        return True

    def _skip_perfometer_by_trivial_metrics(self, required_metric_names, translated_metrics):
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


class MetricometerRenderer(object):
    __metaclass__ = abc.ABCMeta
    """Abstract base class for all metricometer renderers"""

    @classmethod
    def type_name(cls):
        raise NotImplementedError()

    def __init__(self, perfometer, translated_metrics):
        super(MetricometerRenderer, self).__init__()
        self._perfometer = perfometer
        self._translated_metrics = translated_metrics

    @abc.abstractmethod
    def get_stack(self):
        """Return a list of perfometer elements

        Each element is represented by a 2 element tuple where the first element is
        the width in px and the second element the hex color code of this element.
        """
        raise NotImplementedError()

    def get_label(self):
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
    def _get_type_label(self):
        """Returns the label for this perfometer type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_sort_number(self):
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        raise NotImplementedError()


class MetricometerRendererRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return MetricometerRenderer

    def plugin_name(self, plugin_class):
        return plugin_class.type_name()

    def get_renderer(self, perfometer, translated_metrics):
        subclass = self[perfometer["type"]]
        return subclass(perfometer, translated_metrics)


renderer_registry = MetricometerRendererRegistry()


@renderer_registry.register
class MetricometerRendererLogarithmic(MetricometerRenderer):
    @classmethod
    def type_name(cls):
        return "logarithmic"

    def __init__(self, perfometer, translated_metrics):
        super(MetricometerRendererLogarithmic, self).__init__(perfometer, translated_metrics)

        if self._perfometer is not None and "metric" not in self._perfometer:
            raise MKGeneralException(
                _("Missing key \"metric\" in logarithmic perfometer: %r") % self._perfometer)

    def get_stack(self):
        value, _unit, color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return [
            self.get_stack_from_values(value, self._perfometer["half_value"],
                                       self._perfometer["exponent"], color)
        ]

    def _get_type_label(self):
        value, unit, _color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return unit["render"](value)

    def get_sort_number(self):
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        value, _unit, _color = evaluate(self._perfometer["metric"], self._translated_metrics)
        return value

    def get_stack_from_values(self, value, half_value, base, color):
        # Negative values are printed like positive ones (e.g. time offset)
        value = abs(float(value))
        if value == 0.0:
            pos = 0
        else:
            half_value = float(half_value)
            h = math.log(half_value, base)  # value to be displayed at 50%
            pos = 50 + 10.0 * (math.log(value, base) - h)
            if pos < 2:
                pos = 2
            if pos > 98:
                pos = 98

        return [(pos, color), (100 - pos, "#ffffff")]


@renderer_registry.register
class MetricometerRendererLinear(MetricometerRenderer):
    @classmethod
    def type_name(cls):
        return "linear"

    def get_stack(self):
        entry = []

        summed = self._get_summed_values()

        if "total" in self._perfometer:
            total, _unit, _color = evaluate(self._perfometer["total"], self._translated_metrics)
        else:
            total = summed

        if total == 0:
            entry.append((100.0, "#ffffff"))

        else:
            for ex in self._perfometer["segments"]:
                value, _unit, color = evaluate(ex, self._translated_metrics)
                entry.append((100.0 * value / total, color))

            # Paint rest only, if it is positive and larger than one promille
            if total - summed > 0.001:
                entry.append((100.0 * (total - summed) / total, "#ffffff"))

        return [entry]

    def _get_type_label(self):
        # Use unit of first metrics for output of sum. We assume that all
        # stackes metrics have the same unit anyway
        _value, unit, _color = evaluate(self._perfometer["segments"][0], self._translated_metrics)
        return unit["render"](self._get_summed_values())

    def get_sort_number(self):
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
    def type_name(cls):
        return "stacked"

    def get_stack(self):
        stack = []
        for sub_perfometer in self._perfometer["perfometers"]:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            stack.append(sub_stack[0])

        return stack

    def _get_type_label(self):
        sub_labels = []
        for sub_perfometer in self._perfometer["perfometers"]:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_number(self):
        """Use the number of the first stack element."""
        sub_perfometer = self._perfometer["perfometers"][0]
        renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
        return renderer.get_sort_number()


@renderer_registry.register
class MetricometerRendererDual(MetricometerRenderer):
    @classmethod
    def type_name(cls):
        return "dual"

    def __init__(self, perfometer, translated_metrics):
        super(MetricometerRendererDual, self).__init__(perfometer, translated_metrics)

        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly "
                  "two definitions, not %d") % len(perfometer["perfometers"]))

    def get_stack(self):
        content = []
        for nr, sub_perfometer in enumerate(self._perfometer["perfometers"]):
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            if len(sub_stack) != 1:
                raise MKInternalError(
                    _("Perf-O-Meter of type 'dual' must only contain plain Perf-O-Meters"))

            half_stack = [(value / 2, color) for (value, color) in sub_stack[0]]
            if nr == 0:
                half_stack.reverse()
            content += half_stack

        return [content]

    def _get_type_label(self):
        sub_labels = []
        for sub_perfometer in self._perfometer["perfometers"]:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_number(self):
        """Sort by max(left, right)

        E.g. for traffic graphs it seems to be useful to
        make it sort by the maximum traffic independent of the direction.
        """
        sub_sort_numbers = []
        for sub_perfometer in self._perfometer["perfometers"]:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
            sub_sort_numbers.append(renderer.get_sort_number())

        return max(*sub_sort_numbers)


#.
#   .--PNP Templates-------------------------------------------------------.
#   |  ____  _   _ ____    _____                    _       _              |
#   | |  _ \| \ | |  _ \  |_   _|__ _ __ ___  _ __ | | __ _| |_ ___  ___   |
#   | | |_) |  \| | |_) |   | |/ _ \ '_ ` _ \| '_ \| |/ _` | __/ _ \/ __|  |
#   | |  __/| |\  |  __/    | |  __/ | | | | | |_) | | (_| | ||  __/\__ \  |
#   | |_|   |_| \_|_|       |_|\___|_| |_| |_| .__/|_|\__,_|\__\___||___/  |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   |  Core for creating templates for PNP4Nagios from CMK graph defi-     |
#   |  nitions.                                                            |
#   '----------------------------------------------------------------------'


def _scalar_description(expression, description, value):
    if description:
        return description
    if expression.endswith(':warn'):
        return 'Warning at %.1f' % value
    if expression.endswith(':crit'):
        return 'Critical at %.1f' % value
    return None


def _scalar_value_command(scalar, translated_metrics):
    if isinstance(scalar, tuple):
        expression, description = scalar
    else:
        expression, description = scalar, None

    try:
        value, _unit, color = evaluate(expression, translated_metrics)
    except Exception:
        return ""

    if not value:
        return ""

    rule_txt = _scalar_description(expression, description, value)
    if not rule_txt:
        return "HRULE:%s%s " % (value, color)

    return "HRULE:%s%s:\"%s\" COMMENT:\"\\n\" " % (
        value,
        color,
        rule_txt,
    )


@cmk.gui.pages.register("noauth:pnp_template")
def page_pnp_template():
    try:
        template_id = html.request.var("id")

        check_command, perf_string = template_id.split(":", 1)

        # TODO: pnp-templates/default.php still returns a default value of
        # 1 for the value and "" for the unit.
        perf_data, _ = parse_perf_data(perf_string)
        translated_metrics = translate_metrics(perf_data, check_command)
        if not translated_metrics:
            return  # check not supported

        # Collect output in string. In case of an exception to not output
        # any definitions
        output = ""
        for graph_template in get_graph_templates(translated_metrics):
            graph_code = render_graph_pnp(graph_template, translated_metrics)
            output += graph_code

        html.write(output)

    except Exception:
        html.write("An error occured:\n%s\n" % traceback.format_exc())


# TODO: some_value.max not yet working
def render_graph_pnp(graph_template, translated_metrics):
    graph_title = None
    vertical_label = None

    rrdgraph_commands = ""

    legend_precision = graph_template.get("legend_precision", 2)
    legend_scale = graph_template.get("legend_scale", 1)
    legend_scale_symbol = scale_symbols[legend_scale]

    # Define one RRD variable for each of the available metrics.
    # Note: We need to use the original name, not the translated one.
    for var_name, metrics in translated_metrics.items():
        rrd = "$RRDBASE$_" + metrics["orig_name"] + ".rrd"
        scale = metrics["scale"]
        unit = metrics["unit"]

        if scale != 1.0:
            rrdgraph_commands += "DEF:%s_UNSCALED=%s:1:MAX " % (var_name, rrd)
            rrdgraph_commands += "CDEF:%s=%s_UNSCALED,%f,* " % (var_name, var_name, scale)

        else:
            rrdgraph_commands += "DEF:%s=%s:1:MAX " % (var_name, rrd)

        # Scaling for legend
        rrdgraph_commands += "CDEF:%s_LEGSCALED=%s,%f,/ " % (var_name, var_name, legend_scale)

        # Prepare negative variants for upside-down graph
        rrdgraph_commands += "CDEF:%s_NEG=%s,-1,* " % (var_name, var_name)
        rrdgraph_commands += "CDEF:%s_LEGSCALED_NEG=%s_LEGSCALED,-1,* " % (var_name, var_name)

    # Now add areas and lines to the graph
    graph_metrics = []

    # Graph with upside down metrics? (e.g. for Disk IO)
    have_upside_down = False

    # Compute width of the right column of the legend
    max_title_length = 0
    for nr, metric_definition in enumerate(graph_template["metrics"]):
        if len(metric_definition) >= 3:
            title = metric_definition[2]
        elif not "," in metric_definition:
            metric_name = metric_definition[0].split("#")[0]
            mi = translated_metrics[metric_name]
            title = mi["title"]
        else:
            title = ""
        max_title_length = max(max_title_length, len(title))

    for nr, metric_definition in enumerate(graph_template["metrics"]):
        metric_name = metric_definition[0]
        line_type = metric_definition[1]  # "line", "area", "stack"

        # Optional title, especially for derived values
        if len(metric_definition) >= 3:
            title = metric_definition[2]
        else:
            title = ""

        # Prefixed minus renders the metrics in negative direction
        if line_type[0] == '-':
            have_upside_down = True
            upside_down = True
            upside_down_factor = -1
            line_type = line_type[1:]
            upside_down_suffix = "_NEG"
        else:
            upside_down = False
            upside_down_factor = 1
            upside_down_suffix = ""

        if line_type == "line":
            draw_type = "LINE"
            draw_stack = ""
        elif line_type == "area":
            draw_type = "AREA"
            draw_stack = ""
        elif line_type == "stack":
            draw_type = "AREA"
            draw_stack = ":STACK"

        # User can specify alternative color using a suffixed #aabbcc
        if '#' in metric_name:
            metric_name, custom_color = metric_name.split("#", 1)
        else:
            custom_color = None

        commands = ""
        # Derived value with RBN syntax (evaluated by RRDTool!).
        if "," in metric_name:
            # We evaluate just in order to get color and unit.
            # TODO: beware of division by zero. All metrics are set to 1 here.
            _value, unit, color = evaluate(metric_name, translated_metrics)

            if "@" in metric_name:
                expression, _explicit_unit_name = metric_name.rsplit("@", 1)  # isolate expression
            else:
                expression = metric_name

            # Choose a unique name for the derived variable and compute it
            commands += "CDEF:DERIVED%d=%s " % (nr, expression)
            if upside_down:
                commands += "CDEF:DERIVED%d_NEG=DERIVED%d,-1,* " % (nr, nr)

            metric_name = "DERIVED%d" % nr
            # Scaling and upsidedown handling for legend
            commands += "CDEF:%s_LEGSCALED=%s,%f,/ " % (metric_name, metric_name, legend_scale)
            if upside_down:
                commands += "CDEF:%s_LEGSCALED%s=%s,%f,/ " % (
                    metric_name, upside_down_suffix, metric_name, legend_scale * upside_down_factor)

        else:
            mi = translated_metrics[metric_name]
            if not title:
                title = mi["title"]
            color = parse_color_into_hexrgb(mi["color"])
            unit = mi["unit"]

        if custom_color:
            color = "#" + custom_color

        # Paint the graph itself
        # TODO: Die Breite des Titels intelligent berechnen. Bei legend = "mirrored" muss man die
        # Vefügbare Breite ermitteln und aufteilen auf alle Titel
        right_pad = " " * (max_title_length - len(title))
        commands += "%s:%s%s%s:\"%s%s\"%s " % (draw_type, metric_name, upside_down_suffix, color,
                                               title.replace(":", "\\:"), right_pad, draw_stack)
        if line_type == "area":
            commands += "LINE:%s%s%s " % (metric_name, upside_down_suffix,
                                          render_color(darken_color(parse_color(color), 0.2)))

        unit_symbol = unit["symbol"]
        if unit_symbol == "%":
            unit_symbol = "%%"
        else:
            unit_symbol = " " + unit_symbol

        graph_metrics.append((metric_name, unit_symbol, commands))

        # Use title and label of this metrics as default for the graph
        if title and not graph_title:
            graph_title = title
        if not vertical_label:
            vertical_label = unit["title"]

    # Now create the rrdgraph commands for all metrics - according to the choosen layout
    for metric_name, unit_symbol, commands in graph_metrics:
        rrdgraph_commands += commands
        legend_symbol = unit_symbol
        if unit_symbol and unit_symbol[0] == " ":
            legend_symbol = " %s%s" % (legend_scale_symbol, unit_symbol[1:])
        for what, what_title in [("AVERAGE", _("average")), ("MAX", _("max")), ("LAST", _("last"))]:
            rrdgraph_commands += "GPRINT:%%s_LEGSCALED:%%s:\"%%%%8.%dlf%%s %%s\" "  % legend_precision % \
                        (metric_name, what, legend_symbol, what_title)
        rrdgraph_commands += "COMMENT:\"\\n\" "

    # add horizontal rules for warn and crit scalars
    for scalar in graph_template.get("scalars", []):
        rrdgraph_commands += _scalar_value_command(scalar, translated_metrics)

    # For graphs with both up and down, paint a gray rule at 0
    if have_upside_down:
        rrdgraph_commands += "HRULE:0#c0c0c0 "

    # Now compute the arguments for the command line of rrdgraph
    rrdgraph_arguments = ""

    graph_title = graph_template.get("title", graph_title)
    vertical_label = graph_template.get("vertical_label", vertical_label)

    rrdgraph_arguments += " --vertical-label %s --title %s " % (cmk.utils.quote_shell_string(
        vertical_label or " "), cmk.utils.quote_shell_string(graph_title))

    min_value, max_value = get_graph_range(graph_template, translated_metrics)
    if min_value is not None and max_value is not None:
        rrdgraph_arguments += " -l %f -u %f" % (min_value, max_value)
    else:
        rrdgraph_arguments += " -l 0"

    return graph_title + "\n" + rrdgraph_arguments + "\n" + rrdgraph_commands + "\n"


#.
#   .--Hover-Graph---------------------------------------------------------.
#   |     _   _                           ____                 _           |
#   |    | | | | _____   _____ _ __      / ___|_ __ __ _ _ __ | |__        |
#   |    | |_| |/ _ \ \ / / _ \ '__|____| |  _| '__/ _` | '_ \| '_ \       |
#   |    |  _  | (_) \ V /  __/ | |_____| |_| | | | (_| | |_) | | | |      |
#   |    |_| |_|\___/ \_/ \___|_|        \____|_|  \__,_| .__/|_| |_|      |
#   |                                                   |_|                |
#   '----------------------------------------------------------------------'


def cmk_graphs_possible(site_id=None):
    try:
        return not config.force_pnp_graphing \
           and browser_supports_canvas() \
           and site_is_running_cmc(site_id)
    except:
        return False


# If site_id is None then we return True if at least
# one site is running CMC
def site_is_running_cmc(site_id):
    if site_id:
        return sites.state(site_id, {}).get("program_version", "").startswith("Check_MK")

    for status in sites.states().values():
        if status.get("program_version", "").startswith("Check_MK"):
            return True
    return False


def browser_supports_canvas():
    user_agent = html.request.user_agent

    if 'MSIE' in user_agent:
        matches = regex(r'MSIE ([0-9]{1,}[\.0-9]{0,})').search(user_agent)
        if matches:
            ie_version = float(matches.group(1))
            if ie_version >= 9.0:
                return True

        # Trying to deal with the IE compatiblity mode to detect the real IE version
        matches = regex(r'Trident/([0-9]{1,}[\.0-9]{0,})').search(user_agent)
        if matches:
            trident_version = float(matches.group(1)) + 4
            if trident_version >= 9.0:
                return True

        return False
    else:
        return True


def get_graph_template_by_source(graph_templates, source):
    graph_template = None
    for source_nr, template in enumerate(graph_templates):
        if source == source_nr + 1:
            graph_template = template
            break
    return graph_template


# This page is called for the popup of the graph icon of hosts/services.
@cmk.gui.pages.register("host_service_graph_popup")
def page_host_service_graph_popup():
    site_id = html.request.var('site')
    host_name = html.request.var('host_name')
    service_description = html.get_unicode_input('service')

    # TODO: Refactor this to some OO based approach
    if cmk_graphs_possible(site_id):
        import cmk.gui.cee.plugins.metrics.graphs as graphs
        graphs.host_service_graph_popup_cmk(site_id, host_name, service_description)
    else:
        host_service_graph_popup_pnp(site_id, host_name, service_description)


def host_service_graph_popup_pnp(site, host_name, service_description):
    pnp_host = cmk.utils.pnp_cleanup(host_name)
    pnp_svc = cmk.utils.pnp_cleanup(service_description)
    url_prefix = config.site(site)["url_prefix"]

    if html.mobile:
        url = url_prefix + ("pnp4nagios/index.php?kohana_uri=/mobile/popup/%s/%s" % \
            (html.urlencode(pnp_host), html.urlencode(pnp_svc)))
    else:
        url = url_prefix + ("pnp4nagios/index.php/popup?host=%s&srv=%s" % \
            (html.urlencode(pnp_host), html.urlencode(pnp_svc)))

    html.write(url)


#.
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
def page_graph_dashlet():
    spec = html.request.var("spec")
    if not spec:
        raise MKUserError("spec", _("Missing spec parameter"))
    graph_identification = json.loads(html.request.var("spec"))

    render = html.request.var("render")
    if not render:
        raise MKUserError("render", _("Missing render parameter"))
    custom_graph_render_options = json.loads(html.request.var("render"))

    # TODO: Refactor this to some OO based approach
    if cmk_graphs_possible():
        import cmk.gui.cee.plugins.metrics.graphs as graphs
        graphs.host_service_graph_dashlet_cmk(graph_identification, custom_graph_render_options)
    elif graph_identification[0] == "template":
        host_service_graph_dashlet_pnp(graph_identification)
    else:
        html.write(_("This graph can not be rendered."))


def host_service_graph_dashlet_pnp(graph_identification):
    site = graph_identification[1]["site"]
    source = int(graph_identification[1]["graph_index"])

    pnp_host = cmk.utils.pnp_cleanup(graph_identification[1]["host_name"])
    pnp_svc = cmk.utils.pnp_cleanup(graph_identification[1]["service_description"])
    url_prefix = config.site(site)["url_prefix"]

    pnp_theme = html.get_theme()
    if pnp_theme == "classic":
        pnp_theme = "multisite"

    html.write(url_prefix + "pnp4nagios/index.php/image?host=%s&srv=%s&source=%d&view=%s&theme=%s" % \
        (html.urlencode(pnp_host), html.urlencode(pnp_svc), source, html.request.var("timerange"), pnp_theme))


#.
#   .--Metrics Table-------------------------------------------------------.
#   |      __  __      _        _            _____     _     _             |
#   |     |  \/  | ___| |_ _ __(_) ___ ___  |_   _|_ _| |__ | | ___        |
#   |     | |\/| |/ _ \ __| '__| |/ __/ __|   | |/ _` | '_ \| |/ _ \       |
#   |     | |  | |  __/ |_| |  | | (__\__ \   | | (_| | |_) | |  __/       |
#   |     |_|  |_|\___|\__|_|  |_|\___|___/   |_|\__,_|_.__/|_|\___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Renders a simple table with all metrics of a host or service        |
#   '----------------------------------------------------------------------'


def render_metrics_table(translated_metrics, host_name, service_description):
    output = "<table class=metricstable>"
    for metric_name, metric in sorted(
            translated_metrics.items(),
            cmp=lambda a, b: cmp(a[1]["title"], b[1]["title"]),
    ):
        output += "<tr>"
        output += "<td class=color>%s</td>" % render_color_icon(metric["color"])
        output += "<td>%s:</td>" % metric["title"]
        output += "<td class=value>%s</td>" % metric["unit"]["render"](metric["value"])
        if cmk_graphs_possible():
            output += "<td>"
            output += html.render_popup_trigger(
                html.render_icon(
                    "custom_graph",
                    title=_("Add this metric to a custom graph"),
                    cssclass="iconbutton"),
                ident="add_metric_to_graph_" + host_name + ";" + service_description,
                what="add_metric_to_custom_graph",
                url_vars=[
                    ("host", host_name),
                    ("service", service_description),
                    ("metric", metric_name),
                ])
            output += "</td>"
        output += "</tr>"
    output += "</table>"
    return output
