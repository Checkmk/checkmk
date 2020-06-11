#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Type
from livestatus import lqencode
from cmk.utils.render import date_and_time
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.visuals import get_filter_headers
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.plugins.dashboard.bar_chart_dashlet import BarBarChartDataGenerator
from cmk.gui.figures import ABCFigureDashlet
from cmk.gui.utils.url_encoder import HTTPVariables
from cmk.gui.exceptions import MKTimeout, MKGeneralException
from cmk.gui.valuespec import Dictionary, DropdownChoice


#   .--Base Classes--------------------------------------------------------.
#   |       ____                    ____ _                                 |
#   |      | __ )  __ _ ___  ___   / ___| | __ _ ___ ___  ___  ___         |
#   |      |  _ \ / _` / __|/ _ \ | |   | |/ _` / __/ __|/ _ \/ __|        |
#   |      | |_) | (_| \__ \  __/ | |___| | (_| \__ \__ \  __/\__ \        |
#   |      |____/ \__,_|___/\___|  \____|_|\__,_|___/___/\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
class ABCEventBarChartDataGenerator(BarBarChartDataGenerator):
    """ Generates the data for host/service alert/notifications bar charts """
    @classmethod
    def log_type(cls):
        raise NotImplementedError()

    @classmethod
    def log_class(cls):
        raise NotImplementedError()

    @classmethod
    def filter_infos(cls):
        return ["host", "service"]

    @classmethod
    def vs_parameters(cls):
        # Specifies the properties for this data generator
        return Dictionary(
            title=_("Properties"),
            render="form",
            optional_keys=[],
            elements=super(ABCEventBarChartDataGenerator, cls).bar_chart_vs_components() +
            [("log_target",
              DropdownChoice(
                  title=_("Host or service %ss" % cls.log_type()),
                  choices=[("host", _("Show %ss for hosts" % cls.log_type())),
                           ("service", _("Show %ss for services" % cls.log_type()))],
                  default_value="service",
              ))])

    @classmethod
    def _get_data(cls, properties, context, return_column_headers=True):
        time_range = cls._int_time_range_from_rangespec(properties["time_range"])
        # TODO KO: check typing
        c_headers = "ColumnHeaders: on\n" if return_column_headers else ""  # type: Any
        filter_headers, only_sites = get_filter_headers("log", cls.filter_infos(), context)

        query = ("GET log\n"
                 "Columns: log_state host_name service_description log_type log_time\n"
                 "%s"
                 "Filter: class = %d\n"
                 "Filter: log_time >= %f\n"
                 "Filter: log_time <= %f\n"
                 "Filter: log_type ~ %s .*\n"
                 "%s" % (c_headers, cls.log_class(), time_range[0], time_range[1],
                         lqencode(properties["log_target"].upper()), lqencode(filter_headers)))

        try:
            if only_sites:
                sites.live().set_only_sites(only_sites)
            rows = sites.live().query(query)
        except MKTimeout:
            raise
        except Exception as _e:
            raise MKGeneralException(_("The query returned no data."))
        finally:
            sites.live().set_only_sites(None)

        c_headers = ""
        if return_column_headers:
            c_headers = rows.pop(0)
        return rows, c_headers

    @classmethod
    def _forge_tooltip_and_url(cls, time_frame, properties, context):
        time_range = cls._int_time_range_from_rangespec(properties["time_range"])
        end_time = min(time_frame["end_time"], time_range[1])
        from_time_str = date_and_time(time_frame["start_time"])
        to_time_str = date_and_time(end_time)
        # TODO: Can this be simplified by passing a list as argument to html.render_table()?
        tooltip = html.render_table(
            html.render_tr(html.render_td(_("From:")) + html.render_td(from_time_str)) +
            html.render_tr(html.render_td(_("To:")) + html.render_td(to_time_str)) + \
            html.render_tr(html.render_td("%ss:" % properties["log_target"].capitalize()) +
                html.render_td(time_frame["value"])))

        args = []  # type: HTTPVariables
        # Generic filters
        args.append(("filled_in", "filter"))
        args.append(("view_name", "events"))
        args.append(("logtime_from", str(time_frame["start_time"])))
        args.append(("logtime_from_range", "unix"))
        args.append(("logtime_until", str(end_time)))
        args.append(("logtime_until_range", "unix"))
        args.append(("logclass%d" % cls.log_class(), "on"))

        # Target filters
        if properties["log_target"] == "host":
            args.append(("logst_h0", "on"))
            args.append(("logst_h1", "on"))
            args.append(("logst_h2", "on"))
        else:
            args.append(("logst_s0", "on"))
            args.append(("logst_s1", "on"))
            args.append(("logst_s2", "on"))
            args.append(("logst_s3", "on"))

        # Context
        for fil in context.values():
            for k, f in fil.items():
                args.append((k, f))

        return tooltip, html.makeuri_contextless(args, filename="view.py")


