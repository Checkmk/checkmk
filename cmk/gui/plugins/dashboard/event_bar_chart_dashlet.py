#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import livestatus
from livestatus import lqencode

from cmk.utils.render import date_and_time
from cmk.gui.type_defs import HTTPVariables
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.visuals import get_filter_headers
from cmk.gui.plugins.dashboard import dashlet_registry, ABCFigureDashlet
from cmk.gui.plugins.dashboard.bar_chart_dashlet import BarChartDataGenerator
from cmk.gui.plugins.dashboard.utils import render_title_with_macros_string
from cmk.gui.exceptions import MKTimeout, MKGeneralException
from cmk.gui.valuespec import (Dictionary, DropdownChoice, CascadingDropdown, Timerange)
from cmk.gui.utils.urls import makeuri_contextless


#   .--Base Classes--------------------------------------------------------.
#   |       ____                    ____ _                                 |
#   |      | __ )  __ _ ___  ___   / ___| | __ _ ___ ___  ___  ___         |
#   |      |  _ \ / _` / __|/ _ \ | |   | |/ _` / __/ __|/ _ \/ __|        |
#   |      | |_) | (_| \__ \  __/ | |___| | (_| \__ \__ \  __/\__ \        |
#   |      |____/ \__,_|___/\___|  \____|_|\__,_|___/___/\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
class ABCEventBarChartDataGenerator(BarChartDataGenerator):
    """ Generates the data for host/service alert/notifications bar charts """
    def __init__(self, log_type, log_class):
        self.log_type = log_type
        self.log_class = log_class

    @classmethod
    def filter_infos(cls):
        return ["host", "service"]

    def generate_response_data(self, properties, context, settings):
        """Toggle between the data of the different render modes"""
        # TODO: Would be better to have independent data generators for the various render modes,
        # but that is not possible with the current mechanic. Once we spread the toggling of render
        # modes, we should restructure this.
        if properties["render_mode"][0] == "bar_chart":
            return super().generate_response_data(properties, context, settings)
        if properties["render_mode"][0] == "simple_number":
            return self._generate_simple_number_response_data(properties, context, settings)
        raise NotImplementedError()

    def _generate_simple_number_response_data(self, properties, context, settings):
        """Needs to produce a data structure that is understood by the "single_metric" figure
        instance we initiate in the show() method """
        return {
            "plot_definitions": [{
                "label": "",
                "id": "number",
                "plot_type": "single_value",
                "use_tags": ["number"],
                "metrics": {
                    "warn": None,
                    "crit": None,
                    "min": None,
                    "max": None,
                }
            }],
            "data": self._get_simple_number_data(properties, context),
        }

    # TODO: Possible performance optimization: We only need to count events. Changing this to Stats
    # queries could improve the performance of the dashlet
    def _get_data(self, properties, context):
        mode_properties = properties["render_mode"][1]
        time_range = self._int_time_range_from_rangespec(mode_properties["time_range"])
        filter_headers, only_sites = get_filter_headers("log", self.filter_infos(), context)
        object_type_filter = self._get_object_type_filter(properties)

        query = ("GET log\n"
                 "Columns: log_state host_name service_description log_type log_time\n"
                 "Filter: class = %d\n"
                 "Filter: log_time >= %f\n"
                 "Filter: log_time <= %f\n"
                 "%s"
                 "%s" % (self.log_class, time_range[0], time_range[1], object_type_filter,
                         lqencode(filter_headers)))

        with sites.only_sites(only_sites):
            try:
                return sites.live().query(query)
            except MKTimeout:
                raise
            except Exception:
                raise MKGeneralException(_("The query returned no data."))

    def _get_simple_number_data(self, properties, context):
        return [{
            "tag": "number",
            "timestamp": int(time.time()),
            "value": count,
            "last_value": True,
        } for label, count in zip([_("Total")], self._fetch_simple_number_data(properties, context))
               ]

    def _fetch_simple_number_data(self, properties, context):
        mode_properties = properties["render_mode"][1]
        time_range = self._int_time_range_from_rangespec(mode_properties["time_range"])
        filter_headers, only_sites = get_filter_headers("log", self.filter_infos(), context)
        object_type_filter = self._get_object_type_filter(properties)

        query = ("GET log\n"
                 "Stats: log_type != \n"
                 "Filter: class = %d\n"
                 "Filter: log_time >= %f\n"
                 "Filter: log_time <= %f\n"
                 "%s"
                 "%s" % (self.log_class, time_range[0], time_range[1], object_type_filter,
                         lqencode(filter_headers)))

        with sites.only_sites(only_sites):
            try:
                return sites.live().query_summed_stats(query)
            except livestatus.MKLivestatusNotFoundError:
                raise MKGeneralException(_("The query returned no data."))

    @classmethod
    def _get_object_type_filter(cls, properties) -> str:
        if properties["log_target"] != "both":
            return "Filter: log_type ~ %s .*\n" % lqencode(properties["log_target"].upper())
        return ""

    def _forge_tooltip_and_url(self, time_frame, properties, context):
        mode_properties = properties["render_mode"][1]
        time_range = self._int_time_range_from_rangespec(mode_properties["time_range"])
        ending_timestamp = min(time_frame["ending_timestamp"], time_range[1])
        from_time_str = date_and_time(time_frame["timestamp"])
        to_time_str = date_and_time(ending_timestamp)
        # TODO: Can this be simplified by passing a list as argument to html.render_table()?
        tooltip = html.render_table(
            html.render_tr(html.render_td(_("From:")) + html.render_td(from_time_str)) +
            html.render_tr(html.render_td(_("To:")) + html.render_td(to_time_str)) + html.render_tr(
                html.render_td("%ss:" % properties["log_target"].capitalize()) +
                html.render_td(time_frame["value"])))

        args: HTTPVariables = []
        # Generic filters
        args.append(("filled_in", "filter"))
        args.append(("view_name", "events"))
        args.append(("logtime_from", str(time_frame["timestamp"])))
        args.append(("logtime_from_range", "unix"))
        args.append(("logtime_until", str(ending_timestamp)))
        args.append(("logtime_until_range", "unix"))
        args.append(("logclass%d" % self.log_class, "on"))

        # Target filters
        if properties["log_target"] == "host":
            args.append(("logst_h0", "on"))
            args.append(("logst_h1", "on"))
            args.append(("logst_h2", "on"))
        elif properties["log_target"] == "service":
            args.append(("logst_s0", "on"))
            args.append(("logst_s1", "on"))
            args.append(("logst_s2", "on"))
            args.append(("logst_s3", "on"))

        # Context
        for fil in context.values():
            for k, f in fil.items():
                args.append((k, f))

        return tooltip, makeuri_contextless(request, args, filename="view.py")


