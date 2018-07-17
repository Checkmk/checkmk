#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import json

from cmk.gui.i18n import _
from cmk.gui.globals import html
import cmk.gui.sites as sites

from . import SidebarSnapin

class Speedometer(SidebarSnapin):
    @staticmethod
    def type_name():
        return "speedometer"


    def title(self):
        return _("Service Speed-O-Meter")


    def description(self):
        return _("A gadget that shows your current service check rate in relation to "
                 "the scheduled check rate. If the Speed-O-Meter shows a speed "
                 "of 100 percent, all service checks are being executed in exactly "
                 "the rate that is desired.")


    def show(self):
        html.open_div(class_="speedometer")
        html.img("images/speedometer.png", id_="speedometerbg")
        html.canvas('', width=228, height=136, id_="speedometer")
        html.close_div()

        html.javascript("""
function show_speed(percentage) {
    var canvas = document.getElementById('speedometer');
    if (!canvas)
        return;

    var context = canvas.getContext('2d');
    if (!context)
        return;

    if (percentage > 100.0)
        percentage = 100.0;

    var orig_x = 116;
    var orig_y = 181;
    var angle_0   = 232.0;
    var angle_100 = 307.0;
    var angle = angle_0 + (angle_100 - angle_0) * percentage / 100.0;
    var angle_rad = angle / 360.0 * Math.PI * 2;
    var length = 120;
    var end_x = orig_x + (Math.cos(angle_rad) * length);
    var end_y = orig_y + (Math.sin(angle_rad) * length);

    context.clearRect(0, 0, 228, 136);
    context.beginPath();
    context.moveTo(orig_x, orig_y);
    context.lineTo(end_x, end_y);
    context.closePath();
    context.shadowOffsetX = 2;
    context.shadowOffsetY = 2;
    context.shadowBlur = 2;
    context.strokeStyle = "#000000";
    context.stroke();
}

function speedometer_show_speed(last_perc, program_start, scheduled_rate)
{
    var url = "sidebar_ajax_speedometer.py" +
                           "?last_perc=" + last_perc +
                           "&scheduled_rate=" + scheduled_rate +
                           "&program_start=" + program_start;

    call_ajax(url, {
        response_handler: function(handler_data, response_body) {
            try {
                var data = JSON.parse(response_body);

                oDiv = document.getElementById('speedometer');

                // Terminate reschedule when the speedometer div does not exist anymore
                // (e.g. the snapin has been removed)
                if (!oDiv)
                    return;

                oDiv.title = data.title
                oDiv = document.getElementById('speedometerbg');
                oDiv.title = data.title

                move_needle(data.last_perc, data.percentage); // 50 * 100ms = 5s = refresh time
            } catch(ie) {
                // Ignore errors during re-rendering. Proceed with reschedule...
                var data = handler_data;
            }

            setTimeout(function(data) {
                return function() {
                    speedometer_show_speed(data.percentage, data.program_start, data.scheduled_rate);
                };
            }(data), 5000);
        },
        error_handler    : function(handler_data, status_code, error_msg) {
            setTimeout(function(data) {
                return function() {
                    return speedometer_show_speed(data.percentage, data.program_start, data.scheduled_rate);
                };
            }(handler_data), 5000);
        },
        method           : "GET",
        handler_data     : {
            "percentage"     : last_perc,
            "last_perc"      : last_perc,
            "program_start"  : program_start,
            "scheduled_rate" : scheduled_rate
        }
    });
}

var g_needle_timeout = null;

function move_needle(from_perc, to_perc)
{
    var new_perc = from_perc * 0.9 + to_perc * 0.1;

    show_speed(new_perc);

    if (g_needle_timeout != null)
        clearTimeout(g_needle_timeout);

    g_needle_timeout = setTimeout(function(new_perc, to_perc) {
        return function() {
            move_needle(new_perc, to_perc);
        };
    }(new_perc, to_perc), 50);
}

speedometer_show_speed(0, 0, 0);
""")


    def allowed_roles(self):
        return [ "admin" ]


    def styles(self):
        return """
div.speedometer {
    position: relative;
    top: 0px;
    left: 0px;
    height: 223px;
}
img#speedometerbg {
    position: absolute;
    top: 0px;
    left: 0px;
}
canvas#speedometer {
    position: absolute;
    top: 0px;
    left: 0px;
}
"""

    def page_handlers(self):
        return {
            "sidebar_ajax_speedometer"    : self._ajax_speedometer,
        }


    def _ajax_speedometer(self):
        try:
            # Try to get values from last call in order to compute
            # driftig speedometer-needle and to reuse the scheduled
            # check reate.
            last_perc          = float(html.var("last_perc"))
            scheduled_rate     = float(html.var("scheduled_rate"))
            last_program_start = int(html.var("program_start"))

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
                # These days, we configure the correct check interval for Check_MK checks.
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

        except Exception, e:
            scheduled_rate = 0.0
            program_start = 0
            percentage = 0
            last_perc = 0.0
            title = _("No performance data: %s") % e

        data = {
            "scheduled_rate" : scheduled_rate,
            "program_start"  : program_start,
            "percentage"     : percentage,
            "last_perc"      : last_perc,
            "title"          : title,
        }

        html.write(json.dumps(data))
