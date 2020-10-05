#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import List, Tuple, Optional

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Dictionary,
    Timerange,
    TextUnicode,
    CascadingDropdown,
    DropdownChoice,
)
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.plugins.dashboard.utils import site_query, create_data_for_single_metric
from cmk.gui.plugins.metrics.utils import MetricName, reverse_translate_metric_name
from cmk.gui.plugins.metrics.rrd_fetch import rrd_columns
from cmk.gui.utils.url_encoder import HTTPVariables
from cmk.gui.figures import ABCFigureDashlet, ABCDataGenerator


class SingleMetricDataGenerator(ABCDataGenerator):
    """Data generator for a scatterplot with average lines"""
    @classmethod
    def vs_parameters(cls):
        return Dictionary(title=_("Properties"),
                          render="form",
                          optional_keys=["title"],
                          elements=cls._vs_elements())

    @classmethod
    def _vs_elements(cls):
        return [
            ("title", TextUnicode(default_value="", title=_("Figure title"))),
            ("metric", MetricName()),  # MetricChoice would be nicer, but is CEE
            ("rrd_consolidation",
             DropdownChoice(
                 choices=[
                     ("average", _("Average")),
                     ("min", _("Minimum")),
                     ("max", _("Maximum")),
                 ],
                 default_value="average",
                 title="RRD consolidation",
                 help=_("Consolidation function for the [cms_graphing#rrds|RRD] data column"),
             )),
            (
                "time_range",
                CascadingDropdown(
                    title=_("Timerange"),
                    orientation="horizontal",
                    choices=[
                        ("current", _("Only show current value")),
                        (
                            "range",
                            _("Show historic values"),
                            # TODO: add RRD consolidation, here and in _get_data below
                            Timerange(title=_("Time range to consider"),
                                      default_value="d0",
                                      allow_empty=True)),
                    ],
                    default_value="current"))
        ]

    @classmethod
    @site_query
    def _get_data(cls, properties, context):
        cmc_cols = [
            "host_name", "service_check_command", "service_description", "service_perf_data"
        ]
        metric_columns = []
        if properties["time_range"] != "current":
            from_time, until_time = map(int,
                                        Timerange().compute_range(properties["time_range"][1])[0])
            data_range = "%s:%s:%s" % (from_time, until_time, 60)
            _metrics: List[Tuple[str, Optional[str], float]] = [
                (name, None, scale)
                for name, scale in reverse_translate_metric_name(properties["metric"])
            ]
            metric_columns = list(rrd_columns(_metrics, properties["rrd_consolidation"],
                                              data_range))

        return cmc_cols + metric_columns

    @classmethod
    def generate_response_data(cls, properties, context):
        data, metrics = create_data_for_single_metric(cls, properties, context)
        return cls._create_single_metric_config(data, metrics, properties, context)

    @classmethod
    def _create_single_metric_config(cls, data, metrics, properties, context):
        plot_definitions = []

        # Historic values are always added as plot_type area
        if properties["time_range"] != "current":
            for row_id, host, metric in metrics:
                plot_definition = {
                    "plot_type": "area",
                    "label": host,
                    "id": row_id,
                    "use_tags": [row_id]
                }
                if "color" in metric:
                    plot_definition["color"] = metric["color"]
                plot_definitions.append(plot_definition)

        # The current/last value definition also gets the metric levels
        for row_id, host, metric in metrics:
            plot_definition = {
                "plot_type": "single_value",
                "id": "%s_single" % row_id,
                "use_tags": [row_id],
                "label": host,
                "metrics": {
                    "warn": metric["scalar"].get("warn"),
                    "crit": metric["scalar"].get("crit"),
                    "min": metric["scalar"].get("min"),
                    "max": metric["scalar"].get("max"),
                }
            }
            if "color" in metric:
                plot_definition["color"] = metric["color"]

            plot_definitions.append(plot_definition)

        response = {
            "plot_definitions": plot_definitions,
            "data": data,
        }

        response["title"] = properties.get("title")
        return response


@page_registry.register_page("single_metric_data")
class SingleMetricPage(AjaxPage):
    def page(self):
        return SingleMetricDataGenerator.generate_response_from_request()


#   .--Gauge---------------------------------------------------------------.
#   |                     ____                                             |
#   |                    / ___| __ _ _   _  __ _  ___                      |
#   |                   | |  _ / _` | | | |/ _` |/ _ \                     |
#   |                   | |_| | (_| | |_| | (_| |  __/                     |
#   |                    \____|\__,_|\__,_|\__, |\___|                     |
#   |                                      |___/                           |
#   +----------------------------------------------------------------------+


