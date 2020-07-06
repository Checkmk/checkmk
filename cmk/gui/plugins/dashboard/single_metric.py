#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Dict, List, Union, Tuple, Optional

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Dictionary,
    Fontsize,
    Timerange,
    TextUnicode,
    CascadingDropdown,
    DropdownChoice,
)

from cmk.gui.htmllib import HTML
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.plugins.dashboard.utils import site_query, create_data_for_single_metric
from cmk.gui.plugins.metrics.utils import MetricName, reverse_translate_metric_name
from cmk.gui.metrics import translate_perf_data
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
        html.header("")
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
        html.header("")
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


class SingleGraphValueDataGenerator(SingleMetricDataGenerator):
    @classmethod
    def _vs_elements(cls):
        elements = super()._vs_elements()
        elements += cls._render_options()
        return elements

    @classmethod
    def _render_options(cls):
        return [
            (
                "render_options",
                Dictionary(
                    title=_("Render options"),
                    elements=[
                        ("font_size",
                         CascadingDropdown(
                             title=_("Metric value font size"),
                             orientation="horizontal",
                             choices=[
                                 ("fix", _("Set the metric value font size to:"),
                                  Fontsize(default_value="22.5")),
                                 ("dynamic",
                                  _("Dynamically adapt the metric font size to the dashlet size"))
                             ],
                             default_value="dynamic")),
                        ("link_to_svc_detail",
                         DropdownChoice(
                             title=_("Link to service detail page"),
                             choices=[
                                 ("true",
                                  _("Open service detail page when clicking on the metric value")),
                                 ("false", _("Do not add a link to the metric value"))
                             ],
                             default_value="true")),
                        ("show_site",
                         CascadingDropdown(
                             title=_("Show the site name"),
                             orientation="horizontal",
                             sorted=False,
                             choices=[("above", _("... above the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("below", _("... below the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("tooltip",
                                       _("... in a tooltip when hovering the metric value")),
                                      ("false", _("Do not show the site name"))],
                             default_value="false")),
                        ("show_host",
                         CascadingDropdown(
                             title=_("Show the host name"),
                             orientation="horizontal",
                             sorted=False,
                             choices=[("above", _("... above the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("below", _("... below the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("tooltip",
                                       _("... in a tooltip when hovering the metric value")),
                                      ("false", _("Do not show the host name"))],
                             default_value="false")),
                        ("show_service",
                         CascadingDropdown(
                             title=_("Show the service name"),
                             orientation="horizontal",
                             sorted=False,
                             choices=[("above", _("... above the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("below", _("... below the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("tooltip",
                                       _("... in a tooltip when hovering the metric value")),
                                      ("false", _("Do not show the service name"))],
                             default_value="tooltip")),
                        ("show_metric",
                         CascadingDropdown(
                             title=_("Show the metric name"),
                             orientation="horizontal",
                             sorted=False,
                             choices=[("above", _("... above the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("below", _("... below the metric value with font size:"),
                                       Fontsize(default_value="12.0")),
                                      ("tooltip",
                                       _("... in a tooltip when hovering the metric value")),
                                      ("false", _("Do not show the metric name"))],
                             default_value="above")),
                        ("show_state_color",
                         DropdownChoice(title=_("Show the service state color"),
                                        choices=[
                                            ("background", _("... as background color")),
                                            ("font", _("... as font color")),
                                            ("false", _("Do not show the service state color")),
                                        ],
                                        default_value="background")),
                        ("show_unit",
                         DropdownChoice(title=_("Show the metric's unit"),
                                        choices=[
                                            ("true", _("Show the metric's unit")),
                                            ("false", _("Do not show the metric's unit")),
                                        ],
                                        default_value="true")),
                    ],
                    optional_keys=[],
                ),
            ),
        ]


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

    def _get_titles(self, metric_spec, links, render_options):
        titles: Dict[str, List[Union[str, Tuple[str, int]]]] = {
            "above": [],
            "below": [],
            "tooltip": [],
        }

        for opt in ["site", "host", "service", "metric"]:
            opt_id = "show_%s" % opt
            if opt_id in render_options and render_options[opt_id]:
                tmp_opt = render_options[opt_id]
                if isinstance(tmp_opt, tuple):  # position != tooltip
                    position, font_size = tmp_opt
                    titles[position].append(
                        (str(links[opt] if opt in links else metric_spec[opt]), font_size))
                elif tmp_opt == "tooltip":
                    titles[tmp_opt].append(str(metric_spec[opt]))
        return titles

    def _get_rendered_metric_value(self, metric, render_options, tooltip_titles, service_url):
        rendered_value = metric["unit"]["render"](metric["value"])
        if render_options["show_unit"] != "true":
            rendered_value = " ".join(rendered_value.split()[:-1])
        return html.render_a(
            content=rendered_value,
            href=service_url if render_options["link_to_svc_detail"] == "true" else "",
            title=", ".join(tooltip_titles) if tooltip_titles else "")

    def _get_metric_value_classes(self, render_options, svc_state):
        state_color_class = "no-state-color"
        if render_options["show_state_color"] == "background":
            state_color_class = ""
        elif render_options["show_state_color"] == "font":
            state_color_class = "state-color-font"
        font_size_class = "dynamic_font_size"
        if isinstance(render_options["font_size"],
                      tuple):  # fixed font size with a user given value
            font_size_class = "fixed_font_size"
        return "metric_value state%s %s %s" % (svc_state, state_color_class, font_size_class)

    def _render_titles(self, titles, position_str):
        if titles[position_str]:
            html.open_tr(class_="metric_title %s" % position_str)
            html.open_td()
            for cnt, (title, font_size) in enumerate(titles[position_str]):
                if cnt != 0:
                    html.write(", ")
                html.span(title, style="font-size: %spt;" % str(font_size))
            html.close_td()
            html.close_tr()

    def _render_metric_content(self, metric, render_options, titles, svc_state, svc_url):
        rendered_metric_value = self._get_rendered_metric_value(metric, render_options,
                                                                titles["tooltip"], svc_url)
        value_div_classes = self._get_metric_value_classes(render_options, svc_state)
        font_size_style = ""
        if "fixed_font_size" in value_div_classes:
            font_size_style = "font-size: %spt" % str(render_options["font_size"][1])

        html.open_table(class_="metric_content")
        self._render_titles(titles, "above")
        html.open_tr()
        html.open_td(class_=value_div_classes, style_="%s" % font_size_style)
        html.write(rendered_metric_value)
        html.close_td()
        html.close_tr()
        self._render_titles(titles, "below")
        html.close_table()

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
        if self._dashlet_spec["time_range"] != "current":
            return super(SingleMetricDashlet, self).on_resize()
        return self._adjust_font_size_js()

    @classmethod
    def single_infos(cls):
        return ["service"]

    def show_with_timeseries(self):
        html.header("")
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        fetch_url = "ajax_single_graph_metric_data.py"
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

    def show_without_timeseries(self):
        @site_query
        def query(cls, properties, context):
            return [
                "host_name", "service_check_command", "service_description", "service_perf_data",
                "service_state"
            ]

        col_names, data = query(  # pylint: disable=unbalanced-tuple-unpacking
            self, json.dumps(self.vs_parameters().value_to_json(self._dashlet_spec)),
            self._dashlet_spec["context"])

        row = dict(zip(col_names, data[0]))

        site = row["site"]
        host = row["host_name"]
        service = row["service_description"]
        metric = self._dashlet_spec.get("metric", "")

        t_metrics = translate_perf_data(row["service_perf_data"], row["service_check_command"])
        chosen_metric = t_metrics.get(metric)
        if chosen_metric is None:
            html.show_warning(_("There are no metrics meeting your context filters."))
            warning_txt = HTML(
                _("The given metric \"%s\" could not be found.\
                        For the selected service \"%s\" you can choose from the following metrics:"
                  % (metric, service)))
            warning_txt += html.render_ul("".join(
                [str(html.render_li(m["title"])) for m in t_metrics.values()]))
            html.show_warning(warning_txt)
            return

        svc_url = "view.py?view_name=service&site=%s&host=%s&service=%s" % (
            html.urlencode(site), html.urlencode(host), html.urlencode(service))
        links = {
            "site": html.render_a(site,
                                  "view.py?view_name=sitehosts&site=%s" % (html.urlencode(site))),
            "host": html.render_a(
                host, "view.py?view_name=host&site=%s&host=%s" %
                (html.urlencode(site), html.urlencode(host))),
            "service": html.render_a(service, svc_url)
        }
        render_options = self._dashlet_spec["render_options"]

        svc_state = row["service_state"]

        html.open_div(class_="metric")
        metric_spec = {
            "site": site,
            "host": host,
            "service": service,
            "metric": chosen_metric.get("title", metric)
        }
        titles = self._get_titles(metric_spec, links, render_options)
        self._render_metric_content(chosen_metric, render_options, titles, svc_state, svc_url)
        html.close_div()

    def show(self):
        if self._dashlet_spec["time_range"] != "current":
            self.show_with_timeseries()
        else:
            self.show_without_timeseries()

    @classmethod
    def data_generator(cls):
        return SingleGraphValueDataGenerator


@page_registry.register_page("ajax_single_graph_metric_data")
class SingleMetricDataPage(AjaxPage):
    def page(self):
        return SingleGraphValueDataGenerator.generate_response_from_request()
