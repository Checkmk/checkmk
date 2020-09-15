#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Dict, Optional, Tuple, List
import numpy as np  # type: ignore[import]

from cmk.utils.render import date_and_time

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    TextUnicode,
    Timerange,
)
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.plugins.dashboard.utils import site_query
from cmk.gui.plugins.metrics.utils import MetricName, reverse_translate_metric_name
from cmk.gui.plugins.metrics.rrd_fetch import rrd_columns, merge_multicol
from cmk.gui.utils.url_encoder import HTTPVariables
from cmk.gui.figures import ABCFigureDashlet, ABCDataGenerator
import cmk.gui.metrics as metrics


class AverageScatterplotDataGenerator(ABCDataGenerator):
    """Data generator for a scatterplot with average lines"""
    @classmethod
    def figure_title(cls, properties, context):
        title_config = properties["figure_title"]
        if title_config == "show":
            return cls.default_figure_title(properties, context)
        if title_config == "hide":
            return ""
        if isinstance(title_config, tuple) and title_config[0] == "custom" and isinstance(
                title_config[1], str):
            return title_config[1]
        raise MKUserError("figure_title",
                          _("Invalid bar chart title config \"%r\" given" % (title_config,)))

    @classmethod
    def default_figure_title(cls, properties, context):
        return _("Average scatterplot for %s") % cls._get_metric_name(properties, context)

    @classmethod
    def _get_metric_name(cls, properties, context):
        metric = metrics.metric_info.get(properties["metric"])
        return metric["title"] if metric else properties["metric"]

    @classmethod
    def _scatterplot_vs_components(cls):
        return [
            ("time_range", Timerange(
                title=_("Time range"),
                default_value='d0',
            )),
            ("figure_title",
             CascadingDropdown(title=_("Average scatterplot title"),
                               orientation="horizontal",
                               choices=[
                                   ("show", _("Show default title")),
                                   ("hide", _("Hide title")),
                                   ("custom", _("Set a custom title:"),
                                    TextUnicode(default_value="")),
                               ],
                               default_value="show")),
        ]

    @classmethod
    def vs_parameters(cls):
        return Dictionary(title=_("Properties"),
                          render="form",
                          optional_keys=[],
                          elements=cls._scatterplot_vs_components() + [("metric", MetricName())])

    @classmethod
    def int_time_range_from_rangespec(cls, rangespec):
        time_range, _range_title = Timerange().compute_range(rangespec)
        return [int(t) for t in time_range]

    @classmethod
    @site_query
    def _get_data(cls, properties, context):
        cmc_cols = [
            'host_name', 'host_state', 'service_description', 'service_state',
            'service_check_command', 'service_metrics', 'service_perf_data'
        ]

        from_time, until_time = map(int, Timerange().compute_range(properties['time_range'])[0])
        data_range = "%s:%s:%s" % (from_time, until_time, 60)
        _metrics: List[Tuple[str, Optional[str], float]] = [
            (name, None, scale)
            for name, scale in reverse_translate_metric_name(properties['metric'])
        ]
        metric_colums = list(rrd_columns(_metrics, 'max', data_range))

        return cmc_cols + metric_colums

    @classmethod
    def _create_scatterplot_config(cls, elements, properties, context):
        metric_name = cls._get_metric_name(properties, context)
        return {
            "title": cls.figure_title(properties, context),
            "plot_definitions": [{
                "plot_type": "scatterplot",
                "css_classes": ["scatterdot"],
                "id": "id_scatter",
                "label": _("%s by host") % metric_name,
                "use_tags": ["scatter"]
            }, {
                "plot_type": "line",
                "css_classes": ["mean_line"],
                "id": "id_mean",
                "label": _("Mean %s") % metric_name,
                "use_tags": ["line_mean"]
            }, {
                "plot_type": "line",
                "css_classes": ["median_line"],
                "id": "id_median",
                "label": _("Median %s") % metric_name,
                "use_tags": ["line_median"]
            }],
            "data": elements
        }

    @classmethod
    def generate_response_data(cls, properties, context):
        elements = cls._create_plot_elements(properties, context)
        return cls._create_scatterplot_config(elements, properties, context)

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
        columns, data_rows = cls._get_data(properties, context)  # type: ignore[call-arg]
        elements = []

        metric_name = cls._get_metric_name(properties, context)
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
            median_value = cls._get_median_value(value_dict.values())
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
        if isinstance(values, dict):
            values = [v for v in values.values() if v]
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

    @classmethod
    def data_generator(cls):
        return AverageScatterplotDataGenerator

    def show(self):
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        fetch_url = "ajax_average_scatterplot_data.py"
        args: HTTPVariables = []
        args.append(("context", json.dumps(self._dashlet_spec["context"])))
        args.append(
            ("properties", json.dumps(self.vs_parameters().value_to_json(self._dashlet_spec))))
        body = html.urlencode_vars(args)

        html.javascript(
            """
            let average_scatterplot_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("average_scatterplot");
            let %(instance_name)s = new average_scatterplot_class_%(dashlet_id)d(%(div_selector)s);
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
                "update": 300,
            })


@page_registry.register_page("ajax_average_scatterplot_data")
class AverageScatterplotDataPage(AjaxPage):
    def page(self):
        return AverageScatterplotDataGenerator.generate_response_from_request()
