#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Iterable,
    Mapping,
    Tuple,
)

from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryElements,
    DropdownChoice,
    GraphColor,
    Timerange,
)

from cmk.gui.plugins.dashboard.utils import (
    create_data_for_single_metric,
    render_title_with_macros_string,
)
from cmk.gui.plugins.dashboard import dashlet_registry, ABCFigureDashlet
from cmk.gui.plugins.metrics.valuespecs import ValuesWithUnits
from cmk.gui.plugins.metrics.utils import MetricName
from cmk.gui.plugins.metrics.rrd_fetch import metric_in_all_rrd_columns
from cmk.gui.plugins.views.painters import service_state_short


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

    def svc_map(row):
        state, status_name = service_state_short(row)
        draw_status = properties.get("status_border", "not_ok")
        if draw_status == "not_ok" and state == "0":
            draw_status = False

        return {
            "style": "svcstate state%s" % state,
            "msg": _("Status: ") + status_name,
            "draw": draw_status
        }

    def metric_state_color(metric):
        warn = metric["scalar"].get("warn")
        crit = metric["scalar"].get("crit")
        if warn is not None and crit is not None:
            if metric['value'] >= crit:
                return "#FF3232"
            if metric['value'] >= warn:
                return "#FFFE44"
            return "#13D389"
        return "#3CC2FF"

    # Historic values are always added as plot_type area
    if properties.get("time_range", "current")[0] == "range":
        for row_id, metric, row in metrics:
            # Fix style for 2.0 release
            # time_range_params = properties["time_range"][1]
            # chosen_color = time_range_params.get("color", "default")
            # color = metric.get(
            # 'color',
            # "#008EFF",
            # ) if chosen_color == "default" else chosen_color
            plot_type = "area"
            color = "#008EFF"
            plot_definition = {
                "label": row['host_name'],
                "id": row_id,
                "plot_type": plot_type,
                "use_tags": [row_id],
                "color": color,
                "opacity": 0.1 if plot_type == "area" else 1
            }
            if plot_type == "area":
                plot_definition["style"] = "with_topline"
            if properties.get("metric_status_display") == "background":
                plot_definition["color"] = metric_state_color(metric)
                plot_definition["opacity"] = 0.4 if plot_type == "area" else 1

            plot_definitions.append(plot_definition)

    # The current/last value definition also gets the metric levels
    for row_id, metric, row in metrics:
        plot_definition = {
            "label": row['host_name'],
            "id": "%s_single" % row_id,
            "plot_type": "single_value",
            "use_tags": [row_id],
            "svc_state": svc_map(row),
            "js_render": metric['unit'].get("js_render"),
            "metrics": {
                "warn": metric["scalar"].get("warn"),
                "crit": metric["scalar"].get("crit"),
                "min": metric["scalar"].get("min"),
                "max": metric["scalar"].get("max"),
            }
        }
        if "color" in metric:
            plot_definition["color"] = metric["color"]
        if "metric_status_display" in properties:
            plot_definition["metric_status_display"] = properties["metric_status_display"]

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
        allow_empty=True,
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

    if "with_graph_styling" in with_elements:
        yield "style", DropdownChoice(
            choices=[
                ("line", _("Line")),
                ("area", _("Area")),
            ],
            default_value="area",
            title=_("Style"),
        )
        yield "color", GraphColor(
            title=_("Color"),
            default_value="default",
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

        yield "display_range", CascadingDropdown(
            title=_("Display range"),
            choices=[
                ("fixed", _("Fixed range"),
                 ValuesWithUnits(vs_name="display_range",
                                 metric_vs_name="metric",
                                 help=_("Set the range in which data is displayed. "
                                        "Having selected a metric before auto selects "
                                        "here the matching unit of the metric."),
                                 elements=[_("Minimum"), _("Maximum")],
                                 validate_value_elemets=validate_range)),
                # ("infer", _("Automatic")), # For future logic
            ],
            default_value="fixed")

    if "metric_status_display" in with_elements:
        yield "metric_status_display", DropdownChoice(
            title=_("Metric Status"),
            choices=[(None, _("Metric value is displayed in neutral color")),
                     ("text", _("Metric state is colored in its value")),
                     ("background", _("Metric status is colored on the dashlet background"))],
        )

    if "status_border" in with_elements:
        yield "status_border", DropdownChoice(
            title=_("Status border"),
            choices=[
                (False, _("Do not show any service status border")),
                ("not_ok", _("Draw a status border when service is not OK")),
                ("always", _("Always draw the service status on the border")),
            ],
            default_value="not_ok")


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
        return ""

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
        return _vs_elements(["time_range", "status_border", "metric_status_display"])

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from super().get_additional_title_macros()
        yield "$SITE$"
