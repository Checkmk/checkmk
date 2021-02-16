#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Iterable, Mapping, Tuple

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard import ABCFigureDashlet, dashlet_registry
from cmk.gui.plugins.dashboard.utils import (
    create_data_for_single_metric,
    render_title_with_macros_string,
    purge_metric_for_js,
)
from cmk.gui.plugins.metrics.rrd_fetch import metric_in_all_rrd_columns
from cmk.gui.plugins.metrics.utils import MetricName
from cmk.gui.plugins.metrics.valuespecs import ValuesWithUnits
from cmk.gui.plugins.views.painters import service_state_short
from cmk.gui.valuespec import (
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DictionaryElements,
    DropdownChoice,
    Timerange,
)


def dashlet_title(
    settings: Mapping[str, Any],
    metric: Tuple[str, Mapping[str, Any], Mapping[str, Any]],
) -> str:
    if not settings.get("show_title", True):
        return ""
    default_title = SingleMetricDashlet.default_display_title()
    _unused, metric_specs, metric_context = metric
    metric_name = metric_specs.get("title")
    return render_title_with_macros_string(
        {
            context_key: metric_context[metrics_key] for metrics_key, context_key in (
                ("host_name", "host"),
                ("service_description", "service"),
                ("site", "site"),
            ) if metrics_key in metric_context
        },
        settings["single_infos"],
        settings.get("title", default_title),
        default_title,
        **({
            "$METRIC_NAME$": metric_name
        } if metric_name else {}),
    )


def required_columns(properties, context):
    cmc_cols = [
        "host_name", "service_check_command", "service_description", "service_perf_data",
        "service_state", "service_has_been_checked"
    ]
    metric_columns = []
    if properties.get("time_range", "current")[0] == "range":
        params = properties["time_range"][1]
        from_time, until_time = map(int, Timerange().compute_range(params['window'])[0])
        metric_columns = metric_in_all_rrd_columns(properties["metric"],
                                                   params["rrd_consolidation"], from_time,
                                                   until_time)

    return cmc_cols + metric_columns


def _create_single_metric_config(data, metrics, properties, context, settings):
    plot_definitions = []

    def metric_state_color(metric):
        warn = metric["scalar"].get("warn")
        crit = metric["scalar"].get("crit")
        if warn is not None and crit is not None:
            if metric['value'] >= crit:
                return "2", "CRIT"
            if metric['value'] >= warn:
                return "1", "WARN"
            return "0", "OK"
        return "_", ""

    def svc_map(row):
        state, status_name = service_state_short(row)
        return {
            "style": "svcstate state%s" % state,
            "msg": _("Service: ") + status_name,
            "draw": state != "0",
        }

    def metric_map(metric):
        state, status_name = metric_state_color(metric)
        return {
            "style": "metricstate state%s" % state,
            "msg": _("Metric: ") + status_name if status_name else "",
            "draw": state != "0",
        }

    def status_component(style, metric, row):
        if style == "service":
            return svc_map(row)
        if style == "metric":
            return metric_map(metric)
        return {}

    # Historic values are always added as plot_type area
    if properties.get("time_range", "current")[0] == "range":
        for row_id, metric, row in metrics:
            plot_definition = {
                "label": row['host_name'],
                "id": row_id,
                "plot_type": "area",
                "style": "with_topline",
                "use_tags": [row_id],
                "color": "#008EFF",
                "opacity": 0.1,
                "metric": purge_metric_for_js(metric),
            }

            plot_definitions.append(plot_definition)

    # The current/last value definition also gets the metric levels
    for row_id, metric, row in metrics:
        plot_definition = {
            "label": row['host_name'],
            "id": "%s_single" % row_id,
            "plot_type": "single_value",
            "use_tags": [row_id],
            "border_component": status_component(properties.get("status_border"), metric, row),
            "inner_render": status_component(properties.get("inner_state_display"), metric, row),
            "metric": purge_metric_for_js(metric),
            "color": metric.get("color", "#3CC2FF")
        }

        plot_definitions.append(plot_definition)

    return {
        "plot_definitions": plot_definitions,
        "data": data,
        "title": dashlet_title(settings, metrics[0] if metrics else ("", {}, {}))
    }


def _time_range_historic_dict_elements(with_elements) -> DictionaryElements:
    yield 'window', Timerange(
        title=_("Time range to consider"),
        default_value="d0",
    )
    yield "rrd_consolidation", DropdownChoice(
        choices=[
            ("average", _("Average")),
            ("min", _("Minimum")),
            ("max", _("Maximum")),
        ],
        default_value="max",
        title="RRD consolidation",
        help=_("Consolidation function for the [cms_graphing#rrds|RRD] data column"),
    )