@dashlet_registry.register
class GaugeDashlet(ABCFigureDashlet):
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

    @classmethod
    def data_generator(cls):
        return SingleMetricDataGenerator

    @classmethod
    def single_infos(cls):
        return ["service"]

    def show(self):
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        fetch_url = "single_metric_data.py"
        args: HTTPVariables = []
        args.append(("context", json.dumps(self._dashlet_spec["context"])))
        args.append(
            ("properties", json.dumps(self.vs_parameters().value_to_json(self._dashlet_spec))))
        body = html.urlencode_vars(args)

        html.javascript(
            """
            let gauge_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("gauge");
            let %(instance_name)s = new gauge_class_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.initialize();
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """ % {
                "dashlet_id": self._dashlet_id,
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(body),
                "update": 60,
            })


#   .--Bar Plot------------------------------------------------------------.
#   |                ____               ____  _       _                    |
#   |               | __ )  __ _ _ __  |  _ \| | ___ | |_                  |
#   |               |  _ \ / _` | '__| | |_) | |/ _ \| __|                 |
#   |               | |_) | (_| | |    |  __/| | (_) | |_                  |
#   |               |____/ \__,_|_|    |_|   |_|\___/ \__|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@dashlet_registry.register
class BarplotDashlet(ABCFigureDashlet):
    @classmethod
    def type_name(cls):
        return "barplot"

    @classmethod
    def title(cls):
        return _("Barplot")

    @classmethod
    def data_generator(cls):
        return SingleMetricDataGenerator

    @classmethod
    def description(cls):
        return _("Barplot")

    @classmethod
    def single_infos(cls):
        return ["service"]

    def show(self):
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        fetch_url = "single_metric_data.py"
        args: HTTPVariables = []
        args.append(("context", json.dumps(self._dashlet_spec["context"])))
        args.append(
            ("properties", json.dumps(self.vs_parameters().value_to_json(self._dashlet_spec))))
        body = html.urlencode_vars(args)

        html.javascript(
            """
            let barplot_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("barplot");
            let %(instance_name)s = new barplot_class_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.initialize();
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """ % {
                "dashlet_id": self._dashlet_id,
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(body),
                "update": 60,
            })


#   .--Single Graph--------------------------------------------------------.
#   |      ____  _             _         ____                 _            |
#   |     / ___|(_)_ __   __ _| | ___   / ___|_ __ __ _ _ __ | |__         |
#   |     \___ \| | '_ \ / _` | |/ _ \ | |  _| '__/ _` | '_ \| '_ \        |
#   |      ___) | | | | | (_| | |  __/ | |_| | | | (_| | |_) | | | |       |
#   |     |____/|_|_| |_|\__, |_|\___|  \____|_|  \__,_| .__/|_| |_|       |
#   |                    |___/                         |_|                 |
#   +----------------------------------------------------------------------+


@dashlet_registry.register
class SingleMetricDashlet(ABCFigureDashlet):
    """Dashlet that displays a single metric"""
    def __init__(self, dashboard_name, dashboard, dashlet_id, dashlet):
        super(SingleMetricDashlet, self).__init__(dashboard_name, dashboard, dashlet_id, dashlet)
        self._perf_data = []
        self._check_command = ""

    @classmethod
    def type_name(cls):
        return "single_metric"

    @classmethod
    def title(cls):
        return _("Single metric")

    @classmethod
    def description(cls):
        return _("Displays a single metric of a specific host and service.")

    def _adjust_font_size_js(self):
        return """
            let oTdMetricValue = document.getElementById("dashlet_%s").getElementsByClassName("metric_value dynamic_font_size");
            if (oTdMetricValue.length)
                cmk.dashboard.adjust_single_metric_font_size(oTdMetricValue[0]);
        """ % self._dashlet_id

    def update(self):
        self.show()
        html.javascript(self._adjust_font_size_js())

    def on_resize(self):
        return self._adjust_font_size_js()

    @classmethod
    def single_infos(cls):
        return ["service"]

    def show(self):
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        fetch_url = "single_metric_data.py"
        args: HTTPVariables = []
        args.append(("context", json.dumps(self._dashlet_spec["context"])))
        args.append(
            ("properties", json.dumps(self.vs_parameters().value_to_json(self._dashlet_spec))))
        body = html.urlencode_vars(args)

        html.javascript(
            """
            let single_metric_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("single_metric");
            let %(instance_name)s = new single_metric_class_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.initialize();
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """ % {
                "dashlet_id": self._dashlet_id,
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(body),
                "update": 60,
            })

    @classmethod
    def data_generator(cls):
        return SingleMetricDataGenerator