def default_bar_chart_title(log_target: str, name: str) -> str:
    log_target_to_title = {
        "both": _("Host and service"),
        "host": _("Host"),
        "service": _("Service"),
    }

    return _("%s %s") % (log_target_to_title[log_target], name)


def bar_chart_title(properties, context, settings) -> str:
    if not settings.get("show_title", True):
        return ""

    chart_name = settings['type'].split("_")[0]
    deflt_title = default_bar_chart_title(properties['log_target'], chart_name)

    return render_title_with_macros_string(
        context,
        settings["single_infos"],
        settings.get("title", deflt_title),
        deflt_title,
    )


def bar_chart_vs_time_components():
    return [
        ("time_range", Timerange(
            title=_("Time range"),
            default_value='d0',
        )),
        ("time_resolution",
         DropdownChoice(
             title=_("Time resolution"),
             choices=[("h", _("Show per hour")), ("d", _("Show per day"))],
             default_value="h",
         )),
    ]


class ABCEventBarChartDashlet(ABCFigureDashlet):
    log_type = ""
    log_class = 0

    @classmethod
    def _vs_elements(cls):
        return [
            ("render_mode",
             CascadingDropdown(choices=[
                 ("bar_chart", _("Bar chart"),
                  Dictionary(
                      elements=bar_chart_vs_time_components(),
                      optional_keys=[],
                  )),
                 ("simple_number", _("Number of notifications as text"),
                  Dictionary(
                      elements=[
                          ("time_range", Timerange(
                              title=_("Time range"),
                              default_value='d0',
                          )),
                      ],
                      optional_keys=[],
                  )),
             ])),
            ("log_target",
             DropdownChoice(
                 title=_("Host or service %ss" % cls.log_type),
                 choices=[
                     ("both", _("Show %ss for hosts and services" % cls.log_type)),
                     ("host", _("Show %ss for hosts" % cls.log_type)),
                     ("service", _("Show %ss for services" % cls.log_type)),
                 ],
                 default_value="both",
             )),
        ]

    def show(self):
        render_type = self._dashlet_spec["render_mode"][0]
        if render_type == "bar_chart":
            figure_type_name = "timeseries"
        elif render_type == "simple_number":
            figure_type_name = "single_metric"
        else:
            raise NotImplementedError()
        self.js_dashlet(figure_type_name=figure_type_name)

    # TODO: implement default_display_title. This is currently handled in bar_chart_title, but it
    #  should be implemented here. This can be done once the ajax calls for rendering the dashlets
    #  actually instantiate the corresponding dashlet class.


#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
@dashlet_registry.register
class NotificationsBarChartDashlet(ABCEventBarChartDashlet):
    """Dashlet that displays a bar chart for host and service notifications"""
    log_type = "notification"
    log_class = 3

    @classmethod
    def type_name(cls):
        return "notifications_bar_chart"

    @classmethod
    def title(cls):
        return _("Notification timeline")

    @classmethod
    def description(cls):
        return _("Displays a bar chart for host and service notifications.")

    @staticmethod
    def generate_response_data(properties, context, settings):

        response = ABCEventBarChartDataGenerator("notification", 3).generate_response_data(
            properties, context, settings)
        response['title'] = bar_chart_title(properties, context, settings)
        return response


#   .--Alerts--------------------------------------------------------------.
#   |                        _    _           _                            |
#   |                       / \  | | ___ _ __| |_ ___                      |
#   |                      / _ \ | |/ _ \ '__| __/ __|                     |
#   |                     / ___ \| |  __/ |  | |_\__ \                     |
#   |                    /_/   \_\_|\___|_|   \__|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
@dashlet_registry.register
class AlertsBarChartDashlet(ABCEventBarChartDashlet):
    """Dashlet that displays a bar chart for host and service alerts"""
    log_type = "alert"
    log_class = 1

    @classmethod
    def type_name(cls):
        return "alerts_bar_chart"

    @classmethod
    def title(cls):
        return _("Alert timeline")

    @classmethod
    def description(cls):
        return _("Displays a bar chart for host and service alerts.")

    @staticmethod
    def generate_response_data(properties, context, settings):
        response = ABCEventBarChartDataGenerator("alert", 1).generate_response_data(
            properties, context, settings)
        response['title'] = bar_chart_title(properties, context, settings)
        return response
