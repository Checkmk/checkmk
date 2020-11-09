#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui.i18n import _
from cmk.gui.globals import html
import cmk.gui.sites as sites

from cmk.gui.plugins.sidebar import SidebarSnapin, snapin_registry


@snapin_registry.register
class Speedometer(SidebarSnapin):
    @staticmethod
    def type_name():
        return "speedometer"

    @classmethod
    def title(cls):
        return _("Service Speed-O-Meter")

    @classmethod
    def description(cls):
        return _("A gadget that shows your current service check rate in relation to "
                 "the scheduled check rate. If the Speed-O-Meter shows a speed "
                 "of 100 percent, all service checks are being executed in exactly "
                 "the rate that is desired.")

    def show(self):
        html.open_div(class_="speedometer")
        html.img(html.theme_url("images/speedometer.png"), id_="speedometerbg")
        html.canvas('', width="228", height="136", id_="speedometer")
        html.close_div()

        html.javascript("cmk.sidebar.speedometer_show_speed(0, 0, 0);")

    @classmethod
    def allowed_roles(cls):
        return ["admin"]

    def page_handlers(self):
        return {
            "sidebar_ajax_speedometer": self._ajax_speedometer,
        }

    def _ajax_speedometer(self):
        html.set_output_format("json")
        try:
            # Try to get values from last call in order to compute
            # driftig speedometer-needle and to reuse the scheduled
            # check reate.
            # TODO: Do we need a get_float_input_mandatory?
            last_perc = float(html.request.get_str_input_mandatory("last_perc"))
            scheduled_rate = float(html.request.get_str_input_mandatory("scheduled_rate"))
            last_program_start = html.request.get_integer_input_mandatory("program_start")

            # Get the current rates and the program start time. If there
            # are more than one site, we simply add the start times.
            data = sites.live().query_summed_stats("GET status\n"
                                                   "Columns: service_checks_rate program_start")
            current_rate = data[0]
            program_start = data[1]

            # Recompute the scheduled_rate only if it is not known (first call)
            # or if one of the sites has been restarted. The computed value cannot
            # change during the monitoring since it just reflects the configuration.
            # That way we save CPU resources since the computation of the
            # scheduled checks rate needs to loop over all hosts and services.
            if last_program_start != program_start:
                # These days, we configure the correct check interval for Checkmk checks.
                # We do this correctly for active and for passive ones. So we can simply
                # use the check_interval of all services. Hosts checks are ignored.
                #
                # Manually added services without check_interval could be a problem, but
                # we have no control there.
                scheduled_rate = sites.live().query_summed_stats(
                    "GET services\n"
                    "Stats: suminv check_interval\n")[0] / 60.0

            percentage = 100.0 * current_rate / scheduled_rate
            title = _("Scheduled service check rate: %.1f/s, current rate: %.1f/s, that is "
                      "%.0f%% of the scheduled rate") % \
                      (scheduled_rate, current_rate, percentage)

        except Exception as e:
            scheduled_rate = 0.0
            program_start = 0
            percentage = 0
            last_perc = 0.0
            title = _("No performance data: %s") % e

        html.write(
            json.dumps({
                "scheduled_rate": scheduled_rate,
                "program_start": program_start,
                "percentage": percentage,
                "last_perc": last_perc,
                "title": title,
            }))