def _vs_elements(with_elements) -> DictionaryElements:
    yield ("metric", MetricName())  # MetricChoice would be nicer, but we use the context filters
    if "time_range" in with_elements:
        yield "time_range", CascadingDropdown(
            title=_("Timerange"),
            orientation="horizontal",
            choices=[
                (
                    "current",
                    _("Only show current value"),
                ),
                (
                    "range",
                    _("Show historic values"),
                    Dictionary(
                        optional_keys=False,
                        elements=_time_range_historic_dict_elements(with_elements),
                        show_more_keys=['rrd_consolidation'],
                    ),
                ),
            ],
            default_value="current",
        )

    if "display_range" in with_elements:

        def validate_range(value, varprefix):
            _min, _max = value
            if _min >= _max:
                raise MKUserError(varprefix,
                                  _("Display range: Minimum must be strictly less than maximum"))

        fix_range: CascadingDropdownChoice = (
            "fixed", _("Fixed range"),
            ValuesWithUnits(vs_name="display_range",
                            metric_vs_name="metric",
                            help=_("Set the range in which data is displayed. "
                                   "Having selected a metric before auto selects "
                                   "here the matching unit of the metric."),
                            elements=[_("Minimum"), _("Maximum")],
                            validate_value_elemets=validate_range))
        auto_range: CascadingDropdownChoice = ("automatic",
                                               _("Automatically adjusted to available data"))

        choices = [fix_range] + ([auto_range] if "automatic_range" in with_elements else [])

        yield "display_range", CascadingDropdown(
            title=_("Data range"),
            choices=choices,
            default_value="automatic" if "automatic_range" in with_elements else "fixed")

        if "toggle_range_display" in with_elements:
            yield "toggle_range_display", DropdownChoice(
                title=_("Show range limits"),
                choices=[(True, _("Show the limits of values displayed")),
                         (False, _("Don't show information of limits"))])

    if "inner_state_display" in with_elements:
        yield "inner_state_display", DropdownChoice(
            title=_("Metric color"),
            choices=[(None, _("Follow theme default")),
                     ("service", _("Color value after SERVICE state")),
                     ("metric", _("Color value following it's METRIC THRESHOLDS if available"))],
        )

    if "status_border" in with_elements:
        yield "status_border", DropdownChoice(
            title=_("Status border"),
            choices=[
                (None, _("Do not show any status border")),
                ("service", _("Draw a status border when SERVICE is not OK")),
                ("metric", _("Draw a status border when METRICS THRESHOLDS are crossed")),
            ],
            default_value="service")


class SingleMetricDashlet(ABCFigureDashlet):
    @staticmethod
    def generate_response_data(properties, context, settings):
        data, metrics = create_data_for_single_metric(properties, context, required_columns)
        return _create_single_metric_config(data, metrics, properties, context, settings)

    @classmethod
    def single_infos(cls):
        return ["service", "host"]

    @staticmethod
    def default_display_title() -> str:
        return "$METRIC_NAME$"

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield "$METRIC_NAME$"


#   .--Gauge---------------------------------------------------------------.
#   |                     ____                                             |
#   |                    / ___| __ _ _   _  __ _  ___                      |
#   |                   | |  _ / _` | | | |/ _` |/ _ \                     |
#   |                   | |_| | (_| | |_| | (_| |  __/                     |
#   |                    \____|\__,_|\__,_|\__, |\___|                     |
#   |                                      |___/                           |
#   +----------------------------------------------------------------------+


@dashlet_registry.register
class GaugeDashlet(SingleMetricDashlet):
    """Dashlet that displays a scatterplot and average lines for a selected type of service"""
    @classmethod
    def type_name(cls):
        return "gauge"

    @classmethod
    def title(cls):
        return _("Gauge")

    @classmethod
    def description(cls):
        return _("Displays Gauge")

    @staticmethod
    def _vs_elements():
        return _vs_elements(["time_range", "display_range", "status_border"])

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from super().get_additional_title_macros()
        yield "$SITE$"


#   .--Bar Plot------------------------------------------------------------.
#   |                ____               ____  _       _                    |
#   |               | __ )  __ _ _ __  |  _ \| | ___ | |_                  |
#   |               |  _ \ / _` | '__| | |_) | |/ _ \| __|                 |
#   |               | |_) | (_| | |    |  __/| | (_) | |_                  |
#   |               |____/ \__,_|_|    |_|   |_|\___/ \__|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@dashlet_registry.register
class BarplotDashlet(SingleMetricDashlet):
    @classmethod
    def type_name(cls):
        return "barplot"

    @classmethod
    def title(cls):
        return _("Barplot")

    @classmethod
    def description(cls):
        return _("Barplot")

    @staticmethod
    def _vs_elements():
        return _vs_elements([])

    @classmethod
    def single_infos(cls):
        return ["service"]


#   .--Single Graph--------------------------------------------------------.
#   |      ____  _             _         ____                 _            |
#   |     / ___|(_)_ __   __ _| | ___   / ___|_ __ __ _ _ __ | |__         |
#   |     \___ \| | '_ \ / _` | |/ _ \ | |  _| '__/ _` | '_ \| '_ \        |
#   |      ___) | | | | | (_| | |  __/ | |_| | | | (_| | |_) | | | |       |
#   |     |____/|_|_| |_|\__, |_|\___|  \____|_|  \__,_| .__/|_| |_|       |
#   |                    |___/                         |_|                 |
#   +----------------------------------------------------------------------+


@dashlet_registry.register
class SingleGraphDashlet(SingleMetricDashlet):
    """Dashlet that displays a single metric"""
    @classmethod
    def type_name(cls):
        return "single_metric"

    @classmethod
    def title(cls):
        return _("Single metric")

    @classmethod
    def description(cls):
        return _("Displays a single metric of a specific host and service.")

    @staticmethod
    def _vs_elements():
        return _vs_elements([
            "time_range", "display_range", "automatic_range", "toggle_range_display",
            "status_border", "inner_state_display"
        ])

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from super().get_additional_title_macros()
        yield "$SITE$"
