#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List
import numpy as np  # type: ignore[import]

from cmk.utils.render import date_and_time

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    DictionaryElements,
    GraphColor,
    Timerange,
)
from cmk.gui.plugins.dashboard import dashlet_registry, ABCFigureDashlet
from cmk.gui.plugins.dashboard.utils import service_table_query
from cmk.gui.plugins.metrics.utils import MetricName
from cmk.gui.plugins.metrics.rrd_fetch import metric_in_all_rrd_columns, merge_multicol
from cmk.gui.plugins.metrics.utils import get_metric_info


class AverageScatterplotDataGenerator:
    """Data generator for a scatterplot with average lines"""
    @classmethod
    def figure_title(cls, properties, context, settings) -> str:
        title: List[str] = []
        if settings.get("show_title", False):
            if settings.get("title") and "plain" in settings.get("title_format", []):
                title.append(settings.get("title"))
            if "add_host_name" in settings.get("title_format", []):
                if "hostregex" in context:
                    hostregex = context["hostregex"].get("host_regex", "")
                    neg_regex = context["hostregex"].get("neg_host_regex")
                    host_title = ("not " if neg_regex else "") + hostregex
                    title.append(host_title)
            if "add_service_description" in settings.get("title_format", []):
                service = context.get("service")
                if isinstance(service, str):
                    title.append(service)
                elif isinstance(service, dict):
                    if service.get('service'):
                        title.append(service['service'])

        return " / ".join(txt for txt in title)

    @staticmethod
    def required_columns(properties, context):
        cmc_cols = [
            'host_name', 'host_state', 'service_description', 'service_state',
            'service_check_command', 'service_metrics', 'service_perf_data'
        ]

        from_time, until_time = map(int, Timerange().compute_range(properties['time_range'])[0])
        metric_columns = metric_in_all_rrd_columns(properties["metric"], 'max', from_time,
                                                   until_time)

        return cmc_cols + metric_columns

    @classmethod
    def _create_scatterplot_config(cls, elements, properties, context, settings):
        metric = get_metric_info(properties["metric"], 0)[0]
        metric_name = metric["title"]

        metric_color = metric['color'] if properties.get(
            "metric_color", "default") == "default" else properties['metric_color']
        avg_color = "#0F62AF" if properties.get("avg_color",
                                                "default") == "default" else properties['avg_color']
        median_color = "#3CC2FF" if properties.get(
            "median_color", "default") == "default" else properties['median_color']

        return {
            "title": cls.figure_title(properties, context, settings),
            "plot_definitions": [{
                "plot_type": "scatterplot",
                "id": "id_scatter",
                "color": metric_color,
                "label": _("%s by host") % metric_name,
                "use_tags": ["scatter"],
                "js_render": metric['unit'].get("js_render"),
            }, {
                "plot_type": "line",
                "id": "id_mean",
                "color": avg_color,
                "label": _("Mean %s") % metric_name,
                "use_tags": ["line_mean"],
                "js_render": metric['unit'].get("js_render"),
            }, {
                "plot_type": "line",
                "id": "id_median",
                "color": median_color,
                "label": _("Median %s") % metric_name,
                "use_tags": ["line_median"],
                "js_render": metric['unit'].get("js_render"),
            }],
            "data": elements
        }

    @classmethod
    def generate_response_data(cls, properties, context, settings):
        elements = cls._create_plot_elements(properties, context)
        return cls._create_scatterplot_config(elements, properties, context, settings)

    @classmethod
    def _create_plot_elements(cls, properties, context):
        """Return a list of dicts specified as follows:
        elements = [{
            "timestamp": 1234567891,
            "value": 1.470,
            "tags": ['bli', 'bla', 'blu'],
            "label": "tribe29blibla",   # = host_name
            "tooltip": "time frame information text",
            "url": "https://url/to/specific/data/view",
            <optional_detail>
        }, ... ]"""
        elements = cls._create_scatter_elements(properties, context)
        elements.extend(cls._create_average_elements(elements))
        return elements

    @classmethod
    def _create_scatter_elements(cls, properties, context):
        columns, data_rows = service_table_query(properties, context, cls.required_columns)
        elements = []

        metric_name = get_metric_info(properties["metric"], 0)[0]["title"]
        for row in data_rows:
            d_row = dict(zip(columns, row))
            series = merge_multicol(d_row, columns, properties)
            site, host = row[:2]
            for ts, elem in series.time_data_pairs():
                if elem:
                    elements.append({
                        "timestamp": ts,
                        "value": round(elem, 3),
                        "tag": "scatter",
                        "label": host,
                        "url": cls._create_url_to_service_view(site, host, metric_name),
                        "tooltip": "%s on %s: %.2f" % (host, date_and_time(ts), elem),
                    })
        return elements

    @classmethod
    def _create_average_elements(cls, elements):
        values_per_timestamp: Dict[str, Dict] = {}
        for elem in elements:
            values_per_timestamp.setdefault(elem["timestamp"],
                                            {}).update({elem["label"]: elem["value"]})
        for ts, value_dict in values_per_timestamp.items():
            median_value = cls._get_median_value(list(value_dict.values()))
            mean_value = sum(value_dict.values()) / len(value_dict.values())
            yield {
                "timestamp": ts,
                "value": round(median_value, 3),
                "tag": "line_median",
                "label": "median",
                "tooltip": cls._create_tooltip(ts, value_dict, [("median", median_value)]),
            }
            yield {
                "timestamp": ts,
                "value": round(mean_value, 3),
                "tag": "line_mean",
                "label": "mean",
                "tooltip": cls._create_tooltip(ts, value_dict, [("mean", mean_value)]),
            }

    @classmethod
    def _create_url_to_service_view(cls, site, host, service):
        return "view.py?view_name=service&site=%(site)s&host=%(host)s&service=%(service)s" % {
            "site": site,
            "host": host,
            "service": service.replace(" ", "+"),
        }

    @classmethod
    def _create_tooltip(cls, timestamp, host_to_value_dict, additional_rows=None):
        table_rows = sorted(host_to_value_dict.items(), key=lambda item: item[1]) + additional_rows
        table_html = ""
        # TODO: cleanup str casting
        for a, b in table_rows:
            table_html += str(html.render_tr(html.render_td(a) + html.render_td(b)))
        table_html = str(html.render_table(table_html))
        tooltip = html.render_div(date_and_time(timestamp)) + table_html
        return tooltip

    @classmethod
    def _get_median_value(cls, values):
        values = list(filter(None, values))
        if values:
            return np.percentile(values, 50, interpolation='midpoint')
        return None


@dashlet_registry.register
class AverageScatterplotDashlet(ABCFigureDashlet):
    """Dashlet that displays a scatterplot and average lines for a selected type of service"""
    @classmethod
    def type_name(cls):
        return "average_scatterplot"

    @classmethod
    def title(cls):
        return _("Average scatterplot")

    @classmethod
    def description(cls):
        return _("Displays a scatterplot and average lines for for a selected type of service.")

    @staticmethod
    def generate_response_data(properties, context, settings):
        return AverageScatterplotDataGenerator.generate_response_data(properties, context, settings)

    @staticmethod
    def _vs_elements() -> DictionaryElements:
        return [
            ("metric", MetricName()),
            ("time_range", Timerange(
                title=_("Time range"),
                default_value='d0',
            )),
            ("metric_color",
             GraphColor(title=_("Color for the main metric scattered dots"),
                        default_value="default")),
            ("avg_color", GraphColor(title=_("Color for the average line"),
                                     default_value="default")),
            ("median_color",
             GraphColor(title=_("Color for the median line"), default_value="default")),
        ]

    def show(self):
        self.js_dashlet(figure_type_name=self.type_name(), fetch_url="ajax_figure_dashlet_data.py")
