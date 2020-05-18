#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import (  # pylint: disable=unused-import
    Dict, Text, List)
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKTimeout, MKGeneralException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    TextUnicode,
    Timerange,
)
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.plugins.metrics.stats import percentile
from cmk.utils.render import date_and_time
from cmk.gui.visuals import get_filter_headers

from cmk.gui.utils.url_encoder import HTTPVariables  # pylint: disable=unused-import
from cmk.gui.figures import ABCFigureDashlet, ABCDataGenerator


class AverageScatterplotDataGenerator(ABCDataGenerator):
    """Data generator for a scatterplot with average lines"""
    @classmethod
    def type_name(cls):
        return "average_scatterplot"

    @classmethod
    def scatterplot_title(cls, properties, context):
        title_config = properties["scatterplot_title"]
        if title_config == "show":
            return cls.default_scatterplot_title(properties, context)
        elif title_config == "hide":
            return ""
        elif isinstance(title_config, tuple) and title_config[0] == "custom" and isinstance(
                title_config[1], (unicode, str)):
            return title_config[1]
        else:
            raise MKUserError("scatterplot_title",
                              _("Invalid bar chart title config \"%r\" given" % (title_config,)))

    @classmethod
    def default_scatterplot_title(cls, properties, context):
        return _("Average scatterplot for %s") % properties["service"]

    @classmethod
    def _scatterplot_vs_components(cls):
        return [
            ("time_range", Timerange(
                title=_("Time range"),
                default_value='d0',
            )),
            ("scatterplot_title",
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
                          elements=cls._scatterplot_vs_components() +
                          [("service",
                            DropdownChoice(title=_("Service type"),
                                           choices=[("CPU load", _("CPU load")),
                                                    ("CPU utilization", _("CPU utilization"))],
                                           default_value="CPU load"))])

    @classmethod
    def int_time_range_from_rangespec(cls, rangespec):
        time_range, _range_title = Timerange().compute_range(rangespec)
        return [int(t) for t in time_range]

    @classmethod
    def _get_data(cls, properties, context, return_column_headers=True):
        time_range = cls.int_time_range_from_rangespec(properties["time_range"])
        c_headers = "ColumnHeaders: on\n" if return_column_headers else ""
        filter_headers, only_sites = get_filter_headers("log", ["host", "service"], context)
        metrics = {
            "CPU load": "load1",
            "CPU utilization": "util",
        }
        service_desc = properties["service"]

        query = (
            "GET services\n"
            "Columns: host_name host_state service_description service_state service_check_command service_metrics service_perf_data rrddata:v1:%(metric)s:%(start)s:%(end)s:%(step)s\n"
            #  rrddata:m1:load1.max:%(start)s:%(end)s:%(step)s rrddata:m5:load5.max:%(start)s:%(end)s:%(step)s rrddata:m15:load15.max:%(start)s:%(end)s:%(step)s
            "%(column)s"
            "Filter: service_description ~~ %(service)s\n"
            "%(filter)s" % {
                "metric": metrics[service_desc],
                "start": time_range[0],
                "end": time_range[1],
                "step": 300,
                "service": service_desc,
                "column": c_headers,
                "filter": filter_headers,
            })

        with sites.only_sites(only_sites), sites.prepend_site():
            try:
                rows = sites.live().query(query)
            except MKTimeout:
                raise
            except Exception as _e:
                raise MKGeneralException(_("The query returned no data."))

        if return_column_headers:
            return rows[0], rows[1:]
        return rows, ""

    @classmethod
    def _create_scatterplot_config(cls, elements, properties, context):
        return {
            "title": cls.scatterplot_title(properties, context),
            "plot_definitions": [
                {
                    "plot_type": "scatterplot",
                    "css_classes": ["scatterdot"],
                    "show_axis": True,
                    "id": "id_scatter",
                    #TODO: properties["service"] is already dashlet specific; rm this from data generator
                    "label": _("%s by host") % properties["service"],
                    "use_tags": ["scatter"]
                },
                {
                    "plot_type": "line",
                    "css_classes": ["mean_line"],
                    "id": "id_mean",
                    "label": _("Mean %s") % properties["service"],
                    "use_tags": ["line_mean"]
                },
                {
                    "plot_type": "line",
                    "css_classes": ["median_line"],
                    "id": "id_median",
                    "label": _("Median %s") % properties["service"],
                    "use_tags": ["line_median"]
                }
            ],
            "data": elements
        }

    @classmethod
    def generate_response_data(cls, properties, context):
        data_rows, _column_headers = cls._get_data(properties, context, return_column_headers=False)
        elements = cls._create_plot_elements(data_rows, properties, context)
        return cls._create_scatterplot_config(elements, properties, context)

    @classmethod
    def _create_plot_elements(cls, data_rows, properties, context):
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
        elements = cls._create_scatter_elements(data_rows, properties)
        elements.extend(cls._create_average_elements(elements))
        return elements

    @classmethod
    def _create_scatter_elements(cls, data_rows, properties):
        elements = []
        for row in data_rows:
            start, _end, step = row[-1][:3]
            site, host = row[:2]
            service = properties["service"]
            for i, elem in enumerate(row[-1][3:]):
                if elem:
                    if elem > 20:
                        continue
                    ts = start + i * step
                    elements.append({
                        "timestamp": ts,
                        "value": round(elem, 3),
                        "tag": "scatter",
                        "label": row[1],
                        "url": cls._create_url_to_service_view(site, host, service),
                        "tooltip": "%s on %s: %.2f" % (row[1], date_and_time(ts), elem),
                    })
        return elements

    @classmethod
    def _create_average_elements(cls, elements):
        median_elements = []
        mean_elements = []
        values_per_timestamp = {}  # type: Dict[Text, Dict]
        for elem in elements:
            if elem["timestamp"] in values_per_timestamp:
                values_per_timestamp[elem["timestamp"]][elem["label"]] = elem["value"]
            else:
                values_per_timestamp[elem["timestamp"]] = {elem["label"]: elem["value"]}
        for ts, value_dict in values_per_timestamp.iteritems():
            median_value = cls._get_median_value(value_dict.values())
            mean_value = sum(value_dict.values()) / len(value_dict.values())
            median_elements.append({
                "timestamp": ts,
                "value": round(median_value, 3),
                "tag": "line_median",
                "label": "median",
                "tooltip": cls._create_tooltip(ts, value_dict, [("median", median_value)]),
            })
            mean_elements.append({
                "timestamp": ts,
                "value": round(mean_value, 3),
                "tag": "line_mean",
                "label": "mean",
                "tooltip": cls._create_tooltip(ts, value_dict, [("mean", mean_value)]),
            })
        return median_elements + mean_elements

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
            return percentile(values, 50)
        return None


@dashlet_registry.register
class AverageScatterplotDashlet(ABCFigureDashlet):
    """Dashlet that displays a scatterplot and average lines for a selected type of service"""
    @classmethod
    def type_name(cls):
        return "average_scatterplot_dashlet"

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
        html.header("")
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        fetch_url = "ajax_average_scatterplot_data.py"
        args = []  # type: HTTPVariables
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