class ABCEventBarChartDashlet(ABCFigureDashlet):
    @classmethod
    def data_generator(cls):
        # type: () -> Type[ABCEventBarChartDataGenerator]
        raise NotImplementedError()

    def show(self):
        args = []  # type: HTTPVariables
        args.append(("context", json.dumps(self._dashlet_spec["context"])))
        args.append(
            ("properties", json.dumps(self.vs_parameters().value_to_json(self._dashlet_spec))))
        args.append(("log_type", self.data_generator().log_type()))
        body = html.urlencode_vars(args)

        fetch_url = "ajax_%s_dashlet.py" % self.type_name()
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)
        html.javascript(
            """
            let bar_chart_class_%(dashlet_id)d = cmk.figures.figure_registry.get_figure("timeseries");
            let %(instance_name)s = new bar_chart_class_%(dashlet_id)d(%(div_selector)s);
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
                "update": self.update_interval,
            })


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
    @classmethod
    def type_name(cls):
        return "notifications_bar_chart"

    @classmethod
    def title(cls):
        return _("Host and service notifications")

    @classmethod
    def description(cls):
        return _("Displays a bar chart for host and service notifications.")

    @classmethod
    def data_generator(cls):
        # type: () -> Type[NotificationsBarChartDataGenerator]
        return NotificationsBarChartDataGenerator


class NotificationsBarChartDataGenerator(ABCEventBarChartDataGenerator):
    @classmethod
    def log_type(cls):
        return "notification"

    @classmethod
    def log_class(cls):
        return 3

    @classmethod
    def default_bar_chart_title(cls, properties, context):
        log_target_to_title = {
            "host": _("Host"),
            "service": _("Service"),
        }
        return _("%s notifications") % log_target_to_title[properties["log_target"]]


@page_registry.register_page("ajax_notifications_bar_chart_dashlet")
class NotificationsDataPage(AjaxPage):
    def page(self):
        return NotificationsBarChartDataGenerator.generate_response_from_request()


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
    @classmethod
    def type_name(cls):
        return "alerts_bar_chart"

    @classmethod
    def title(cls):
        return _("Host and service alerts")

    @classmethod
    def description(cls):
        return _("Displays a bar chart for host and service alerts.")

    @classmethod
    def data_generator(cls):
        # type: () -> Type[AlertBarChartDataGenerator]
        return AlertBarChartDataGenerator


class AlertBarChartDataGenerator(ABCEventBarChartDataGenerator):
    @classmethod
    def log_type(cls):
        return "alert"

    @classmethod
    def log_class(cls):
        return 1

    @classmethod
    def default_bar_chart_title(cls, properties, context):
        log_target_to_title = {
            "host": _("Host"),
            "service": _("Service"),
        }
        return _("%s alerts") % log_target_to_title[properties["log_target"]]


@page_registry.register_page("ajax_alerts_bar_chart_dashlet")
class AlertsDataPage(AjaxPage):
    def page(self):
        return AlertBarChartDataGenerator.generate_response_from_request()
