#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (  # pylint: disable=unused-import
    Dict, List, Text, Union, Tuple,
)
import six

import livestatus
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    Fontsize,
    TextUnicode,
    Transform,
)
from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)
from cmk.gui.plugins.metrics.utils import (
    parse_perf_data,
    translate_metrics,
    check_metrics,
)


@dashlet_registry.register
class SingleMetricDashlet(Dashlet):
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

    @classmethod
    def sort_index(cls):
        return 95

    @classmethod
    def initial_refresh_interval(cls):
        return 60

    @classmethod
    def initial_size(cls):
        return (30, 12)

    @classmethod
    def infos(cls):
        return ["host", "service"]

    @classmethod
    def single_infos(cls):
        return ["host", "service"]

    @classmethod
    def has_context(cls):
        return True

    @classmethod
    def default_settings(cls):
        return {"show_title": False}

    @classmethod
    def vs_parameters(cls):
        return Dictionary(
            title=_("Properties"),
            render="form",
            optional_keys=[],
            elements=cls._metric_info() + cls._render_options(),
        )

    @classmethod
    def _metric_info(cls):
        return [("metric",
                 TextUnicode(
                     title=_('Metric'),
                     size=50,
                     help=_("Enter the name of a metric here to display it's value "
                            "with respect to the selected host and service"),
                 ))]

    @classmethod
    def _render_options(cls):
        return [
            (
                "metric_render_options",
                Transform(
                    Dictionary(
                        elements=[
                            ("font_size",
                             CascadingDropdown(
                                 title=_("Metric value font size"),
                                 orientation="horizontal",
                                 choices=[
                                     ("fix", _("Set the metric value font size to:"),
                                      Fontsize(default_value="22.5")),
                                     ("dynamic",
                                      _("Dynamically adapt the metric font size to the dashlet size"
                                       ))
                                 ],
                                 default_value="dynamic")),
                            ("link_to_svc_detail",
                             DropdownChoice(
                                 title=_("Link to service detail page"),
                                 choices=[
                                     ("true",
                                      _("Open service detail page when clicking on the metric value"
                                       )), ("false", _("Do not add a link to the metric value"))
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
                        title=_("Metric rendering options"),
                    ),),
            ),
        ]

    def _get_site_by_host_name(self, host_name):
        if html.request.has_var('site'):
            site = html.request.var('site')
        else:
            query = "GET hosts\nFilter: name = %s\nColumns: name" % livestatus.lqencode(host_name)
            try:
                sites.live().set_prepend_site(True)
                site = sites.live().query_column(query)[0]
            except IndexError:
                raise MKUserError("host", _("The host could not be found on any active site."))
            finally:
                sites.live().set_prepend_site(False)
        return site

    def _query_for_metrics_of_host(self, site_id, host_name, service_name):
        if not host_name or not service_name:
            return {}

        query = ("GET services\n"
                 "Columns: description check_command service_perf_data host_state service_state\n"
                 "Filter: host_name = %s\n"
                 "Filter: service_description = %s\n" %
                 (livestatus.lqencode(host_name), service_name))
        try:
            rows = sites.live().query(query)
        except Exception:
            raise MKGeneralException(
                _("The query for the given metric, service and host names returned no data."))

        for service_description, check_command, service_perf_data, host_state, svc_state in rows:
            return {
                "service_description": service_description,
                "check_command": check_command,
                "service_perf_data": service_perf_data,
                "host_state": host_state,
                "svc_state": svc_state,
            }

    def _get_translated_metrics_from_perf_data(self, row):
        perf_data_string = row["service_perf_data"].strip()
        if not perf_data_string:
            return
        self._perf_data, self._check_command = parse_perf_data(perf_data_string,
                                                               row["check_command"])
        return translate_metrics(self._perf_data, self._check_command)

    def _get_chosen_metric(self, t_metrics, given_metric_name):
        chosen_metric_name = ""
        metric_choices = []
        for data in self._perf_data:
            varname = data[0]
            orig_varname = varname
            if varname not in t_metrics:
                varname = check_metrics[self._check_command][varname]["name"]
            metric_title = t_metrics[varname]["title"]
            metric_choices.append((varname, "%s (%s)" % (varname, metric_title)))
            if varname == given_metric_name or orig_varname == given_metric_name:
                chosen_metric_name = varname
        return chosen_metric_name, metric_choices

    def _get_titles(self, metric_spec, links, render_options):
        titles = {
            "above": [],
            "below": [],
            "tooltip": [],
        }  # type: Dict[str, List[Union[Text, Tuple[Text, int]]]]

        for opt in ["site", "host", "service", "metric"]:
            opt_id = "show_%s" % opt
            if opt_id in render_options and render_options[opt_id]:
                tmp_opt = render_options[opt_id]
                if isinstance(tmp_opt, tuple):  # position != tooltip
                    position, font_size = tmp_opt
                    titles[position].append(
                        (six.text_type(links[opt] if opt in links else metric_spec[opt]),
                         font_size))
                elif tmp_opt == "tooltip":
                    titles[tmp_opt].append(six.text_type(metric_spec[opt]))
        return titles

    def _get_rendered_metric_value(self, metric, render_options, tooltip_titles, service_url):
        if render_options["show_unit"] == "true":
            rendered_value = metric["unit"]["render"](metric["value"])
        else:
            rendered_value = " ".join(metric["unit"]["render"](metric["value"]).split()[:-1])
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
        return self._adjust_font_size_js()

    def show(self):
        host = self._dashlet_spec['context'].get("host", html.request.var("host"))
        if not host:
            raise MKUserError('host', _('Missing needed host parameter.'))

        service = self._dashlet_spec['context'].get("service")
        if not service:
            service = "_HOST_"

        metric = self._dashlet_spec["metric"] if "metric" in self._dashlet_spec else ""
        site = self._get_site_by_host_name(host)
        metric_spec = {"site": site, "host": host, "service": service, "metric": metric}
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
        render_options = self._dashlet_spec["metric_render_options"]
        metrics = self._query_for_metrics_of_host(site, host, service)
        t_metrics = self._get_translated_metrics_from_perf_data(metrics)
        chosen_metric_name, metric_choices = self._get_chosen_metric(t_metrics, metric)
        svc_state = metrics["svc_state"]

        html.open_div(class_="metric")
        if metrics:
            if chosen_metric_name:
                chosen_metric = t_metrics[chosen_metric_name]
                titles = self._get_titles(metric_spec, links, render_options)
                self._render_metric_content(chosen_metric, render_options, titles, svc_state,
                                            svc_url)
            else:
                html.open_div(class_="no_metric_match")
                if metric_choices:
                    # TODO: Fix this handling of no available/matching metric
                    # after the implementation of host/site contexts
                    warning_txt = HTML(
                        _("The given metric \"%s\" could not be found.\
                            For the selected service \"%s\" you can choose from the following metrics:"
                          % (metric, service)))
                    warning_txt += html.render_ul("".join(
                        [str(html.render_li(b)) for _a, b in metric_choices]))
                    html.show_warning(warning_txt)
                else:
                    html.show_warning(_("No metric could be found."))
                html.close_div()
        else:
            html.show_warning(_("There are no metrics meeting your context filters."))
        html.close_div()
